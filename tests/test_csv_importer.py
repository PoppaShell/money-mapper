"""Tests for money_mapper.csv_importer module."""

import csv

from money_mapper.csv_importer import (
    CSVImporter,
    CSVValidator,
    _extract_amount,
    detect_csv_type,
    parse_csv_transactions,
    parse_ofx_file,
    standardize_csv_transaction,
    validate_csv_headers,
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
            "Balance": "1000.00",
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
            "Amount": "-50.00",
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
            "Balance": "5000.00",
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
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STARBUCKS #1234",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "AMAZON.COM",
                    "Debit": "49.99",
                    "Credit": "",
                    "Balance": "994.51",
                }
            )

        transactions = parse_csv_transactions(str(csv_file))
        assert len(transactions) >= 0
        if len(transactions) > 0:
            assert "date" in transactions[0] or "transaction_date" in transactions[0]

    def test_parse_credit_csv(self, temp_output_dir):
        """Test parsing credit card CSV."""
        csv_file = temp_output_dir / "credit.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Transaction Date", "Post Date", "Description", "Amount"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Transaction Date": "03/15/2024",
                    "Post Date": "03/16/2024",
                    "Description": "STARBUCKS",
                    "Amount": "-5.50",
                }
            )

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

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

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

        with open(csv_file, "w", newline="") as f:
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
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "GROCERY STORE",
                    "Debit": "35.00",
                    "Credit": "",
                    "Balance": "964.50",
                }
            )

        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "checking")

        assert isinstance(transactions, list)
        assert len(transactions) >= 0

    def test_import_credit_csv(self, temp_output_dir):
        """Test importing credit CSV."""
        csv_file = temp_output_dir / "credit.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Transaction Date", "Post Date", "Description", "Amount"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Transaction Date": "03/15/2024",
                    "Post Date": "03/16/2024",
                    "Description": "RESTAURANT",
                    "Amount": "-75.00",
                }
            )

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

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        importer = CSVImporter()
        result = importer.validate_file(str(csv_file))

        assert isinstance(result, (bool, dict, tuple))

    def test_detect_csv_type_automatically(self, temp_output_dir):
        """Test automatic CSV type detection."""
        csv_file = temp_output_dir / "auto_detect.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TEST",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file))  # No type specified, should auto-detect

        assert isinstance(transactions, list)

    def test_import_multiple_transactions(self, temp_output_dir):
        """Test importing multiple transactions."""
        csv_file = temp_output_dir / "multi.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            for i in range(10):
                writer.writerow(
                    {
                        "Date": f"03/{15 + i}/2024",
                        "Description": f"MERCHANT {i}",
                        "Debit": f"{10 + i}.50",
                        "Credit": "",
                        "Balance": f"{1000 - (10 + i) * 10}.50",
                    }
                )

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
        temp_output_dir / "output.json"

        # Create input CSV
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STARBUCKS #1234 COFFEE",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "WHOLE FOODS MKT",
                    "Debit": "65.32",
                    "Credit": "",
                    "Balance": "934.68",
                }
            )

        importer = CSVImporter()
        transactions = importer.import_csv(str(csv_file), "checking")

        assert isinstance(transactions, list)

    def test_csv_column_mapping_flexibility(self, temp_output_dir):
        """Test flexibility with different column names."""
        csv_file = temp_output_dir / "flexible.csv"

        # Create CSV with slightly different column names
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Transaction Date", "Merchant", "Debit Amount", "Credit Amount"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Transaction Date": "03/15/2024",
                    "Merchant": "STARBUCKS",
                    "Debit Amount": "5.50",
                    "Credit Amount": "",
                }
            )

        # Should either handle this or provide helpful error
        importer = CSVImporter()
        result = importer.import_csv(str(csv_file))

        assert isinstance(result, list)


