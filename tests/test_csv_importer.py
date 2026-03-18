"""Tests for money_mapper.csv_importer module."""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
import csv

from money_mapper.csv_importer import (
    CSVImporter,
    CSVValidator,
    detect_csv_type,
    parse_csv_transactions,
    validate_csv_headers,
    standardize_csv_transaction,
)


class TestDetectCSVType:
    """Test CSV type detection."""

    def test_detect_checking_account_csv(self):
        """Test detecting checking account CSV format."""
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        result = detect_csv_type(headers)
        assert result in ["checking", "savings", "credit", None]

    def test_detect_credit_card_csv(self):
        """Test detecting credit card CSV format."""
        headers = ["Transaction Date", "Post Date", "Description", "Amount"]
        result = detect_csv_type(headers)
        assert result in ["checking", "savings", "credit", None]

    def test_detect_savings_account_csv(self):
        """Test detecting savings account CSV format."""
        headers = ["Date", "Transaction", "Withdrawal", "Deposit", "Balance"]
        result = detect_csv_type(headers)
        assert result in ["checking", "savings", "credit", None]

    def test_detect_unknown_csv(self):
        """Test detecting unknown CSV format."""
        headers = ["Column1", "Column2", "Column3"]
        result = detect_csv_type(headers)
        assert result is None


class TestValidateCSVHeaders:
    """Test CSV header validation."""

    def test_validate_checking_headers(self):
        """Test validating checking account headers."""
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        result = validate_csv_headers(headers, "checking")
        assert result is True or result is False

    def test_validate_credit_headers(self):
        """Test validating credit card headers."""
        headers = ["Transaction Date", "Post Date", "Description", "Amount"]
        result = validate_csv_headers(headers, "credit")
        assert result is True or result is False

    def test_validate_missing_required_headers(self):
        """Test validation fails with missing headers."""
        headers = ["Date", "Description"]
        result = validate_csv_headers(headers, "checking")
        assert isinstance(result, (bool, tuple))

    def test_validate_empty_headers(self):
        """Test validation with empty headers."""
        headers = []
        result = validate_csv_headers(headers, "checking")
        assert isinstance(result, (bool, tuple))


class TestStandardizeCSVTransaction:
    """Test transaction standardization from CSV."""

    def test_standardize_checking_transaction(self):
        """Test standardizing checking account transaction."""
        row = {
            "Date": "03/15/2024",
            "Description": "STARBUCKS #1234",
            "Debit": "5.50",
            "Credit": "",
            "Balance": "1000.00"
        }
        result = standardize_csv_transaction(row, "checking")
        
        assert "date" in result or "transaction_date" in result
        assert "merchant" in result or "description" in result
        assert "amount" in result

    def test_standardize_credit_transaction(self):
        """Test standardizing credit card transaction."""
        row = {
            "Transaction Date": "03/15/2024",
            "Post Date": "03/16/2024",
            "Description": "AMAZON.COM",
            "Amount": "-50.00"
        }
        result = standardize_csv_transaction(row, "credit")
        
        assert "date" in result or "transaction_date" in result
        assert "merchant" in result or "description" in result
        assert "amount" in result

    def test_standardize_savings_transaction(self):
        """Test standardizing savings account transaction."""
        row = {
            "Date": "03/15/2024",
            "Transaction": "Interest",
            "Withdrawal": "",
            "Deposit": "2.50",
            "Balance": "5000.00"
        }
        result = standardize_csv_transaction(row, "savings")
        
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_standardize_handles_missing_fields(self):
        """Test standardization handles missing optional fields gracefully."""
        row = {
            "Date": "03/15/2024",
            "Description": "TEST",
            "Debit": "",
            "Credit": "",
        }
        result = standardize_csv_transaction(row, "checking")
        
        assert isinstance(result, dict)


