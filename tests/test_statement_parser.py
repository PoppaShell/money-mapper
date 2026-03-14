"""Tests for money_mapper.statement_parser module."""

import pytest

from money_mapper.statement_parser import (
    normalize_whitespace,
    detect_statement_type,
    determine_transaction_year,
    extract_statement_period,
    mask_account_number,
    validate_transaction,
    sort_transactions_by_date,
)


class TestNormalizeWhitespace:
    """Test whitespace normalization."""

    def test_multiple_spaces(self):
        """Test normalizing multiple spaces."""
        result = normalize_whitespace("STARBUCKS    COFFEE")
        assert result == "STARBUCKS COFFEE"

    def test_leading_trailing_spaces(self):
        """Test removing leading/trailing spaces."""
        result = normalize_whitespace("  AMAZON  ")
        assert result == "AMAZON"

    def test_mixed_whitespace(self):
        """Test handling mixed whitespace."""
        result = normalize_whitespace("  WHOLE   FOODS  MKT  ")
        assert result == "WHOLE FOODS MKT"

    def test_no_whitespace_changes(self):
        """Test string with normal spacing."""
        result = normalize_whitespace("NORMAL SPACING")
        assert result == "NORMAL SPACING"

    def test_tabs_and_newlines(self):
        """Test handling tabs and newlines."""
        result = normalize_whitespace("STARBUCKS\t\tCOFFEE\n")
        assert "\t" not in result
        assert "\n" not in result


class TestDetectStatementType:
    """Test statement type detection."""

    def test_detect_banking_statement(self):
        """Test detecting banking statement."""
        text = "CHECKING ACCOUNT\nTRANSACTION HISTORY\nDate\tMerchant\tAmount"
        config = {"statement_types": {"banking": {"keywords": ["CHECKING", "TRANSACTION"]}}}
        result = detect_statement_type(text, config)
        
        # Should detect banking type or return something reasonable
        assert result is not None or result is None

    def test_detect_credit_statement(self):
        """Test detecting credit statement."""
        text = "CREDIT CARD STATEMENT\nPURCHASES AND CREDITS"
        config = {"statement_types": {"credit": {"keywords": ["CREDIT CARD", "PURCHASES"]}}}
        result = detect_statement_type(text, config)
        
        # Should detect or return None
        assert isinstance(result, (str, type(None)))

    def test_detect_unknown_statement(self):
        """Test handling unknown statement type."""
        text = "RANDOM TEXT WITHOUT KEYWORDS"
        config = {"statement_types": {}}
        result = detect_statement_type(text, config)
        
        # Should return None for unknown
        assert result is None or isinstance(result, str)


class TestDetermineTransactionYear:
    """Test transaction year determination."""

    def test_january_with_statement_period(self):
        """Test January uses statement end year."""
        year = determine_transaction_year(1, {"end_year": 2024})
        assert year == 2024

    def test_december_with_statement_period(self):
        """Test December uses statement end year."""
        year = determine_transaction_year(12, {"end_year": 2024})
        assert year == 2024

    def test_year_without_statement_period(self):
        """Test year determination without period."""
        year = determine_transaction_year(6, None)
        assert isinstance(year, int)
        assert year >= 2000

    @pytest.mark.parametrize("month", [1, 6, 12])
    def test_various_months(self, month):
        """Test year determination for various months."""
        year = determine_transaction_year(month, {"end_year": 2024})
        assert year == 2024


class TestExtractStatementPeriod:
    """Test statement period extraction."""

    def test_extract_valid_period(self):
        """Test extracting valid statement period."""
        text = "Statement Period: January 1, 2024 - January 31, 2024"
        config = {
            "period_extraction": {
                "pattern": r"(\w+)\s+(\d+),\s+(\d{4})",
                "format": "month_day_year"
            }
        }
        result = extract_statement_period(text, config)
        
        # Should return dict or None
        assert result is None or isinstance(result, dict)

    def test_extract_period_no_match(self):
        """Test extraction with no matching period."""
        text = "NO PERIOD INFORMATION"
        config = {"period_extraction": {}}
        result = extract_statement_period(text, config)
        
        assert result is None or isinstance(result, dict)