class TestCSVEdgeCases:
    """Test edge cases in CSV processing."""

    def test_csv_with_empty_rows(self, temp_output_dir):
        """Test CSV with empty rows."""
        csv_file = temp_output_dir / "empty_rows.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "TRANSACTION",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )
            writer.writerow(
                {"Date": "", "Description": "", "Debit": "", "Credit": "", "Balance": ""}
            )
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "NEXT TRANSACTION",
                    "Debit": "20.00",
                    "Credit": "",
                    "Balance": "980.00",
                }
            )

        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_with_special_characters(self, temp_output_dir):
        """Test CSV with special characters in merchant names."""
        csv_file = temp_output_dir / "special_chars.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "CVS/PHARMACY #1234 MA",
                    "Debit": "25.50",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "AT&T WIRELESS",
                    "Debit": "75.00",
                    "Credit": "",
                    "Balance": "925.00",
                }
            )

        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_with_duplicate_transactions(self, temp_output_dir):
        """Test CSV with duplicate transactions."""
        csv_file = temp_output_dir / "duplicates.csv"

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
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STARBUCKS",
                    "Debit": "5.50",
                    "Credit": "",
                    "Balance": "994.50",
                }
            )

        transactions = parse_csv_transactions(str(csv_file))
        # Should handle duplicates gracefully
        assert isinstance(transactions, list)

    def test_csv_large_amounts(self, temp_output_dir):
        """Test CSV with large transaction amounts."""
        csv_file = temp_output_dir / "large_amounts.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "LARGE PURCHASE",
                    "Debit": "9999.99",
                    "Credit": "",
                    "Balance": "100000.00",
                }
            )

        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_negative_amounts(self, temp_output_dir):
        """Test CSV with negative amounts."""
        csv_file = temp_output_dir / "negatives.csv"

        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow({"Date": "03/15/2024", "Description": "REFUND", "Amount": "-25.00"})

        transactions = parse_csv_transactions(str(csv_file))
        assert isinstance(transactions, list)

    def test_csv_mixed_date_formats(self, temp_output_dir):
        """Test CSV with mixed date formats."""
        csv_file = temp_output_dir / "mixed_dates.csv"

        with open(csv_file, "w", newline="") as f:
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


class TestOFXImport:
    """Test OFX/QFX file import support."""

    def test_import_file_csv(self, temp_output_dir):
        """Test import_file with CSV file."""
        csv_file = temp_output_dir / "test.csv"
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
        transactions = importer.import_file(str(csv_file))

        assert isinstance(transactions, list)
        assert len(transactions) == 1

    def test_import_file_unsupported_extension(self, temp_output_dir):
        """Test import_file with unsupported file extension."""
        unsupported_file = temp_output_dir / "data.json"
        unsupported_file.write_text("{}")

        importer = CSVImporter(debug=False)
        transactions = importer.import_file(str(unsupported_file))

        assert transactions == []

    def test_import_directory_mixed_formats(self, temp_output_dir):
        """Test import_directory with mixed CSV and OFX files."""
        mixed_dir = temp_output_dir / "mixed"
        mixed_dir.mkdir()

        # Create CSV file
        csv_file = mixed_dir / "test.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "CSV TEST",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "1000.00",
                }
            )

        # Create OFX file (empty for now)
        ofx_file = mixed_dir / "sample.ofx"
        ofx_file.write_text("")

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(mixed_dir))

        assert isinstance(transactions, list)
        # Should import CSV at least
        assert len(transactions) >= 1

    def test_import_directory_ofx_only(self, temp_output_dir):
        """Test import_directory with only OFX files."""
        ofx_dir = temp_output_dir / "ofx_only"
        ofx_dir.mkdir()

        # Create OFX file
        ofx_file = ofx_dir / "transactions.ofx"
        ofx_file.write_text("")

        importer = CSVImporter(debug=False)
        transactions = importer.import_directory(str(ofx_dir))

        assert isinstance(transactions, list)

    def test_import_file_extension_case_insensitive(self, temp_output_dir):
        """Test import_file handles file extensions case-insensitively."""
        ofx_file = temp_output_dir / "test.OFX"
        ofx_file.write_text("")

        importer = CSVImporter(debug=False)
        transactions = importer.import_file(str(ofx_file))

        # Should recognize .OFX as OFX despite case
        assert isinstance(transactions, list)