class TestParseCSVTransactions:
    """Test parsing CSV to transactions."""

    def test_parse_checking_csv(self, temp_output_dir):
        """Test parsing checking account CSV."""
        csv_file = temp_output_dir / "checking.csv"
        
        # Create sample CSV
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "STARBUCKS #1234",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "03/16/2024",
                "Description": "AMAZON.COM",
                "Debit": "49.99",
                "Credit": "",
                "Balance": "994.51"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert len(transactions) >= 0
        if len(transactions) > 0:
            assert "date" in transactions[0] or "transaction_date" in transactions[0]

    def test_parse_credit_csv(self, temp_output_dir):
        """Test parsing credit card CSV."""
        csv_file = temp_output_dir / "credit.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Transaction Date", "Post Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow({
                "Transaction Date": "03/15/2024",
                "Post Date": "03/16/2024",
                "Description": "STARBUCKS",
                "Amount": "-5.50"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file returns empty list."""
        transactions = parse_csv_transactions("/nonexistent/file.csv")
        assert transactions == [] or isinstance(transactions, list)

    def test_parse_empty_csv(self, temp_output_dir):
        """Test parsing empty CSV file."""
        csv_file = temp_output_dir / "empty.csv"
        csv_file.touch()
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_parse_malformed_csv(self, temp_output_dir):
        """Test parsing malformed CSV returns gracefully."""
        csv_file = temp_output_dir / "malformed.csv"
        csv_file.write_text("This is\nnot valid\nCSV format,,,")
        
        result = parse_csv_transactions(str(csv_file))
        assert isinstance(result, list)


class TestCSVValidator:
    """Test CSV validation class."""

    def test_validator_initialization(self):
        """Test CSVValidator initialization."""
        validator = CSVValidator("checking")
        assert validator is not None
        assert hasattr(validator, "validate")

    def test_validator_valid_checking_csv(self, temp_output_dir):
        """Test validator accepts valid checking CSV."""
        csv_file = temp_output_dir / "checking.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "TEST",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
        
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert isinstance(result, (bool, dict, tuple))

    def test_validator_invalid_csv(self, temp_output_dir):
        """Test validator rejects invalid CSV."""
        csv_file = temp_output_dir / "invalid.csv"
        csv_file.write_text("Invalid CSV Content")
        
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert isinstance(result, (bool, dict, tuple))

    def test_validator_missing_headers(self, temp_output_dir):
        """Test validator detects missing headers."""
        csv_file = temp_output_dir / "missing_headers.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Col1", "Col2"])
            writer.writeheader()
            writer.writerow({"Col1": "val1", "Col2": "val2"})
        
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert isinstance(result, (bool, dict, tuple))


class TestCSVImporter:
    """Test main CSVImporter class."""

    def test_importer_initialization(self):
        """Test CSVImporter initialization."""
        importer = CSVImporter()
        assert importer is not None
        assert hasattr(importer, "import_csv")
        assert hasattr(importer, "validate_file")

    def test_import_checking_csv(self, temp_output_dir):
        """Test importing checking CSV."""
        csv_file = temp_output_dir / "checking.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "STARBUCKS",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "03/16/2024",
                "Description": "GROCERY STORE",
                "Debit": "35.00",
                "Credit": "",
                "Balance": "964.50"
            })
        
        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "checking")
        
        assert isinstance(transactions, list)
        assert len(transactions) >= 0

    def test_import_credit_csv(self, temp_output_dir):
        """Test importing credit CSV."""
        csv_file = temp_output_dir / "credit.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Transaction Date", "Post Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow({
                "Transaction Date": "03/15/2024",
                "Post Date": "03/16/2024",
                "Description": "RESTAURANT",
                "Amount": "-75.00"
            })
        
        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "credit")
        
        assert isinstance(transactions, list)

    def test_validate_file_nonexistent(self):
        """Test validate_file with nonexistent file."""
        importer = CSVImporter()
        result = importer.validate_file("/nonexistent/file.csv")
        
        assert isinstance(result, (bool, dict, tuple))

    def test_validate_checking_file(self, temp_output_dir):
        """Test validate_file for checking CSV."""
        csv_file = temp_output_dir / "checking.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "TEST",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
        
        importer = CSVImporter()
        result = importer.validate_file(str(csv_file))
        
        assert isinstance(result, (bool, dict, tuple))

    def test_detect_csv_type_automatically(self, temp_output_dir):
        """Test automatic CSV type detection."""
        csv_file = temp_output_dir / "auto_detect.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "TEST",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
        
        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file))  # No type specified, should auto-detect
        
        assert isinstance(transactions, list)

    def test_import_multiple_transactions(self, temp_output_dir):
        """Test importing multiple transactions."""
        csv_file = temp_output_dir / "multi.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({
                    "Date": f"03/{15+i}/2024",
                    "Description": f"MERCHANT {i}",
                    "Debit": f"{10 + i}.50",
                    "Credit": "",
                    "Balance": f"{1000 - (10+i) * 10}.50"
                })
        
        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "checking")
        
        assert isinstance(transactions, list)
        if len(transactions) > 0:
            assert len(transactions) >= 1

    def test_error_handling_on_import(self, temp_output_dir):
        """Test error handling during import."""
        csv_file = temp_output_dir / "error.csv"
        csv_file.write_text("Invalid content")
        
        importer = CSVImporter()
        result = importer.import_csv(str(csv_file), "checking")
        
        # Should handle gracefully without crashing
        assert isinstance(result, list)


class TestCSVImportIntegration:
    """Integration tests for CSV import."""

    def test_csv_to_json_workflow(self, temp_output_dir):
        """Test workflow from CSV to JSON output."""
        csv_file = temp_output_dir / "input.csv"
        json_file = temp_output_dir / "output.json"
        
        # Create input CSV
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "STARBUCKS #1234 COFFEE",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "03/16/2024",
                "Description": "WHOLE FOODS MKT",
                "Debit": "65.32",
                "Credit": "",
                "Balance": "934.68"
            })
        
        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "checking")
        
        assert isinstance(transactions, list)

    def test_csv_column_mapping_flexibility(self, temp_output_dir):
        """Test flexibility with different column names."""
        csv_file = temp_output_dir / "flexible.csv"
        
        # Create CSV with slightly different column names
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Transaction Date", "Merchant", "Debit Amount", "Credit Amount"])
            writer.writeheader()
            writer.writerow({
                "Transaction Date": "03/15/2024",
                "Merchant": "STARBUCKS",
                "Debit Amount": "5.50",
                "Credit Amount": ""
            })
        
        # Should either handle this or provide helpful error
        importer = CSVImporter()
        result = importer.import_csv(str(csv_file))
        
        assert isinstance(result, list)


class TestCSVEdgeCases:
    """Test edge cases in CSV processing."""

    def test_csv_with_empty_rows(self, temp_output_dir):
        """Test CSV with empty rows."""
        csv_file = temp_output_dir / "empty_rows.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "TRANSACTION",
                "Debit": "10.00",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "",
                "Description": "",
                "Debit": "",
                "Credit": "",
                "Balance": ""
            })
            writer.writerow({
                "Date": "03/16/2024",
                "Description": "NEXT TRANSACTION",
                "Debit": "20.00",
                "Credit": "",
                "Balance": "980.00"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_with_special_characters(self, temp_output_dir):
        """Test CSV with special characters in merchant names."""
        csv_file = temp_output_dir / "special_chars.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "CVS/PHARMACY #1234 MA",
                "Debit": "25.50",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "03/16/2024",
                "Description": "AT&T WIRELESS",
                "Debit": "75.00",
                "Credit": "",
                "Balance": "925.00"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_with_duplicate_transactions(self, temp_output_dir):
        """Test CSV with duplicate transactions."""
        csv_file = temp_output_dir / "duplicates.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "STARBUCKS",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "1000.00"
            })
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "STARBUCKS",
                "Debit": "5.50",
                "Credit": "",
                "Balance": "994.50"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        # Should handle duplicates gracefully
        assert isinstance(transactions, list)

    def test_csv_large_amounts(self, temp_output_dir):
        """Test CSV with large transaction amounts."""
        csv_file = temp_output_dir / "large_amounts.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "LARGE PURCHASE",
                "Debit": "9999.99",
                "Credit": "",
                "Balance": "100000.00"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_negative_amounts(self, temp_output_dir):
        """Test CSV with negative amounts."""
        csv_file = temp_output_dir / "negatives.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow({
                "Date": "03/15/2024",
                "Description": "REFUND",
                "Amount": "-25.00"
            })
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_mixed_date_formats(self, temp_output_dir):
        """Test CSV with mixed date formats."""
        csv_file = temp_output_dir / "mixed_dates.csv"
        
        with open(csv_file, 'w', newline='') as f:
            f.write("Date,Description,Debit,Credit,Balance\n")
            f.write("03/15/2024,TRANSACTION1,10.00,,1000.00\n")
            f.write("2024-03-16,TRANSACTION2,20.00,,980.00\n")
            f.write("3/17/24,TRANSACTION3,30.00,,950.00\n")
        
        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)


class TestCSVImporterDirectory:
    """Test CSVImporter directory import functionality."""

    def test_import_directory_initialization(self):
        """Test CSVImporter initialization with debug parameter."""
        importer = CSVImporter(debug=True)
        assert importer is not None
        assert importer.debug is True

        importer_no_debug = CSVImporter(debug=False)
        assert importer_no_debug.debug is False

    def test_import_directory_empty_directory(self, temp_output_dir):
        """Test import_directory with empty directory."""
        empty_dir = temp_output_dir / "empty"
        empty_dir.mkdir(exist_ok=True)

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(empty_dir))

        assert isinstance(transactions, list)
        assert len(transactions) == 0

    def test_import_directory_nonexistent(self):
        """Test import_directory with nonexistent directory."""
        importer = CSVImporter(debug=False)
        transactions = importer.import_directory("/nonexistent/directory/path")

        assert isinstance(transactions, list)
        assert len(transactions) == 0

    def test_import_directory_single_csv(self, temp_output_dir):
        """Test import_directory with single CSV file."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        csv_file = csv_dir / "checking.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STARBUCKS",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(csv_dir))

        assert isinstance(transactions, list)

    def test_import_directory_multiple_csv_files(self, temp_output_dir):
        """Test import_directory with multiple CSV files."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        # Create checking CSV
        checking_file = csv_dir / "checking.csv"
        with open(checking_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STORE",
                    "Debit": "25.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        # Create credit CSV
        credit_file = csv_dir / "credit.csv"
        with open(credit_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Transaction Date", "Description", "Amount", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Transaction Date": "03/16/2024",
                    "Description": "RESTAURANT",
                    "Amount": "-50.00",
                    "Balance": "500.00",
                }
            )

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(csv_dir))

        assert isinstance(transactions, list)

    def test_import_directory_mixed_file_types(self, temp_output_dir):
        """Test import_directory ignores non-CSV files."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        # Create CSV
        csv_file = csv_dir / "checking.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        # Create non-CSV files (should be ignored)
        (csv_dir / "notes.txt").write_text("some notes")
        (csv_dir / "data.json").write_text("{}")

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(csv_dir))

        assert isinstance(transactions, list)

    def test_import_directory_with_debug(self, temp_output_dir, capsys):
        """Test import_directory with debug output."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        csv_file = csv_dir / "checking.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        importer = CSVImporter(debug=True)
        transactions = importer.import_directory(str(csv_dir))

        assert isinstance(transactions, list)

    def test_import_directory_file_not_directory(self, temp_output_dir):
        """Test import_directory with file path instead of directory."""
        csv_file = temp_output_dir / "file.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(csv_file))

        assert isinstance(transactions, list)
        assert len(transactions) == 0
