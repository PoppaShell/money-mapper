"""Tests for api/validation.py -- CSV sanitization and input validation."""


class TestSanitizeCsvValue:
    """Test OWASP CSV injection prevention."""

    def test_equals_sign_prefixed(self):
        """Values starting with = get tab-prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("=SUM(A1:A10)") == "\t=SUM(A1:A10)"

    def test_plus_sign_prefixed(self):
        """Values starting with + get tab-prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("+1-555-1234") == "\t+1-555-1234"

    def test_at_sign_prefixed(self):
        """Values starting with @ get tab-prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("@import('evil')") == "\t@import('evil')"

    def test_dash_non_digit_prefixed(self):
        """Values starting with - followed by non-digit get tab-prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("-cmd('calc')") == "\t-cmd('calc')"

    def test_negative_number_not_prefixed(self):
        """Negative numbers like -5.00 should NOT be prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("-5.00") == "-5.00"
        assert sanitize_csv_value("-123") == "-123"
        assert sanitize_csv_value("-0.50") == "-0.50"

    def test_normal_string_unchanged(self):
        """Normal strings pass through unchanged."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("Starbucks") == "Starbucks"
        assert sanitize_csv_value("Walmart Supercenter") == "Walmart Supercenter"
        assert sanitize_csv_value("") == ""

    def test_dash_only_prefixed(self):
        """A bare dash with no following char gets prefixed."""
        from money_mapper.api.validation import sanitize_csv_value

        assert sanitize_csv_value("-") == "\t-"


class TestBuildCsvExport:
    """Test CSV export builder using csv module."""

    def test_header_row_present(self):
        """CSV output starts with header row."""
        from money_mapper.api.validation import build_csv_export

        result = build_csv_export([])
        assert result.startswith("date,merchant,amount,category")

    def test_single_transaction(self):
        """Single transaction produces one data row."""
        from money_mapper.api.validation import build_csv_export

        transactions = [
            {
                "date": "2026-01-15",
                "merchant_name": "Starbucks",
                "amount": -5.50,
                "category": "FOOD_AND_DRINK_COFFEE",
            }
        ]
        result = build_csv_export(transactions)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        assert "Starbucks" in lines[1]
        assert "-5.5" in lines[1]

    def test_comma_in_merchant_name(self):
        """Merchant names with commas are properly quoted by csv module."""
        import csv
        import io

        from money_mapper.api.validation import build_csv_export

        transactions = [
            {
                "date": "2026-01-15",
                "merchant_name": "Chick-fil-A, Inc.",
                "amount": -8.99,
                "category": "FOOD_AND_DRINK_RESTAURANT",
            }
        ]
        result = build_csv_export(transactions)
        # Parse it back to verify it's valid CSV
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][1] == "Chick-fil-A, Inc."

    def test_formula_injection_escaped(self):
        """Dangerous merchant names get tab-prefixed in CSV output."""
        from money_mapper.api.validation import build_csv_export

        transactions = [
            {
                "date": "2026-01-15",
                "merchant_name": "=cmd('calc')",
                "amount": -1.00,
                "category": "OTHER",
            }
        ]
        result = build_csv_export(transactions)
        assert "\t=cmd('calc')" in result

    def test_empty_transactions(self):
        """Empty list produces header-only CSV."""
        from money_mapper.api.validation import build_csv_export

        result = build_csv_export([])
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_missing_fields_use_defaults(self):
        """Transactions with missing fields use sensible defaults."""
        from money_mapper.api.validation import build_csv_export

        transactions = [{"date": "2026-01-15"}]
        result = build_csv_export(transactions)
        lines = result.strip().split("\n")
        assert len(lines) == 2
        # Should not crash, should have empty/default values