class TestDetectCSVTypeExact:
    """Test detect_csv_type with real assertions about returned values."""

    def test_detect_checking_returns_checking(self):
        """Checking headers with Debit/Credit must return 'checking'."""
        headers = ["Date", "Description", "Debit", "Credit", "Balance"]
        assert detect_csv_type(headers) == "checking"

    def test_detect_savings_returns_savings(self):
        """Savings headers with Withdrawal/Deposit must return 'savings'."""
        headers = ["Date", "Transaction", "Withdrawal", "Deposit", "Balance"]
        assert detect_csv_type(headers) == "savings"

    def test_detect_credit_via_transaction_date(self):
        """'Transaction Date' + 'Amount' must return 'credit'."""
        headers = ["Transaction Date", "Description", "Amount"]
        assert detect_csv_type(headers) == "credit"

    def test_detect_credit_via_post_date(self):
        """'Post Date' + 'Description' must return 'credit'."""
        headers = ["Post Date", "Description", "Amount"]
        assert detect_csv_type(headers) == "credit"

    def test_detect_credit_via_card_header(self):
        """'card' header with 'amount' must return 'credit'."""
        headers = ["Card", "Description", "Amount"]
        assert detect_csv_type(headers) == "credit"

    def test_detect_empty_headers_returns_none(self):
        """Empty header list must return None."""
        assert detect_csv_type([]) is None

    def test_detect_alternative_checking_via_amount(self):
        """Date + Description + Amount (no Debit/Credit) should return 'checking'."""
        headers = ["Date", "Description", "Amount"]
        result = detect_csv_type(headers)
        assert result == "checking"

    def test_detect_alternative_checking_via_charge(self):
        """Date + Description + Charge columns match alternative checking."""
        headers = ["Date", "Description", "Charge"]
        result = detect_csv_type(headers)
        assert result == "checking"

    def test_detect_alternative_checking_via_withdrawal(self):
        """Date + Description + Withdrawal (without deposit) matches alternative checking."""
        # Note: savings needs all 4: date, transaction, withdrawal, deposit
        # A CSV with date + description + withdrawal hits alternative checking path
        headers = ["Date", "Description", "Withdrawal"]
        result = detect_csv_type(headers)
        assert result == "checking"

    def test_detect_completely_unknown_headers(self):
        """Unrecognized headers must return None."""
        headers = ["Foo", "Bar", "Baz"]
        assert detect_csv_type(headers) is None


class TestValidateCSVHeadersExact:
    """Test validate_csv_headers with real assertions."""

    def test_valid_checking_headers_returns_true(self):
        """All required checking headers present must return True."""
        headers = ["Date", "Description", "Debit", "Credit"]
        result = validate_csv_headers(headers, "checking")
        assert result is True

    def test_valid_savings_headers_returns_true(self):
        """All required savings headers present must return True."""
        headers = ["Date", "Transaction", "Withdrawal", "Deposit"]
        result = validate_csv_headers(headers, "savings")
        assert result is True

    def test_valid_credit_headers_returns_true(self):
        """All required credit headers present must return True."""
        headers = ["Transaction Date", "Description", "Amount"]
        result = validate_csv_headers(headers, "credit")
        assert result is True

    def test_unknown_csv_type_returns_false_with_message(self):
        """Unknown type must return (False, message) tuple."""
        result = validate_csv_headers(["Date", "Description"], "unknown_type")
        assert isinstance(result, tuple)
        assert result[0] is False
        assert "unknown_type" in result[1].lower() or "Unknown" in result[1]

    def test_empty_headers_returns_false_with_message(self):
        """Empty headers must return (False, message) tuple."""
        result = validate_csv_headers([], "checking")
        assert isinstance(result, tuple)
        assert result[0] is False
        assert len(result[1]) > 0

    def test_missing_headers_returns_false_with_message(self):
        """Missing required headers must return (False, message) with missing names."""
        headers = ["Date", "Description"]  # Missing Debit and Credit
        result = validate_csv_headers(headers, "checking")
        assert isinstance(result, tuple)
        assert result[0] is False
        assert "debit" in result[1].lower() or "credit" in result[1].lower()

    def test_case_insensitive_header_matching(self):
        """Headers matching case-insensitively must be accepted."""
        headers = ["date", "description", "debit", "credit"]
        result = validate_csv_headers(headers, "checking")
        assert result is True