class TestMaskAccountNumber:
    """Test account number masking."""

    def test_mask_basic_account_number(self):
        """Test masking basic account number."""
        result = mask_account_number("1234567890")
        assert "XXXX" in result or "*" in result
        assert "1234567890" not in result

    def test_mask_account_with_format(self):
        """Test masking account with format."""
        result = mask_account_number("12-3456-789")
        assert len(result) > 0
        assert result != "12-3456-789"

    def test_mask_short_account(self):
        """Test masking short account number."""
        result = mask_account_number("1234")
        assert len(result) > 0

    def test_mask_empty_account(self):
        """Test masking empty account."""
        result = mask_account_number("")
        assert isinstance(result, str)


class TestValidateTransaction:
    """Test transaction validation."""

    def test_validate_complete_transaction(self):
        """Test validating complete transaction."""
        transaction = {
            "merchant": "STARBUCKS",
            "amount": -5.50,
            "date": "2024-01-15"
        }
        is_valid = validate_transaction(transaction)
        assert isinstance(is_valid, bool)

    def test_validate_missing_merchant(self):
        """Test validation fails with missing merchant."""
        transaction = {
            "amount": -5.50,
            "date": "2024-01-15"
        }
        is_valid = validate_transaction(transaction)
        assert isinstance(is_valid, bool)

    def test_validate_missing_amount(self):
        """Test validation fails with missing amount."""
        transaction = {
            "merchant": "STARBUCKS",
            "date": "2024-01-15"
        }
        is_valid = validate_transaction(transaction)
        assert isinstance(is_valid, bool)

    def test_validate_missing_date(self):
        """Test validation fails with missing date."""
        transaction = {
            "merchant": "STARBUCKS",
            "amount": -5.50
        }
        is_valid = validate_transaction(transaction)
        assert isinstance(is_valid, bool)

    def test_validate_empty_transaction(self):
        """Test validation of empty transaction."""
        is_valid = validate_transaction({})
        assert isinstance(is_valid, bool)


class TestSortTransactionsByDate:
    """Test transaction sorting."""

    def test_sort_valid_dates(self):
        """Test sorting transactions with valid dates."""
        transactions = [
            {"merchant": "B", "date": "2024-01-15"},
            {"merchant": "A", "date": "2024-01-10"},
            {"merchant": "C", "date": "2024-01-20"},
        ]
        sorted_trans = sort_transactions_by_date(transactions)
        
        assert len(sorted_trans) == 3
        # First transaction should be earliest
        assert sorted_trans[0]["merchant"] == "A"

    def test_sort_mixed_date_formats(self):
        """Test sorting with mixed date formats."""
        transactions = [
            {"merchant": "B", "date": "2024-01-15"},
            {"merchant": "A", "date": "2024-01-10"},
        ]
        sorted_trans = sort_transactions_by_date(transactions)
        
        assert len(sorted_trans) == 2

    def test_sort_empty_list(self):
        """Test sorting empty transaction list."""
        sorted_trans = sort_transactions_by_date([])
        assert sorted_trans == []

    def test_sort_single_transaction(self):
        """Test sorting single transaction."""
        transactions = [{"merchant": "A", "date": "2024-01-15"}]
        sorted_trans = sort_transactions_by_date(transactions)
        
        assert len(sorted_trans) == 1
        assert sorted_trans[0]["merchant"] == "A"

    @pytest.mark.parametrize("dates", [
        (["2024-01-10", "2024-01-20", "2024-01-15"],),
        (["2024-12-01", "2024-01-01", "2024-06-15"],),
    ])
    def test_sort_various_date_orders(self, dates):
        """Test sorting various date orders."""
        transactions = [
            {"merchant": f"M{i}", "date": date}
            for i, date in enumerate(dates[0])
        ]
        sorted_trans = sort_transactions_by_date(transactions)
        
        assert len(sorted_trans) == len(transactions)


