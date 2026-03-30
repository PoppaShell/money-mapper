"""Tests for api/validation.py -- CSV sanitization and input validation."""

import os

import pytest


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


class TestValidateMerchantName:
    """Test merchant name validation."""

    def test_valid_name_passes(self):
        """Normal merchant name passes validation."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("Starbucks")
        assert valid is True
        assert result == "Starbucks"

    def test_empty_string_rejected(self):
        """Empty string is rejected."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("")
        assert valid is False
        assert "empty" in result.lower()

    def test_whitespace_only_rejected(self):
        """Whitespace-only string is rejected."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("   ")
        assert valid is False
        assert "empty" in result.lower()

    def test_too_long_rejected(self):
        """Names over 200 chars are rejected."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("A" * 201)
        assert valid is False
        assert "200" in result

    def test_exactly_200_chars_passes(self):
        """Names at exactly 200 chars pass."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("A" * 200)
        assert valid is True

    def test_control_characters_stripped(self):
        """Control characters (below 0x20 except space) are removed."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("Star\x00bucks\x01")
        assert valid is True
        assert result == "Starbucks"

    def test_spaces_preserved(self):
        """Spaces (0x20) are not stripped as control characters."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("Walmart Supercenter")
        assert valid is True
        assert result == "Walmart Supercenter"

    def test_leading_trailing_whitespace_stripped(self):
        """Leading and trailing whitespace is trimmed."""
        from money_mapper.api.validation import validate_merchant_name

        valid, result = validate_merchant_name("  Starbucks  ")
        assert valid is True
        assert result == "Starbucks"


class TestValidatePfcCategory:
    """Test PFC category validation with fuzzy suggestions."""

    @pytest.fixture
    def plaid_path(self):
        """Path to the real plaid_categories.toml file."""
        return os.path.join(os.path.dirname(__file__), "..", "config", "plaid_categories.toml")

    def test_exact_match_passes(self, plaid_path):
        """Exact PFC subcategory match passes."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("FOOD_AND_DRINK_RESTAURANT", plaid_path)
        assert valid is True
        assert suggestions == []

    def test_case_insensitive_match(self, plaid_path):
        """Category matching is case-insensitive."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("food_and_drink_restaurant", plaid_path)
        assert valid is True

    def test_invalid_returns_suggestions(self, plaid_path):
        """Invalid category returns close matches."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("FOOD_RESTAURANT", plaid_path)
        assert valid is False
        assert len(suggestions) > 0
        assert len(suggestions) <= 3

    def test_completely_wrong_no_suggestions(self, plaid_path):
        """Completely unrelated input may return empty suggestions."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("ZZZZXXXXXNOTACATEGORY", plaid_path)
        assert valid is False

    def test_empty_string_rejected(self, plaid_path):
        """Empty string is rejected."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("", plaid_path)
        assert valid is False

    def test_primary_category_format_accepted(self, plaid_path):
        """The subcategory key like BANK_FEES_ATM_FEES is accepted."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("BANK_FEES_ATM_FEES", plaid_path)
        assert valid is True

    def test_missing_plaid_file_returns_false(self):
        """Missing plaid file returns invalid with no suggestions."""
        from money_mapper.api.validation import validate_pfc_category

        valid, suggestions = validate_pfc_category("ANYTHING", "/nonexistent/path.toml")
        assert valid is False
        assert suggestions == []