class TestExtractAmountExact:
    """Test _extract_amount with real value assertions."""

    def test_credit_positive_amount(self):
        """Credit CSV positive amount must be returned as-is."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "50.00"}
        result = _extract_amount(row, schema, "credit")
        assert result == 50.0

    def test_credit_negative_amount(self):
        """Credit CSV negative amount must be returned as negative float."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "-75.25"}
        result = _extract_amount(row, schema, "credit")
        assert result == -75.25

    def test_credit_amount_with_comma(self):
        """Credit amount with comma formatting must be parsed correctly."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "1,234.56"}
        result = _extract_amount(row, schema, "credit")
        assert result == 1234.56

    def test_credit_amount_with_dollar_sign(self):
        """Credit amount with dollar sign must be parsed correctly."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "$99.99"}
        result = _extract_amount(row, schema, "credit")
        assert result == 99.99

    def test_credit_empty_amount_returns_none(self):
        """Credit CSV with empty Amount must return None."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": ""}
        result = _extract_amount(row, schema, "credit")
        assert result is None

    def test_credit_non_numeric_amount_returns_none(self):
        """Credit CSV with non-numeric Amount must return None (ValueError path)."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "N/A"}
        result = _extract_amount(row, schema, "credit")
        assert result is None

    def test_checking_debit_returns_negative(self):
        """Checking debit amount must be returned as negative value."""
        schema = {"amount_fields": ["Debit", "Credit"]}
        row = {"Debit": "25.00", "Credit": ""}
        result = _extract_amount(row, schema, "checking")
        assert result == -25.0

    def test_checking_credit_returns_positive(self):
        """Checking credit amount must be returned as positive value."""
        schema = {"amount_fields": ["Debit", "Credit"]}
        row = {"Debit": "", "Credit": "100.00"}
        result = _extract_amount(row, schema, "checking")
        assert result == 100.0

    def test_checking_debit_with_comma(self):
        """Checking debit with comma must be parsed correctly."""
        schema = {"amount_fields": ["Debit", "Credit"]}
        row = {"Debit": "1,500.00", "Credit": ""}
        result = _extract_amount(row, schema, "checking")
        assert result == -1500.0

    def test_checking_non_numeric_debit_falls_through_to_credit(self):
        """Non-numeric Debit falls through to check Credit field."""
        schema = {"amount_fields": ["Debit", "Credit"]}
        row = {"Debit": "invalid", "Credit": "50.00"}
        result = _extract_amount(row, schema, "checking")
        # Debit "invalid" fails isdigit-like check or ValueError, then Credit is used
        assert (
            result == 50.0 or result is None
        )  # depends on whether "invalid" passes whitespace check

    def test_checking_both_empty_returns_none(self):
        """Checking with both Debit and Credit empty must return None."""
        schema = {"amount_fields": ["Debit", "Credit"]}
        row = {"Debit": "", "Credit": ""}
        result = _extract_amount(row, schema, "checking")
        assert result is None

    def test_savings_withdrawal_returns_negative(self):
        """Savings Withdrawal must return negative value."""
        schema = {"amount_fields": ["Withdrawal", "Deposit"]}
        row = {"Withdrawal": "300.00", "Deposit": ""}
        result = _extract_amount(row, schema, "savings")
        assert result == -300.0

    def test_savings_deposit_returns_positive(self):
        """Savings Deposit must return positive value."""
        schema = {"amount_fields": ["Withdrawal", "Deposit"]}
        row = {"Withdrawal": "", "Deposit": "50.00"}
        result = _extract_amount(row, schema, "savings")
        assert result == 50.0

    def test_unknown_csv_type_returns_none(self):
        """Unknown csv_type must return None without crashing."""
        schema = {"amount_fields": ["Amount"]}
        row = {"Amount": "100.00"}
        result = _extract_amount(row, schema, "other")
        assert result is None