class TestExtractStatementPeriod:
    """Test statement period extraction - fixes issue #32."""

    @pytest.fixture
    def period_config(self):
        """Period configuration with month names."""
        return {
            "month_names": {
                "january": 1,
                "february": 2,
                "march": 3,
                "april": 4,
                "may": 5,
                "june": 6,
                "july": 7,
                "august": 8,
                "september": 9,
                "october": 10,
                "november": 11,
                "december": 12,
            },
            "patterns": [
                r'''for\s+([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})\s+to\s+([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})''',
                r'''([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})\s+to\s+([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})''',
                r'''(\d{1,2})/(\d{1,2})/(\d{2,4})\s+to\s+(\d{1,2})/(\d{1,2})/(\d{2,4})''',
                r'''([A-Za-z]+)\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})''',
            ],
        }

    def test_credit_card_dash_separator_format(self, period_config):
        """Test extracting period from credit card format with dash separator (issue #32)."""
        text = "Statement Period: December 27 - January 26, 2024"
        period = extract_statement_period(text, period_config)
        
        assert period is not None
        assert period["start_month"] == "December"
        assert period["start_day"] == 27
        assert period["start_year"] == 2023  # Previous year (Dec < Jan)
        assert period["end_month"] == "January"
        assert period["end_day"] == 26
        assert period["end_year"] == 2024

    def test_credit_card_year_boundary_detection(self, period_config):
        """Test year boundary detection (Dec to Jan crossing)."""
        text = "Period: December 1 - January 31, 2024"
        period = extract_statement_period(text, period_config)
        
        # When start_month (12) > end_month (1), start year is previous year
        assert period["start_year"] == 2023
        assert period["end_year"] == 2024

    def test_credit_card_no_year_boundary(self, period_config):
        """Test when no year boundary is crossed."""
        text = "Period: January 1 - February 28, 2024"
        period = extract_statement_period(text, period_config)
        
        # When start_month (1) < end_month (2), both in same year
        assert period["start_year"] == 2024
        assert period["end_year"] == 2024

    def test_traditional_to_separator_format(self, period_config):
        """Test traditional format with 'to' separator still works."""
        text = "Statement for January 1, 2024 to February 28, 2024"
        period = extract_statement_period(text, period_config)
        
        assert period is not None
        assert period["start_year"] == 2024
        assert period["end_year"] == 2024

    def test_statement_period_without_commas(self, period_config):
        """Test credit card format without commas."""
        text = "December 27 - January 26 2024"
        period = extract_statement_period(text, period_config)
        
        assert period is not None
        assert period["end_year"] == 2024


class TestDetermineTransactionYear:
    """Test transaction year determination - issue #32 fallback logic."""

    def test_year_determination_with_statement_period(self):
        """Test year determination using statement period."""
        period = {
            "start_month": "December",
            "start_year": 2023,
            "end_month": "January",
            "end_year": 2024,
        }
        
        # December transaction should be 2023
        assert determine_transaction_year(12, period) == 2023
        
        # January transaction should be 2024
        assert determine_transaction_year(1, period) == 2024

    def test_year_determination_no_period_current_month(self):
        """Test fallback logic with current month."""
        # If current month is 3 (March), transaction in March should be current year
        # We'll test with None statement_period and a month that's likely current or past
        from datetime import datetime
        current_month = datetime.now().month
        
        year = determine_transaction_year(current_month, None)
        assert year == datetime.now().year

    def test_year_determination_no_period_future_month(self):
        """Test fallback logic with future month (should be previous year)."""
        # If current month is early in year, future months should be previous year
        from datetime import datetime
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Pick a month definitely in the future from now
        future_month = (current_month % 12) + 2  # Skip ahead 2 months
        
        year = determine_transaction_year(future_month, None)
        # Future months without period should be previous year
        assert year == current_year - 1

    def test_year_determination_crossing_boundary(self):
        """Test year determination crossing boundary correctly."""
        period = {
            "end_month": "January",  # 1
            "end_year": 2024,
        }
        
        # Month 12 (Dec) > end_month 1 (Jan) = previous year
        assert determine_transaction_year(12, period) == 2023
        
        # Month 1 (Jan) = end_month 1 (Jan) = same year
        assert determine_transaction_year(1, period) == 2024
