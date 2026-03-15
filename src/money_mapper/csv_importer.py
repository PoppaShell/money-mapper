#!/usr/bin/env python3
"""
CSV Importer - Import financial transactions from CSV files.

This module provides functionality to import transactions from various CSV formats
(checking, savings, credit card) and standardize them for processing by the enrichment pipeline.
"""

import csv
import os
from typing import Any

from money_mapper.utils import standardize_date

# CSV format schemas
CSV_SCHEMAS = {
    "checking": {
        "required_headers": ["Date", "Description", "Debit", "Credit"],
        "optional_headers": ["Balance", "Check Number", "Reference"],
        "date_field": "Date",
        "merchant_field": "Description",
        "amount_fields": ["Debit", "Credit"],
        "balance_field": "Balance",
    },
    "savings": {
        "required_headers": ["Date", "Transaction", "Withdrawal", "Deposit"],
        "optional_headers": ["Balance", "Interest"],
        "date_field": "Date",
        "merchant_field": "Transaction",
        "amount_fields": ["Withdrawal", "Deposit"],
        "balance_field": "Balance",
    },
    "credit": {
        "required_headers": ["Transaction Date", "Description", "Amount"],
        "optional_headers": ["Post Date", "Reference Number", "Balance"],
        "date_field": "Transaction Date",
        "merchant_field": "Description",
        "amount_fields": ["Amount"],
        "balance_field": "Balance",
    },
}


def detect_csv_type(headers: list[str]) -> str | None:
    """
    Detect CSV type based on column headers.

    Args:
        headers: List of CSV column headers

    Returns:
        CSV type ('checking', 'savings', 'credit') or None if unknown
    """
    if not headers:
        return None

    # Normalize headers for comparison
    headers_lower = [h.lower() for h in headers]

    # Check for credit card format
    if any(x in headers_lower for x in ["transaction date", "post date", "card"]):
        if any(x in headers_lower for x in ["amount", "description"]):
            return "credit"

    # Check for checking account format
    if all(x in headers_lower for x in ["date", "description", "debit", "credit"]):
        return "checking"

    # Check for savings account format
    if all(x in headers_lower for x in ["date", "transaction", "withdrawal", "deposit"]):
        return "savings"

    # Alternative checking format with just Date and Description
    if "date" in headers_lower and "description" in headers_lower:
        if any(x in headers_lower for x in ["debit", "withdrawal", "amount", "charge"]):
            return "checking"

    return None


def validate_csv_headers(headers: list[str], csv_type: str) -> bool | tuple[bool, str]:
    """
    Validate that CSV has required headers for the specified type.

    Args:
        headers: List of CSV column headers
        csv_type: Type of CSV ('checking', 'savings', 'credit')

    Returns:
        True if valid, False/tuple with error message if invalid
    """
    if csv_type not in CSV_SCHEMAS:
        return False, f"Unknown CSV type: {csv_type}"

    if not headers:
        return False, "No headers found in CSV"

    schema = CSV_SCHEMAS[csv_type]
    headers_lower = [h.lower() for h in headers]
    schema_required_lower = [h.lower() for h in schema["required_headers"]]

    # Check if all required headers are present (case-insensitive)
    missing = []
    for req in schema_required_lower:
        if req not in headers_lower:
            missing.append(req)

    if missing:
        return False, f"Missing required headers for {csv_type}: {', '.join(missing)}"

    return True


def standardize_csv_transaction(row: dict[str, Any], csv_type: str) -> dict[str, Any]:
    """
    Convert CSV row to standardized transaction format.

    Args:
        row: Dictionary representing a CSV row
        csv_type: Type of CSV ('checking', 'savings', 'credit')

    Returns:
        Standardized transaction dictionary
    """
    if csv_type not in CSV_SCHEMAS:
        return {}

    schema = CSV_SCHEMAS[csv_type]
    transaction: dict[str, Any] = {}

    # Extract date
    date_field = schema["date_field"]
    if date_field in row and row[date_field]:
        date_str = row[date_field].strip()
        transaction["date"] = standardize_date(date_str)

    # Extract merchant name
    merchant_field = schema["merchant_field"]
    if merchant_field in row and row[merchant_field]:
        transaction["merchant"] = row[merchant_field].strip()
        transaction["description"] = row[merchant_field].strip()

    # Extract amount
    amount = _extract_amount(row, schema, csv_type)
    if amount is not None:
        transaction["amount"] = amount

    # Extract balance if available
    balance_field = schema.get("balance_field")
    if balance_field and balance_field in row and row[balance_field]:
        try:
            balance_str = row[balance_field].strip().replace(",", "").replace("$", "")
            transaction["balance"] = float(balance_str)
        except (ValueError, AttributeError):
            pass

    # Add transaction type
    transaction["transaction_type"] = csv_type

    return transaction