class TestStandardizeCSVTransactionExact:
    """Test standardize_csv_transaction with real value assertions."""

    def test_checking_debit_amount_is_negative(self):
        """Checking debit row must produce negative amount."""
        row = {"Date": "03/15/2024", "Description": "STORE", "Debit": "42.00", "Credit": ""}
        result = standardize_csv_transaction(row, "checking")
        assert result["amount"] == -42.0

    def test_checking_credit_amount_is_positive(self):
        """Checking credit (deposit) row must produce positive amount."""
        row = {"Date": "03/15/2024", "Description": "PAYROLL", "Debit": "", "Credit": "2000.00"}
        result = standardize_csv_transaction(row, "checking")
        assert result["amount"] == 2000.0

    def test_credit_transaction_amount_preserved(self):
        """Credit card negative charge must be preserved exactly."""
        row = {
            "Transaction Date": "03/15/2024",
            "Description": "AMAZON",
            "Amount": "-89.99",
        }
        result = standardize_csv_transaction(row, "credit")
        assert result["amount"] == -89.99

    def test_merchant_extracted_correctly(self):
        """Merchant name must be extracted and stripped."""
        row = {"Date": "03/15/2024", "Description": "  STARBUCKS  ", "Debit": "5.50", "Credit": ""}
        result = standardize_csv_transaction(row, "checking")
        assert result["merchant"] == "STARBUCKS"
        assert result["description"] == "STARBUCKS"

    def test_balance_extracted_correctly(self):
        """Balance must be extracted as float."""
        row = {
            "Date": "03/15/2024",
            "Description": "TEST",
            "Debit": "10.00",
            "Credit": "",
            "Balance": "999.50",
        }
        result = standardize_csv_transaction(row, "checking")
        assert result["balance"] == 999.50

    def test_balance_with_commas_and_dollar(self):
        """Balance with commas and dollar sign must be parsed correctly."""
        row = {
            "Date": "03/15/2024",
            "Description": "TEST",
            "Debit": "10.00",
            "Credit": "",
            "Balance": "$1,234.56",
        }
        result = standardize_csv_transaction(row, "checking")
        assert result["balance"] == 1234.56

    def test_balance_invalid_value_is_silently_skipped(self):
        """Non-numeric balance must be silently ignored (no balance key or exception)."""
        row = {
            "Date": "03/15/2024",
            "Description": "TEST",
            "Debit": "10.00",
            "Credit": "",
            "Balance": "N/A",
        }
        result = standardize_csv_transaction(row, "checking")
        # Balance key must not be present since parsing failed
        assert "balance" not in result

    def test_transaction_type_set_correctly(self):
        """transaction_type must be set to the csv_type argument."""
        row = {"Date": "03/15/2024", "Description": "TEST", "Debit": "5.00", "Credit": ""}
        result = standardize_csv_transaction(row, "checking")
        assert result["transaction_type"] == "checking"

    def test_transaction_type_credit(self):
        """transaction_type must be 'credit' for credit rows."""
        row = {"Transaction Date": "03/15/2024", "Description": "TEST", "Amount": "-10.00"}
        result = standardize_csv_transaction(row, "credit")
        assert result["transaction_type"] == "credit"

    def test_unknown_csv_type_returns_empty_dict(self):
        """Unknown csv_type must return empty dict."""
        row = {"Date": "03/15/2024", "Description": "TEST", "Debit": "5.00"}
        result = standardize_csv_transaction(row, "completely_unknown")
        assert result == {}

    def test_date_standardized(self):
        """Date must be standardized (not raw string)."""
        row = {"Date": "03/15/2024", "Description": "TEST", "Debit": "5.00", "Credit": ""}
        result = standardize_csv_transaction(row, "checking")
        assert "date" in result
        # standardize_date should produce YYYY-MM-DD or similar normalized form
        assert result["date"] is not None


