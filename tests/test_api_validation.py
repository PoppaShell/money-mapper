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