def _extract_amount(row: dict[str, Any], schema: dict[str, Any], csv_type: str) -> float | None:
    """
    Extract transaction amount from row based on schema.

    Args:
        row: CSV row dictionary
        schema: CSV schema
        csv_type: Type of CSV

    Returns:
        Transaction amount or None
    """
    amount_fields = schema["amount_fields"]

    if csv_type == "credit":
        # Credit cards often have single Amount field (negative for charges)
        if "Amount" in row and row["Amount"]:
            try:
                amount_str = str(row["Amount"]).strip().replace(",", "").replace("$", "")
                return float(amount_str)
            except ValueError:
                pass

    elif csv_type in ["checking", "savings"]:
        # Checking/savings have separate Debit/Credit or Withdrawal/Deposit
        debit_field = amount_fields[0] if len(amount_fields) > 0 else None
        credit_field = amount_fields[1] if len(amount_fields) > 1 else None

        if debit_field and debit_field in row:
            debit_str = str(row[debit_field]).strip()
            if debit_str and debit_str.replace(",", "").replace(".", "", 1):
                try:
                    return -float(debit_str.replace(",", ""))  # Debits are negative
                except ValueError:
                    pass

        if credit_field and credit_field in row:
            credit_str = str(row[credit_field]).strip()
            if credit_str and credit_str.replace(",", "").replace(".", "", 1):
                try:
                    return float(credit_str.replace(",", ""))  # Credits are positive
                except ValueError:
                    pass

    return None


def parse_csv_transactions(csv_file_path: str) -> list[dict[str, Any]]:
    """
    Parse CSV file and return standardized transactions.

    Args:
        csv_file_path: Path to CSV file

    Returns:
        List of standardized transaction dictionaries
    """
    transactions: list[dict[str, Any]] = []

    if not os.path.exists(csv_file_path):
        return transactions

    try:
        with open(csv_file_path, encoding="utf-8", errors="replace") as f:
            # Try to detect CSV dialect
            try:
                sample = f.read(8192)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = "excel"

            f.seek(0)
            reader = csv.DictReader(f, dialect=dialect)

            if not reader.fieldnames:
                return transactions

            # Detect CSV type from headers
            csv_type = detect_csv_type(reader.fieldnames)

            # If type detection failed, try to infer from content
            if csv_type is None:
                # Try checking first (most common)
                csv_type = "checking"

            # Validate headers
            is_valid = validate_csv_headers(reader.fieldnames, csv_type)
            if not is_valid if isinstance(is_valid, bool) else not is_valid[0]:
                # If validation fails, still try to parse
                pass

            # Parse rows
            for row_num, row in enumerate(reader, start=2):
                # Skip empty rows
                if not any(row.values()):
                    continue

                # Standardize transaction
                transaction = standardize_csv_transaction(row, csv_type)

                # Only add if we have at least date and amount
                if transaction and ("date" in transaction or "merchant" in transaction):
                    if "amount" in transaction or "merchant" in transaction:
                        transactions.append(transaction)

    except Exception as e:
        print(f"Warning: Error parsing CSV file {csv_file_path}: {e}")

    return transactions


class CSVValidator:
    """Validator for CSV files."""

    def __init__(self, csv_type: str | None = None):
        """
        Initialize CSV validator.

        Args:
            csv_type: Type of CSV to validate ('checking', 'savings', 'credit') or None for auto-detect
        """
        self.csv_type = csv_type

    def validate(self, csv_file_path: str) -> bool | tuple[bool, str]:
        """
        Validate CSV file structure and content.

        Args:
            csv_file_path: Path to CSV file

        Returns:
            True if valid, (False, error_message) if invalid
        """
        if not os.path.exists(csv_file_path):
            return False, "File does not exist"

        try:
            with open(csv_file_path, encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames:
                    return False, "CSV file has no headers"

                # Auto-detect type if not specified
                csv_type = self.csv_type or detect_csv_type(reader.fieldnames)

                if csv_type is None:
                    return False, "Could not determine CSV type from headers"

                # Validate headers
                is_valid = validate_csv_headers(reader.fieldnames, csv_type)
                if not is_valid if isinstance(is_valid, bool) else not is_valid[0]:
                    error_msg = is_valid[1] if isinstance(is_valid, tuple) else "Invalid headers"
                    return False, error_msg

                # Check that we have at least one data row
                first_row = next(reader, None)
                if first_row is None:
                    return False, "CSV file has no data rows"

                return True

        except Exception as e:
            return False, f"Error validating CSV: {str(e)}"


class CSVImporter:
    """Main CSV importer class."""

    def __init__(self):
        """Initialize CSV importer."""
        self.validator = None

    def validate_file(self, csv_file_path: str) -> bool | tuple[bool, str]:
        """
        Validate a CSV file before import.

        Args:
            csv_file_path: Path to CSV file

        Returns:
            True if valid, (False, error_message) if invalid
        """
        validator = CSVValidator()
        return validator.validate(csv_file_path)

    def import_csv(self, csv_file_path: str, csv_type: str | None = None) -> list[dict[str, Any]]:
        """
        Import transactions from CSV file.

        Args:
            csv_file_path: Path to CSV file
            csv_type: Type of CSV ('checking', 'savings', 'credit') or None for auto-detect

        Returns:
            List of standardized transaction dictionaries
        """
        if not os.path.exists(csv_file_path):
            print(f"Error: CSV file not found: {csv_file_path}")
            return []

        # Auto-detect type if not specified
        if csv_type is None:
            try:
                with open(csv_file_path, encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        detected_type = detect_csv_type(reader.fieldnames)
                        csv_type = detected_type or "checking"
            except Exception as e:
                print(f"Warning: Could not auto-detect CSV type, defaulting to checking: {e}")
                csv_type = "checking"

        # Validate file
        validator = CSVValidator(csv_type)
        is_valid = validator.validate(csv_file_path)
        if not is_valid if isinstance(is_valid, bool) else not is_valid[0]:
            print("Warning: CSV validation failed, attempting import anyway")

        # Parse transactions
        transactions = parse_csv_transactions(csv_file_path)

        return transactions