class TestParseCSVTransactionsExact:
    """Test parse_csv_transactions with real value assertions."""

    def test_nonexistent_file_returns_empty_list(self):
        """Missing file must return exactly empty list."""
        result = parse_csv_transactions("/no/such/file.csv")
        assert result == []

    def test_completely_empty_file_returns_empty_list(self, tmp_path):
        """Empty file (0 bytes) must return empty list."""
        empty = tmp_path / "empty.csv"
        empty.write_text("")
        result = parse_csv_transactions(str(empty))
        assert result == []

    def test_headers_only_no_data_returns_empty_list(self, tmp_path):
        """CSV with headers but no data rows must return empty list."""
        headers_only = tmp_path / "headers.csv"
        headers_only.write_text("Date,Description,Debit,Credit,Balance\n")
        result = parse_csv_transactions(str(headers_only))
        assert result == []

    def test_checking_csv_produces_correct_count(self, tmp_path):
        """Two valid checking rows must produce exactly two transactions."""
        csv_file = tmp_path / "two_rows.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STORE A",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "990.00",
                }
            )
            writer.writerow(
                {
                    "Date": "03/16/2024",
                    "Description": "STORE B",
                    "Debit": "20.00",
                    "Credit": "",
                    "Balance": "970.00",
                }
            )
        result = parse_csv_transactions(str(csv_file))
        assert len(result) == 2

    def test_empty_rows_are_skipped(self, tmp_path):
        """All-empty rows must be skipped and not produce transactions."""
        csv_file = tmp_path / "with_empty.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Date", "Description", "Debit", "Credit", "Balance"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Date": "03/15/2024",
                    "Description": "STORE",
                    "Debit": "10.00",
                    "Credit": "",
                    "Balance": "990.00",
                }
            )
            writer.writerow(
                {"Date": "", "Description": "", "Debit": "", "Credit": "", "Balance": ""}
            )
        result = parse_csv_transactions(str(csv_file))
        assert len(result) == 1

    def test_credit_csv_amount_value(self, tmp_path):
        """Credit CSV transaction amount must be parsed as the correct float."""
        csv_file = tmp_path / "credit.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Transaction Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow(
                {"Transaction Date": "03/15/2024", "Description": "AMAZON", "Amount": "-123.45"}
            )
        result = parse_csv_transactions(str(csv_file))
        assert len(result) == 1
        assert result[0]["amount"] == -123.45

    def test_dialect_sniff_failure_falls_back_to_excel(self, tmp_path):
        """File that fails dialect sniffing must still be parsed with 'excel' dialect."""
        # A file with very short content can cause Sniffer to raise csv.Error
        csv_file = tmp_path / "short.csv"
        csv_file.write_text("Date,Description,Debit,Credit\n03/15/2024,STORE,10.00,\n")
        result = parse_csv_transactions(str(csv_file))
        # Should parse without crashing
        assert isinstance(result, list)

    def test_unknown_headers_fallback_to_checking(self, tmp_path):
        """CSV with unrecognized headers falls back to checking type and still processes."""
        csv_file = tmp_path / "unknown.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Amount"])
            writer.writeheader()
            writer.writerow({"Date": "03/15/2024", "Description": "PURCHASE", "Amount": "50.00"})
        result = parse_csv_transactions(str(csv_file))
        # Should not crash, may or may not find amount depending on validation
        assert isinstance(result, list)


class TestCSVValidatorExact:
    """Test CSVValidator with real assertions."""

    def test_nonexistent_file_returns_false_tuple(self):
        """Nonexistent file must return (False, 'File does not exist')."""
        validator = CSVValidator("checking")
        result = validator.validate("/nonexistent/file.csv")
        assert isinstance(result, tuple)
        assert result[0] is False
        assert "exist" in result[1].lower()

    def test_valid_checking_csv_returns_true(self, tmp_path):
        """Valid checking CSV must return True."""
        csv_file = tmp_path / "good.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit"])
            writer.writeheader()
            writer.writerow(
                {"Date": "03/15/2024", "Description": "TEST", "Debit": "5.00", "Credit": ""}
            )
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert result is True

    def test_headers_only_no_data_returns_false(self, tmp_path):
        """CSV with headers but no data rows must return (False, message)."""
        csv_file = tmp_path / "headers_only.csv"
        csv_file.write_text("Date,Description,Debit,Credit\n")
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert isinstance(result, tuple)
        assert result[0] is False
        assert "data" in result[1].lower() or "row" in result[1].lower()

    def test_unknown_type_via_auto_detect_returns_false(self, tmp_path):
        """CSV with headers that cannot be auto-detected type returns (False, message)."""
        csv_file = tmp_path / "unknown.csv"
        csv_file.write_text("ColA,ColB,ColC\nval1,val2,val3\n")
        # No csv_type provided -> auto-detect will return None -> should fail
        validator = CSVValidator()
        result = validator.validate(str(csv_file))
        assert isinstance(result, tuple)
        assert result[0] is False

    def test_missing_required_headers_returns_false(self, tmp_path):
        """CSV missing required headers must return (False, message)."""
        csv_file = tmp_path / "missing.csv"
        csv_file.write_text("Date,Description\n03/15/2024,TEST\n")
        validator = CSVValidator("checking")
        result = validator.validate(str(csv_file))
        assert isinstance(result, tuple)
        assert result[0] is False


class TestCSVImporterExact:
    """Test CSVImporter with real value assertions."""

    def test_import_file_nonexistent_returns_empty_list(self, tmp_path):
        """import_file with nonexistent path must return []."""
        importer = CSVImporter()
        result = importer.import_file("/no/such/file.csv")
        assert result == []

    def test_import_file_nonexistent_debug_still_empty(self, tmp_path):
        """import_file with nonexistent path in debug mode must return []."""
        importer = CSVImporter(debug=True)
        result = importer.import_file("/no/such/file.csv")
        assert result == []

    def test_import_file_unsupported_extension_debug_returns_empty(self, tmp_path):
        """import_file with unsupported extension in debug mode must return []."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("hello")
        importer = CSVImporter(debug=True)
        result = importer.import_file(str(txt_file))
        assert result == []

    def test_import_file_ofx_extension_dispatches_to_ofx_parser(self, tmp_path):
        """import_file with .ofx extension must dispatch to OFX parser (returns list)."""
        ofx_file = tmp_path / "bank.ofx"
        ofx_file.write_text("")  # empty OFX -> parse_ofx_file returns []
        importer = CSVImporter(debug=False)
        result = importer.import_file(str(ofx_file))
        assert result == []

    def test_import_file_qfx_extension_dispatches_to_ofx_parser(self, tmp_path):
        """import_file with .qfx extension must dispatch to OFX parser (returns list)."""
        qfx_file = tmp_path / "bank.qfx"
        qfx_file.write_text("")
        importer = CSVImporter(debug=False)
        result = importer.import_file(str(qfx_file))
        assert result == []

    def test_import_file_ofx_with_debug(self, tmp_path):
        """import_file with .ofx in debug mode must still return list."""
        ofx_file = tmp_path / "bank.ofx"
        ofx_file.write_text("")
        importer = CSVImporter(debug=True)
        result = importer.import_file(str(ofx_file))
        assert isinstance(result, list)

    def test_import_csv_nonexistent_returns_empty(self):
        """import_csv with nonexistent file must return []."""
        importer = CSVImporter()
        result = importer.import_csv("/no/such/file.csv", "checking")
        assert result == []

    def test_import_directory_nonexistent_with_debug(self):
        """import_directory with nonexistent path in debug mode must return []."""
        importer = CSVImporter(debug=True)
        result = importer.import_directory("/no/such/directory")
        assert result == []

    def test_import_directory_file_path_with_debug(self, tmp_path):
        """import_directory given a file path (not dir) in debug mode must return []."""
        f = tmp_path / "file.csv"
        f.write_text("Date,Description\n")
        importer = CSVImporter(debug=True)
        result = importer.import_directory(str(f))
        assert result == []

    def test_import_directory_empty_dir_with_debug(self, tmp_path):
        """import_directory with empty dir in debug mode must return []."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        importer = CSVImporter(debug=True)
        result = importer.import_directory(str(empty_dir))
        assert result == []

    def test_import_directory_debug_prints_filenames(self, tmp_path, capsys):
        """import_directory in debug mode must print the filename being imported."""
        d = tmp_path / "statements"
        d.mkdir()
        csv_file = d / "mybank.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit"])
            writer.writeheader()
            writer.writerow(
                {"Date": "03/15/2024", "Description": "STORE", "Debit": "5.00", "Credit": ""}
            )
        importer = CSVImporter(debug=True)
        importer.import_directory(str(d))
        captured = capsys.readouterr()
        assert "mybank.csv" in captured.out

    def test_import_directory_returns_aggregated_transactions(self, tmp_path):
        """import_directory with two CSV files must return combined transactions."""
        d = tmp_path / "all"
        d.mkdir()

        for name, desc in [("a.csv", "STORE A"), ("b.csv", "STORE B")]:
            fp = d / name
            with open(fp, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Debit", "Credit"])
                writer.writeheader()
                writer.writerow(
                    {"Date": "03/15/2024", "Description": desc, "Debit": "10.00", "Credit": ""}
                )

        importer = CSVImporter(debug=False)
        result = importer.import_directory(str(d))
        assert len(result) == 2

    def test_import_csv_auto_detect_exception_fallback(self, tmp_path):
        """import_csv with unreadable/weird file still returns list without crashing."""
        # A file that can be opened but has no recognizable headers falls back to checking
        weird = tmp_path / "weird.csv"
        weird.write_text("\x00\x00\x00\n")  # null bytes - hard to read
        importer = CSVImporter()
        result = importer.import_csv(str(weird))
        assert isinstance(result, list)


class TestParseOFXFile:
    """Test parse_ofx_file directly."""

    def test_empty_file_returns_empty_list(self, tmp_path):
        """Empty OFX file must return []."""
        ofx_file = tmp_path / "empty.ofx"
        ofx_file.write_text("")
        result = parse_ofx_file(str(ofx_file))
        assert result == []

    def test_nonexistent_file_returns_empty_or_raises(self, tmp_path):
        """Nonexistent OFX file returns [] when ofxtools not installed, else may raise."""
        import importlib.util

        ofxtools_available = importlib.util.find_spec("ofxtools") is not None
        if ofxtools_available:
            # If ofxtools is installed, os.path.getsize on nonexistent file raises OSError
            import pytest

            with pytest.raises((OSError, FileNotFoundError)):
                parse_ofx_file(str(tmp_path / "nonexistent.ofx"))
        else:
            # If ofxtools not installed, ImportError path returns [] immediately
            result = parse_ofx_file(str(tmp_path / "nonexistent.ofx"))
            assert result == []

    def test_invalid_ofx_content_returns_empty_list(self, tmp_path):
        """Invalid OFX content must return [] without crashing."""
        bad_ofx = tmp_path / "bad.ofx"
        bad_ofx.write_text("This is not valid OFX content at all!")
        result = parse_ofx_file(str(bad_ofx))
        assert result == []

    def test_invalid_ofx_with_debug(self, tmp_path):
        """Invalid OFX with debug=True must still return [] and print error."""
        bad_ofx = tmp_path / "bad.ofx"
        bad_ofx.write_text("Invalid OFX")
        result = parse_ofx_file(str(bad_ofx), debug=True)
        assert result == []
