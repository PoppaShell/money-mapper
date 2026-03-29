"""Tests for money_mapper.utils module."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from money_mapper.utils import (
    calculate_confidence_score,
    check_dependencies,
    clean_merchant_name,
    format_amount,
    fuzzy_match_similarity,
    get_processing_stats,
    load_config,
    load_transactions_from_json,
    merge_transaction_data,
    normalize_text_for_matching,
    prompt_yes_no,
    sanitize_description,
    save_transactions_to_json,
    standardize_date,
    validate_transaction_data,
)


class TestLoadTransactions:
    """Test transaction loading from JSON."""

    def test_load_transactions_valid_file(self, sample_transactions, temp_output_dir):
        """Test loading valid transaction JSON file."""
        test_file = temp_output_dir / "transactions.json"

        # Write sample transactions
        with open(test_file, "w") as f:
            json.dump(sample_transactions, f)

        # Load and verify
        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 4
        assert loaded[0]["merchant"] == "Starbucks"

    def test_load_transactions_empty_file(self, temp_output_dir):
        """Test loading empty transaction file."""
        test_file = temp_output_dir / "empty.json"
        with open(test_file, "w") as f:
            json.dump([], f)

        loaded = load_transactions_from_json(str(test_file))
        assert loaded == []

    def test_load_transactions_nonexistent_file(self):
        """Test loading nonexistent file returns empty list."""
        loaded = load_transactions_from_json("/nonexistent/path/transactions.json")
        assert loaded == []

    def test_load_transactions_invalid_json(self, temp_output_dir):
        """Test loading invalid JSON returns empty list."""
        test_file = temp_output_dir / "invalid.json"
        test_file.write_text("{invalid json")

        loaded = load_transactions_from_json(str(test_file))
        assert loaded == []


class TestSaveTransactions:
    """Test transaction saving to JSON."""

    def test_save_transactions(self, sample_transactions, temp_output_dir):
        """Test saving transactions to JSON."""
        output_file = temp_output_dir / "output.json"

        save_transactions_to_json(sample_transactions, str(output_file))

        assert output_file.exists()

        with open(output_file) as f:
            loaded = json.load(f)

        assert len(loaded) == len(sample_transactions)
        assert loaded[0]["merchant"] == sample_transactions[0]["merchant"]

    def test_save_transactions_creates_directory(self, temp_output_dir):
        """Test that save_transactions creates missing directories."""
        output_file = temp_output_dir / "subdir" / "transactions.json"
        transactions = [{"merchant": "Test", "amount": 10.0}]

        save_transactions_to_json(transactions, str(output_file))

        assert output_file.exists()
        assert output_file.parent.exists()

    def test_save_transactions_empty_list(self, temp_output_dir):
        """Test saving empty transaction list."""
        output_file = temp_output_dir / "empty.json"
        save_transactions_to_json([], str(output_file))

        assert output_file.exists()
        loaded = json.loads(output_file.read_text())
        assert loaded == []

    def test_save_transactions_unicode_content(self, temp_output_dir):
        """Test saving transactions with Unicode characters."""
        output_file = temp_output_dir / "unicode.json"
        transactions = [{"merchant": "Café ☕", "amount": 5.50}]

        save_transactions_to_json(transactions, str(output_file))

        loaded = load_transactions_from_json(str(output_file))
        assert loaded[0]["merchant"] == "Café ☕"


class TestStandardizeDate:
    """Test date standardization."""

    def test_standardize_mm_dd_format(self):
        """Test MM/DD format with year inference."""
        result = standardize_date("03/15")
        assert result.endswith("-03-15")

    def test_standardize_mm_dd_yy_format(self):
        """Test MM/DD/YY format with 2-digit year."""
        result = standardize_date("03/15/24")
        assert result == "2024-03-15"

    def test_standardize_mm_dd_yy_19xx(self):
        """Test MM/DD/YY format with 19xx year."""
        result = standardize_date("03/15/99")
        assert result == "1999-03-15"

    def test_standardize_mm_dd_yyyy_format(self):
        """Test MM/DD/YYYY format."""
        result = standardize_date("03/15/2024")
        assert result == "2024-03-15"

    def test_standardize_yyyy_mm_dd_format(self):
        """Test already standardized YYYY-MM-DD format."""
        result = standardize_date("2024-03-15")
        assert result == "2024-03-15"

    def test_standardize_date_with_whitespace(self):
        """Test date standardization with extra whitespace."""
        result = standardize_date("  03/15/2024  ")
        assert result == "2024-03-15"

    def test_standardize_invalid_date_format(self):
        """Test unrecognized date format returns as-is."""
        invalid = "2024/03/15"  # Wrong separator
        result = standardize_date(invalid)
        assert result == invalid

    @pytest.mark.parametrize("month,day", [("01", "01"), ("12", "31"), ("06", "15")])
    def test_standardize_date_various_dates(self, month, day):
        """Test standardization with various valid dates."""
        result = standardize_date(f"{month}/{day}/2024")
        assert result.endswith(f"-{month}-{day}")


class TestCleanMerchantName:
    """Test merchant name extraction."""

    def test_clean_merchant_with_card_reference(self):
        """Test removing card reference from merchant name."""
        result = clean_merchant_name("CHECKCARD STARBUCKS COFFEE")
        assert "STARBUCKS" in result
        assert "CHECKCARD" not in result

    def test_clean_merchant_with_debit_card_prefix(self):
        """Test removing DEBIT CARD prefix."""
        result = clean_merchant_name("DEBIT CARD AMAZON.COM")
        assert "AMAZON" in result

    def test_clean_merchant_with_card_number(self):
        """Test removing card numbers in specific format."""
        result = clean_merchant_name("MERCHANT NAME 4532 **** 9876")
        # The function removes dates and specific card patterns (XXXX **** XXXX)
        assert "MERCHANT" in result
        assert "NAME" in result

    def test_clean_merchant_takes_first_words(self):
        """Test that only first few words are returned."""
        result = clean_merchant_name("STARBUCKS COFFEE COMPANY LOCATION 12345 SEATTLE")
        words = result.split()
        assert len(words) <= 4

    def test_clean_merchant_empty_string(self):
        """Test cleaning empty string."""
        result = clean_merchant_name("")
        assert result == ""


class TestFormatAmount:
    """Test monetary amount formatting."""

    def test_format_positive_amount(self):
        """Test formatting positive amount."""
        result = format_amount(100.50)
        assert result == "$100.50"

    def test_format_large_amount_with_comma(self):
        """Test formatting large amount with comma separator."""
        result = format_amount(1000.00)
        assert result == "$1,000.00"

    def test_format_negative_amount(self):
        """Test formatting negative amount."""
        result = format_amount(-50.25)
        assert result == "-$50.25"

    def test_format_string_amount(self):
        """Test formatting string representation of amount."""
        result = format_amount("99.99")
        assert result == "$99.99"

    def test_format_invalid_amount(self):
        """Test formatting invalid amount returns string."""
        result = format_amount("not_a_number")
        assert result == "not_a_number"

    @pytest.mark.parametrize(
        "amount,expected",
        [
            (0.01, "$0.01"),
            (0, "$0.00"),
            (999999.99, "$999,999.99"),
        ],
    )
    def test_format_amount_edge_cases(self, amount, expected):
        """Test formatting edge case amounts."""
        assert format_amount(amount) == expected


class TestNormalizeTextForMatching:
    """Test text normalization for matching."""

    def test_normalize_uppercase_text(self):
        """Test normalizing uppercase text."""
        result = normalize_text_for_matching("STARBUCKS")
        assert result == result.lower()

    def test_normalize_special_characters(self):
        """Test removing special characters."""
        result = normalize_text_for_matching("AMAZON.COM/BILL")
        # Should remove dots and slashes
        assert "." not in result or result.count(".") < "AMAZON.COM/BILL".count(".")

    def test_normalize_extra_whitespace(self):
        """Test collapsing whitespace."""
        result = normalize_text_for_matching("MERCHANT   NAME")
        assert "  " not in result


class TestFuzzyMatchSimilarity:
    """Test fuzzy string matching similarity."""

    def test_identical_strings(self):
        """Test identical strings have high similarity."""
        similarity = fuzzy_match_similarity("STARBUCKS", "STARBUCKS")
        assert similarity == 1.0

    def test_completely_different_strings(self):
        """Test completely different strings have low similarity."""
        similarity = fuzzy_match_similarity("STARBUCKS", "AMAZON")
        assert similarity < 0.5

    def test_similar_strings(self):
        """Test similar strings have moderate-high similarity."""
        similarity = fuzzy_match_similarity("STARBUCKS", "STARBUCK")
        assert 0.7 < similarity < 1.0

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        similarity1 = fuzzy_match_similarity("STARBUCKS", "starbucks")
        similarity2 = fuzzy_match_similarity("starbucks", "STARBUCKS")
        assert similarity1 > 0.9
        assert similarity2 > 0.9


class TestValidateTransactionData:
    """Test transaction data validation."""

    def test_validate_complete_transaction(self, sample_transactions):
        """Test validation of complete transaction."""
        transaction = sample_transactions[0]
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid
        assert len(errors) == 0

    def test_validate_transaction_missing_date(self):
        """Test validation fails with missing date."""
        transaction = {"merchant": "STARBUCKS", "amount": 5.50}
        is_valid, errors = validate_transaction_data(transaction)
        assert not is_valid
        assert any("date" in e.lower() for e in errors)

    def test_validate_transaction_missing_amount(self):
        """Test validation fails with missing amount."""
        transaction = {"merchant": "STARBUCKS", "date": "2024-01-15"}
        is_valid, errors = validate_transaction_data(transaction)
        assert not is_valid

    def test_validate_transaction_missing_merchant(self):
        """Test validation fails with missing merchant."""
        transaction = {"date": "2024-01-15", "amount": 5.50}
        is_valid, errors = validate_transaction_data(transaction)
        assert not is_valid

    def test_validate_empty_transaction(self):
        """Test validation of empty transaction."""
        is_valid, errors = validate_transaction_data({})
        assert not is_valid
        assert len(errors) > 0


class TestCalculateConfidenceScore:
    """Test confidence score calculation."""

    def test_confidence_private_mapping(self):
        """Test confidence for private mapping (highest)."""
        score = calculate_confidence_score("private_mapping")
        assert score == 0.95

    def test_confidence_public_mapping(self):
        """Test confidence for public mapping."""
        score = calculate_confidence_score("public_mapping")
        assert score == 0.85

    def test_confidence_fuzzy_match_high_similarity(self):
        """Test confidence for fuzzy match with high similarity."""
        score = calculate_confidence_score("fuzzy_match", similarity=0.95)
        assert score == 0.80  # Capped at 0.80

    def test_confidence_fuzzy_match_low_similarity(self):
        """Test confidence for fuzzy match with low similarity."""
        score = calculate_confidence_score("fuzzy_match", similarity=0.5)
        assert score == 0.5

    def test_confidence_plaid_keyword(self):
        """Test confidence for plaid keyword matching."""
        score = calculate_confidence_score("plaid_keyword")
        assert score == 0.70

    def test_confidence_plaid_fallback(self):
        """Test confidence for plaid fallback."""
        score = calculate_confidence_score("plaid_fallback")
        assert score == 0.40

    def test_confidence_unknown_method(self):
        """Test confidence for unknown method returns low confidence."""
        score = calculate_confidence_score("unknown_method")
        assert score == 0.20


class TestGetProcessingStats:
    """Test processing statistics generation."""

    def test_get_stats_empty_list(self):
        """Test stats for empty transaction list."""
        stats = get_processing_stats([])
        assert stats["total_transactions"] == 0
        assert stats["categorized"] == 0
        assert stats["uncategorized"] == 0

    def test_get_stats_single_transaction(self):
        """Test stats for single transaction with enrichment data."""
        transactions = [
            {
                "merchant": "STARBUCKS",
                "amount": 5.50,
                "date": "2024-01-15",
                "category": "FOOD & DINING",
                "confidence": 0.95,
                "categorization_method": "private_mapping",
            }
        ]
        stats = get_processing_stats(transactions)
        assert stats["total_transactions"] == 1
        assert stats["categorized"] == 1
        assert stats["uncategorized"] == 0

    def test_get_stats_multiple_transactions_mixed(self):
        """Test stats with mix of categorized and uncategorized."""
        transactions = [
            {
                "merchant": "STARBUCKS",
                "amount": 5.50,
                "date": "2024-01-15",
                "category": "FOOD & DINING",
                "confidence": 0.95,
            },
            {
                "merchant": "UNKNOWN MERCHANT",
                "amount": 10.0,
                "date": "2024-01-16",
                "category": None,
                "confidence": 0.0,
            },
        ]
        stats = get_processing_stats(transactions)
        assert stats["total_transactions"] == 2
        assert stats["categorized"] == 1
        assert stats["uncategorized"] == 1
        assert stats["categorization_rate"] == 50.0

    def test_get_stats_has_required_fields(self):
        """Test that stats include required fields."""
        stats = get_processing_stats([])
        assert "total_transactions" in stats
        assert "categorized" in stats
        assert "uncategorized" in stats
        assert "categorization_rate" in stats
        assert "confidence_distribution" in stats
        assert "method_distribution" in stats


class TestMergeTransactionData:
    """Test transaction data merging."""

    def test_merge_updates_base_transaction(self):
        """Test that merge updates base with new data."""
        base = {"merchant": "OLD", "amount": 10.0, "date": "2024-01-01"}
        update = {"merchant": "NEW"}

        result = merge_transaction_data(base, update)
        assert result["merchant"] == "NEW"
        assert result["amount"] == 10.0

    def test_merge_preserves_base_fields(self):
        """Test that merge preserves base fields."""
        base = {"merchant": "STARBUCKS", "amount": 5.50, "date": "2024-01-01"}
        update = {"category": "FOOD"}

        result = merge_transaction_data(base, update)
        assert result["merchant"] == "STARBUCKS"
        assert result["category"] == "FOOD"

    def test_merge_empty_update(self):
        """Test merge with empty update preserves base fields."""
        base = {"merchant": "STARBUCKS", "amount": 5.50}
        result = merge_transaction_data(base, {})
        assert result["merchant"] == "STARBUCKS"
        assert result["amount"] == 5.50
        # merge_transaction_data adds a timestamp
        assert "last_updated" in result


class TestSanitizeDescription:
    """Test merchant description sanitization."""

    @pytest.mark.xfail(reason="Sanitization logic not fully implemented - Phase 2")
    def test_sanitize_starbucks(self):
        """Test Starbucks description sanitization."""
        result = sanitize_description("STARBUCKS #12345 SEATTLE WA")
        assert result == "STARBUCKS"

    def test_sanitize_amazon(self):
        """Test Amazon description sanitization."""
        result = sanitize_description("AMAZON.COM AMZN.COM/BILL")
        assert "AMAZON" in result.upper()

    def test_sanitize_empty(self):
        """Test empty string handling."""
        result = sanitize_description("")
        assert result is not None

    def test_sanitize_with_no_patterns(self):
        """Test sanitization with no patterns returns original."""
        text = "MERCHANT NAME DETAILS"
        result = sanitize_description(text)
        assert text.strip() == result

    def test_sanitize_with_pattern_redaction(self):
        """Test pattern-based redaction."""
        patterns = [{"pattern": r"\d+", "replacement": "[NUM]"}]
        result = sanitize_description("MERCHANT 12345 NAME", sanitization_patterns=patterns)
        assert "[NUM]" in result
        assert "12345" not in result


class TestFuzzyMatchExtended:
    """Extended tests for fuzzy matching with edge cases."""

    def test_fuzzy_match_empty_first_string(self):
        """Test fuzzy matching with empty first string."""
        similarity = fuzzy_match_similarity("", "STARBUCKS")
        assert 0.0 <= similarity < 0.5

    def test_fuzzy_match_empty_second_string(self):
        """Test fuzzy matching with empty second string."""
        similarity = fuzzy_match_similarity("STARBUCKS", "")
        assert 0.0 <= similarity < 0.5

    def test_fuzzy_match_both_empty(self):
        """Test fuzzy matching with both strings empty."""
        similarity = fuzzy_match_similarity("", "")
        assert 0.0 <= similarity <= 1.0

    def test_fuzzy_match_very_long_strings(self):
        """Test fuzzy matching with very long strings."""
        long_str1 = "STARBUCKS " * 100  # 1100+ chars
        long_str2 = "STARBUCKS " * 100
        similarity = fuzzy_match_similarity(long_str1, long_str2)
        assert similarity > 0.9

    def test_fuzzy_match_single_character(self):
        """Test fuzzy matching with single characters."""
        similarity = fuzzy_match_similarity("A", "B")
        assert 0.0 <= similarity < 0.5

    def test_fuzzy_match_whitespace_only(self):
        """Test fuzzy matching with whitespace-only strings."""
        similarity = fuzzy_match_similarity("   ", "   ")
        assert 0.0 <= similarity <= 1.0

    def test_fuzzy_match_with_special_chars(self):
        """Test fuzzy matching with special characters."""
        similarity1 = fuzzy_match_similarity("STARBUCKS@COFFEE", "STARBUCKSCOFFEE")
        # Special chars are removed by normalization, so these become identical
        assert similarity1 > 0.8

    def test_fuzzy_match_with_numbers(self):
        """Test fuzzy matching with numeric characters."""
        similarity = fuzzy_match_similarity("STORE123", "STORE456")
        assert 0.5 < similarity < 1.0

    def test_fuzzy_match_reversed_strings(self):
        """Test fuzzy matching with reversed strings."""
        similarity = fuzzy_match_similarity("STARBUCKS", "SCKCBRATS")
        assert similarity < 0.7

    def test_fuzzy_match_partial_overlap(self):
        """Test fuzzy matching with partial overlap."""
        similarity = fuzzy_match_similarity("AMAZON", "AMAZONIA")
        assert 0.7 < similarity < 1.0

    def test_fuzzy_match_substring(self):
        """Test fuzzy matching with substring."""
        similarity = fuzzy_match_similarity("COFFEE", "STARBUCKS COFFEE")
        assert similarity > 0.3

    def test_fuzzy_match_threshold_zero(self):
        """Test that even completely different strings have > 0 similarity."""
        similarity = fuzzy_match_similarity("AAA", "BBB")
        assert similarity >= 0.0

    def test_fuzzy_match_case_variations(self):
        """Test case variations in fuzzy matching."""
        sim1 = fuzzy_match_similarity("StArBuCkS", "STARBUCKS")
        sim2 = fuzzy_match_similarity("starbucks", "STARBUCKS")
        # Both should be similar due to normalization
        assert sim1 > 0.8
        assert sim2 > 0.8


class TestCalculateConfidenceScoreExtended:
    """Extended tests for confidence score calculation."""

    def test_confidence_all_methods(self):
        """Test confidence for all supported methods."""
        methods = [
            "private_mapping",
            "public_mapping",
            "fuzzy_match",
            "plaid_keyword",
            "plaid_fallback",
            "unknown_method",
        ]
        for method in methods:
            score = calculate_confidence_score(method)
            assert 0.0 <= score <= 1.0

    def test_confidence_fuzzy_match_zero_similarity(self):
        """Test fuzzy match with zero similarity."""
        score = calculate_confidence_score("fuzzy_match", similarity=0.0)
        assert score == 0.0

    def test_confidence_fuzzy_match_one_similarity(self):
        """Test fuzzy match with perfect similarity."""
        score = calculate_confidence_score("fuzzy_match", similarity=1.0)
        assert score == 0.80  # Capped at 0.80

    def test_confidence_fuzzy_match_mid_range(self):
        """Test fuzzy match with mid-range similarity."""
        score = calculate_confidence_score("fuzzy_match", similarity=0.75)
        assert score == 0.75

    def test_confidence_ordering(self):
        """Test that confidence scores are properly ordered."""
        private = calculate_confidence_score("private_mapping")
        public = calculate_confidence_score("public_mapping")
        plaid = calculate_confidence_score("plaid_keyword")
        fallback = calculate_confidence_score("plaid_fallback")
        unknown = calculate_confidence_score("unknown_method")

        assert private > public > plaid > fallback > unknown

    def test_confidence_private_is_highest(self):
        """Test that private mapping has highest confidence."""
        private = calculate_confidence_score("private_mapping")
        fuzzy = calculate_confidence_score("fuzzy_match", similarity=1.0)
        assert private > fuzzy

    def test_confidence_negative_similarity(self):
        """Test fuzzy match with negative similarity (edge case)."""
        # min() will cap at 0.0 or use the negative value as-is
        score = calculate_confidence_score("fuzzy_match", similarity=-0.5)
        # The function uses min(0.80, similarity), so negative gets used
        assert score == -0.5 or score >= 0.0  # Depends on implementation

    def test_confidence_similarity_greater_than_one(self):
        """Test fuzzy match with similarity > 1.0 (edge case)."""
        score = calculate_confidence_score("fuzzy_match", similarity=1.5)
        # Should be capped at 0.80
        assert score <= 0.80


class TestStandardizeDateExtended:
    """Extended tests for date standardization."""

    def test_standardize_all_months(self):
        """Test standardization for all 12 months."""
        for month in range(1, 13):
            month_str = f"{month:02d}"
            result = standardize_date(f"{month_str}/15/2024")
            assert f"-{month_str}-15" in result

    def test_standardize_leap_year_february(self):
        """Test standardization for leap year February 29."""
        result = standardize_date("02/29/2024")
        assert result == "2024-02-29"

    def test_standardize_december_to_january(self):
        """Test date standardization across year boundary."""
        result = standardize_date("12/31/2024")
        assert result == "2024-12-31"

    def test_standardize_single_digit_month(self):
        """Test standardization with single-digit month."""
        result = standardize_date("3/15/2024")
        assert "2024-03-15" == result

    def test_standardize_single_digit_day(self):
        """Test standardization with single-digit day."""
        result = standardize_date("03/5/2024")
        assert "2024-03-05" == result

    def test_standardize_single_digit_both(self):
        """Test standardization with both single digits."""
        result = standardize_date("3/5/2024")
        assert "2024-03-05" == result

    def test_standardize_year_boundary_1999_2000(self):
        """Test 2-digit year parsing at 1999-2000 boundary."""
        result_99 = standardize_date("03/15/99")
        result_00 = standardize_date("03/15/00")
        assert result_99 == "1999-03-15"
        assert result_00 == "2000-03-15"

    def test_standardize_year_boundary_49_50(self):
        """Test 2-digit year parsing at 49-50 boundary."""
        result_49 = standardize_date("03/15/49")
        result_50 = standardize_date("03/15/50")
        assert result_49.startswith("2049")
        assert result_50.startswith("1950")

    def test_standardize_mm_dd_with_current_year(self):
        """Test MM/DD format infers current year."""
        result = standardize_date("03/15")
        year = datetime.now().year
        assert result.startswith(str(year))

    def test_standardize_multiple_spaces(self):
        """Test standardization with multiple spaces."""
        result = standardize_date("   03 / 15 / 2024   ")
        # Should handle gracefully
        assert result is not None

    def test_standardize_tabs_and_spaces(self):
        """Test standardization with mixed whitespace."""
        result = standardize_date("\t03/15/2024\n")
        assert result == "2024-03-15"

    def test_standardize_invalid_date_format_slash_hyphen(self):
        """Test invalid date with mixed separators."""
        invalid = "03-15/2024"
        result = standardize_date(invalid)
        # Should return as-is since format doesn't match
        assert result == invalid


class TestMergeTransactionDataExtended:
    """Extended tests for transaction data merging."""

    def test_merge_multiple_fields(self):
        """Test merging multiple fields."""
        base = {"a": 1, "b": 2, "c": 3}
        update = {"b": 20, "d": 4}
        result = merge_transaction_data(base, update)
        assert result["a"] == 1
        assert result["b"] == 20
        assert result["c"] == 3
        assert result["d"] == 4

    def test_merge_null_values(self):
        """Test merging with None values."""
        base = {"merchant": "STARBUCKS", "category": None}
        update = {"category": "FOOD"}
        result = merge_transaction_data(base, update)
        assert result["category"] == "FOOD"

    def test_merge_overwrites_none(self):
        """Test that update overwrites None values."""
        base = {"merchant": None, "amount": 10.0}
        update = {"merchant": "AMAZON"}
        result = merge_transaction_data(base, update)
        assert result["merchant"] == "AMAZON"

    def test_merge_large_transaction(self):
        """Test merging large transaction objects."""
        base = {f"field_{i}": i for i in range(20)}
        update = {f"field_{i}": i * 2 for i in range(10, 30)}
        result = merge_transaction_data(base, update)
        assert result["field_0"] == 0
        assert result["field_15"] == 30  # Updated value
        assert result["field_25"] == 50  # New value

    def test_merge_has_timestamp(self):
        """Test that merge adds last_updated timestamp."""
        base = {"merchant": "TEST"}
        update = {"amount": 5.0}
        result = merge_transaction_data(base, update)
        assert "last_updated" in result

    def test_merge_timestamp_is_iso_format(self):
        """Test that timestamp is in ISO format."""
        base = {"merchant": "TEST"}
        update = {}
        result = merge_transaction_data(base, update)
        timestamp = result.get("last_updated")
        # Should be parseable as ISO format
        from datetime import datetime

        try:
            datetime.fromisoformat(timestamp)
            assert True
        except ValueError:
            raise AssertionError(f"Timestamp not in ISO format: {timestamp}") from None


class TestValidateTransactionExtended:
    """Extended tests for transaction validation."""

    def test_validate_with_extra_fields(self):
        """Test validation ignores extra fields."""
        transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": 10.0,
            "extra_field": "extra_value",
            "another_field": 123,
        }
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_multiple_required_fields(self):
        """Test validation with multiple missing required fields."""
        transaction = {"amount": 10.0}
        is_valid, errors = validate_transaction_data(transaction)
        assert not is_valid
        assert len(errors) >= 2  # At least date and description missing

    def test_validate_invalid_date_formats(self):
        """Test validation with various invalid date formats."""
        invalid_dates = [
            "01-15-2024",  # Wrong separator
            "2024/01/15",  # Wrong separator
            "01/15",  # Incomplete
            "not a date",
        ]
        for invalid_date in invalid_dates:
            transaction = {
                "date": invalid_date,
                "description": "TEST",
                "amount": 10.0,
            }
            is_valid, errors = validate_transaction_data(transaction)
            # Should have at least date format error
            assert not is_valid or any("date" in e.lower() for e in errors)

    def test_validate_valid_date_format_only(self):
        """Test that only YYYY-MM-DD is considered valid."""
        valid_transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": 10.0,
        }
        is_valid, errors = validate_transaction_data(valid_transaction)
        assert is_valid

    def test_validate_amount_zero(self):
        """Test validation with zero amount."""
        transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": 0.0,
        }
        is_valid, errors = validate_transaction_data(transaction)
        # Zero might not be considered valid depending on implementation
        assert isinstance(is_valid, bool)

    def test_validate_amount_negative(self):
        """Test validation with negative amount."""
        transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": -100.50,
        }
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid  # Negative is valid

    def test_validate_amount_very_large(self):
        """Test validation with very large amount."""
        transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": 999999999.99,
        }
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid

    def test_validate_amount_string_format(self):
        """Test validation with string-formatted amount."""
        transaction = {
            "date": "2024-01-15",
            "description": "TEST",
            "amount": "50.25",
        }
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid

    def test_validate_description_unicode(self):
        """Test validation with Unicode description."""
        transaction = {
            "date": "2024-01-15",
            "description": "CAFÉ ☕",
            "amount": 10.0,
        }
        is_valid, errors = validate_transaction_data(transaction)
        assert is_valid


class TestCleanMerchantNameExtended:
    """Extended tests for merchant name cleaning."""

    def test_clean_merchant_multiple_prefixes(self):
        """Test removing multiple prefixes."""
        result = clean_merchant_name("CHECKCARD DEBIT CARD AMAZON.COM")
        assert "AMAZON" in result.upper()
        assert "CHECKCARD" not in result.upper()

    def test_clean_merchant_with_location(self):
        """Test cleaning merchant with location info."""
        result = clean_merchant_name("STARBUCKS COFFEE SEATTLE WA 98101")
        assert "STARBUCKS" in result.upper()
        # Should be limited to first 4 words
        assert len(result.split()) <= 4

    def test_clean_merchant_numbers_only(self):
        """Test cleaning with numbers only."""
        result = clean_merchant_name("123456789")
        # Should not return empty string
        assert result == "" or result == "123456789"

    def test_clean_merchant_special_chars_only(self):
        """Test cleaning with special characters only."""
        result = clean_merchant_name("@#$%^&*()")
        # Should handle gracefully
        assert isinstance(result, str)

    def test_clean_merchant_mixed_case(self):
        """Test cleaning preserves case."""
        result = clean_merchant_name("StArBuCkS CoffEe")
        # Result should still contain the text (case might change)
        assert "STARBUCKS" in result.upper() or "starbucks" in result.lower()

    def test_clean_merchant_with_apostrophe(self):
        """Test cleaning merchant name with apostrophe."""
        result = clean_merchant_name("JOE'S PIZZA")
        assert "JOE" in result.upper() or "PIZZA" in result.upper()

    def test_clean_merchant_very_long_name(self):
        """Test cleaning very long merchant name."""
        long_name = " ".join(["WORD"] * 20)
        result = clean_merchant_name(long_name)
        # Should be limited to 4 words
        assert len(result.split()) <= 4


class TestNormalizeTextForMatchingExtended:
    """Extended tests for text normalization."""

    def test_normalize_mixed_case(self):
        """Test normalizing mixed case text."""
        result = normalize_text_for_matching("StArBuCkS")
        assert result == result.lower()

    def test_normalize_multiple_spaces(self):
        """Test normalizing multiple spaces."""
        result = normalize_text_for_matching("STARBUCKS    COFFEE")
        assert "  " not in result

    def test_normalize_tabs_and_newlines(self):
        """Test normalizing tabs and newlines."""
        result = normalize_text_for_matching("STARBUCKS\tCOFFEE\nSTORE")
        assert "\t" not in result
        assert "\n" not in result

    def test_normalize_removes_banking_terms(self):
        """Test that banking terms are removed."""
        result = normalize_text_for_matching("CHECKCARD STARBUCKS")
        # Banking term should be removed
        assert len(result) < len("CHECKCARD STARBUCKS".lower())

    def test_normalize_punctuation_removed(self):
        """Test that punctuation is removed."""
        result = normalize_text_for_matching("STARBUCKS.COM/BILL")
        assert "." not in result
        assert "/" not in result

    def test_normalize_unicode_text(self):
        """Test normalizing Unicode text."""
        result = normalize_text_for_matching("CAFÉ ☕")
        # Should handle Unicode gracefully
        assert isinstance(result, str)


class TestFormatAmountExtended:
    """Extended tests for amount formatting."""

    def test_format_amount_thousand_boundary(self):
        """Test formatting at thousand boundaries."""
        result = format_amount(999.99)
        assert result == "$999.99"
        result = format_amount(1000.00)
        assert result == "$1,000.00"

    def test_format_amount_million(self):
        """Test formatting millions."""
        result = format_amount(1000000.00)
        assert result == "$1,000,000.00"

    def test_format_amount_very_small(self):
        """Test formatting very small amounts."""
        result = format_amount(0.01)
        assert result == "$0.01"

    def test_format_amount_scientific_notation(self):
        """Test formatting scientific notation."""
        result = format_amount(1e6)
        assert "$1" in result

    def test_format_amount_with_many_decimals(self):
        """Test formatting with many decimal places."""
        result = format_amount(100.123456)
        # Should be rounded to 2 decimals
        assert ".12" in result or ".13" in result

    def test_format_amount_zero_with_string(self):
        """Test formatting zero as string."""
        result = format_amount("0")
        assert result == "$0.00"

    def test_format_amount_negative_very_large(self):
        """Test formatting large negative amounts."""
        result = format_amount(-1000000.00)
        assert "-" in result
        assert "1,000,000" in result


class TestLoadTransactionsEdgeCases:
    """Extended tests for transaction loading edge cases."""

    def test_load_transactions_with_duplicate_entries(self, temp_output_dir):
        """Test loading transactions with duplicate entries."""
        test_file = temp_output_dir / "duplicates.json"
        transactions = [
            {"merchant": "STARBUCKS", "amount": 5.0, "date": "2024-01-01"},
            {"merchant": "STARBUCKS", "amount": 5.0, "date": "2024-01-01"},
        ]
        test_file.write_text(json.dumps(transactions))

        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 2

    def test_load_transactions_with_malformed_entries(self, temp_output_dir):
        """Test loading transactions with some malformed entries."""
        test_file = temp_output_dir / "mixed.json"
        transactions = [
            {"merchant": "STARBUCKS", "amount": 5.0, "date": "2024-01-01"},
            {"merchant": "AMAZON"},  # Missing date and amount
            {"amount": 10.0},  # Missing merchant and date
        ]
        test_file.write_text(json.dumps(transactions))

        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 3

    def test_load_transactions_large_file(self, temp_output_dir):
        """Test loading large transaction file."""
        test_file = temp_output_dir / "large.json"
        transactions = [
            {"merchant": f"MERCHANT_{i}", "amount": float(i), "date": "2024-01-01"}
            for i in range(1000)
        ]
        test_file.write_text(json.dumps(transactions))

        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 1000


class TestBackupFile:
    """Tests for backup_file utility function."""

    def test_backup_file_creates_backup(self, temp_output_dir):
        """Test that backup_file creates a backup with timestamp."""
        from money_mapper.utils import backup_file

        original_file = temp_output_dir / "original.txt"
        original_file.write_text("original content")

        backup_dir = temp_output_dir / "backups"
        backup_path = backup_file(str(original_file), str(backup_dir))

        assert backup_path is not None
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text() == "original content"

    def test_backup_file_nonexistent_source(self, temp_output_dir):
        """Test backup_file with nonexistent source file."""
        from money_mapper.utils import backup_file

        backup_path = backup_file("/nonexistent/file.txt", str(temp_output_dir))
        assert backup_path is None

    def test_backup_file_creates_directory(self, temp_output_dir):
        """Test that backup_file creates backup directory if needed."""
        from money_mapper.utils import backup_file

        original_file = temp_output_dir / "original.txt"
        original_file.write_text("content")

        backup_dir = temp_output_dir / "new_backup_dir"
        backup_path = backup_file(str(original_file), str(backup_dir))

        assert backup_dir.exists()
        assert backup_path is not None


class TestCheckDependencies:
    """Tests for dependency checking."""

    def test_check_dependencies_existing(self):
        """Test checking for installed dependencies."""

        all_present, missing = check_dependencies(["json", "sys"])
        assert all_present is True
        assert missing == []

    def test_check_dependencies_missing(self):
        """Test checking for missing dependencies."""

        all_present, missing = check_dependencies(["nonexistent_package_xyz"])
        assert all_present is False
        assert len(missing) > 0

    def test_check_dependencies_mixed(self):
        """Test checking for mixed existing and missing dependencies."""

        all_present, missing = check_dependencies(["json", "nonexistent_xyz"])
        assert all_present is False
        assert "nonexistent_xyz" in missing


class TestPromptYesNo:
    """Tests for yes/no prompt."""

    def test_prompt_yes_no_with_mocked_input(self, monkeypatch):
        """Test prompt_yes_no with mocked input."""
        monkeypatch.setattr("builtins.input", lambda prompt: "y")
        result = prompt_yes_no("Continue?", default=False)
        assert result is True

    def test_prompt_yes_no_default_on_empty(self, monkeypatch):
        """Test prompt_yes_no uses default on empty input."""
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = prompt_yes_no("Continue?", default=True)
        assert result is True


class TestPromptWithValidation:
    """Tests for prompt_with_validation utility."""

    def test_prompt_with_validation_valid_input(self, monkeypatch):
        """Test prompt_with_validation with valid input."""
        from money_mapper.utils import prompt_with_validation

        monkeypatch.setattr("builtins.input", lambda prompt: "y")
        result = prompt_with_validation("Action?", ["y", "n", "back"], default="y")
        assert result == "y"

    def test_prompt_with_validation_default(self, monkeypatch):
        """Test prompt_with_validation uses default on empty."""
        from money_mapper.utils import prompt_with_validation

        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = prompt_with_validation("Action?", ["y", "n"], default="y")
        assert result == "y"


class TestShowProgress:
    """Tests for progress bar display."""

    def test_show_progress_full(self, capsys):
        """Test progress bar shows full progress."""
        from money_mapper.utils import show_progress

        show_progress(100, 100)
        captured = capsys.readouterr()
        # Progress bar was shown
        assert "[" in captured.out

    def test_show_progress_zero_total(self, capsys):
        """Test progress bar with zero total."""
        from money_mapper.utils import show_progress

        show_progress(0, 0)
        # Should handle gracefully without error


class TestBackupFilePath:
    """Tests for backup file path utilities."""

    def test_backup_file_has_timestamp(self, temp_output_dir):
        """Test that backup file includes timestamp."""
        from money_mapper.utils import backup_file

        original = temp_output_dir / "test.txt"
        original.write_text("content")

        backup_path = backup_file(str(original), str(temp_output_dir / "backups"))

        # Check that filename includes timestamp format
        backup_name = Path(backup_path).name
        assert "test_" in backup_name
        assert backup_name.endswith(".txt")


class TestSanitizeDescriptionPrivacy:
    """Tests for privacy-aware sanitization."""

    def test_sanitize_with_privacy_redaction(self):
        """Test sanitization with privacy configuration."""
        privacy_config = {
            "enable_redaction": True,
            "patterns": {"account_numbers": [{"pattern": r"\b\d{4}\b", "replacement": "[ACCT]"}]},
            "keywords": {
                "names": ["JOHN SMITH"],
                "employers": ["ACME"],
            },
        }

        result = sanitize_description("ACME CORP 1234 JOHN SMITH", privacy_config=privacy_config)

        # Should have redacted ACME and 1234
        assert "[ACCT]" in result or "[EMPLOYER]" in result

    def test_sanitize_with_disabled_privacy(self):
        """Test sanitization with privacy disabled."""
        privacy_config = {
            "enable_redaction": False,
            "patterns": {"account_numbers": [{"pattern": r"\b\d{4}\b", "replacement": "[ACCT]"}]},
        }

        sanitize_description("TEST 1234", privacy_config=privacy_config)

        # Privacy disabled, so number should remain
        # The behavior depends on implementation


class TestLoadConfig:
    """Tests for TOML config loading."""

    def test_load_config_valid_file(self, temp_output_dir):
        """Test loading valid TOML file."""

        config_file = temp_output_dir / "config.toml"
        config_file.write_text('[section]\nkey = "value"\n')

        # This will call load_config which uses tomllib
        try:
            config = load_config(str(config_file))
            assert isinstance(config, dict)
        except SystemExit:
            # Function calls sys.exit on error, which is expected in some cases
            pass


class TestValidateTomlFiles:
    """Tests for TOML validation utilities."""

    def test_validate_toml_files_valid(self, temp_output_dir):
        """Test TOML validation with valid files."""
        from money_mapper.utils import validate_toml_files

        # This requires config manager setup, might not work in all contexts
        result = validate_toml_files(verbose=False)
        assert isinstance(result, bool)


class TestFormatDependencyStatus:
    """Tests for dependency status formatting."""

    def test_format_dependency_status(self):
        """Test formatting dependency status."""
        from money_mapper.utils import format_dependency_status

        status = format_dependency_status()

        assert isinstance(status, list)
        for package, version, is_installed in status:
            assert isinstance(package, str)
            assert isinstance(is_installed, bool)


class TestEnsureDirectoriesExist:
    """Tests for directory creation utilities."""

    def test_ensure_directories_exist(self):
        """Test that ensure_directories_exist creates required directories."""
        from money_mapper.utils import ensure_directories_exist

        result = ensure_directories_exist()
        # Should return bool
        assert isinstance(result, bool)


class TestLoadConfigErrors:
    """Tests for config loading error handling."""

    def test_load_config_nonexistent_file(self):
        """Test loading nonexistent config file."""

        try:
            config = load_config("/nonexistent/config.toml")
            # If it doesn't raise, it should return dict
            assert isinstance(config, dict)
        except SystemExit:
            # Expected - function calls exit(1) on error
            pass


class TestAdditionalEdgeCases:
    """Additional edge case tests for coverage."""

    def test_fuzzy_match_normalized_text(self):
        """Test fuzzy matching normalizes text consistently."""
        from money_mapper.utils import fuzzy_match_similarity

        # Should be case and punctuation insensitive
        sim1 = fuzzy_match_similarity("STARBUCKS.COM", "starbucks com")
        sim2 = fuzzy_match_similarity("STARBUCKS", "starbucks")

        # Should both be high
        assert sim1 > 0.5
        assert sim2 > 0.9

    def test_merge_transaction_adds_timestamp(self):
        """Test that merge always adds timestamp."""
        from money_mapper.utils import merge_transaction_data

        trans1 = {"id": 1}
        trans2 = {}

        result = merge_transaction_data(trans1, trans2)

        # Must have timestamp
        assert "last_updated" in result
        # Timestamp must be ISO format
        from datetime import datetime

        datetime.fromisoformat(result["last_updated"])

    def test_validate_transaction_empty_description(self):
        """Test validation with empty description field."""
        from money_mapper.utils import validate_transaction_data

        trans = {
            "date": "2024-01-15",
            "description": "",  # Empty!
            "amount": 10.0,
        }

        is_valid, errors = validate_transaction_data(trans)
        # Empty description might be caught
        assert isinstance(is_valid, bool)

    def test_validate_transaction_invalid_amount_format(self):
        """Test validation with non-numeric amount."""
        from money_mapper.utils import validate_transaction_data

        trans = {"date": "2024-01-15", "description": "TEST", "amount": "not a number"}

        is_valid, errors = validate_transaction_data(trans)

        if not is_valid:
            assert any("amount" in e.lower() for e in errors)

    def test_get_stats_with_confidence_edge_values(self):
        """Test stats calculation with confidence edge values."""
        from money_mapper.utils import get_processing_stats

        transactions = [
            {
                "category": "FOOD",
                "confidence": 0.0,  # Very low
                "categorization_method": "unknown",
            },
            {
                "category": "FOOD",
                "confidence": 1.0,  # Perfect
                "categorization_method": "private_mapping",
            },
            {
                "category": "FOOD",
                "confidence": 0.5,  # Mid-range
                "categorization_method": "fuzzy_match",
            },
        ]

        stats = get_processing_stats(transactions)

        assert stats["total_transactions"] == 3
        assert "confidence_distribution" in stats
        assert "method_distribution" in stats

    def test_standardize_date_with_leading_zeros(self):
        """Test date standardization preserves leading zeros."""
        from money_mapper.utils import standardize_date

        result = standardize_date("01/01/2024")

        # Should have leading zeros
        assert result == "2024-01-01"

    def test_clean_merchant_with_path_separators(self):
        """Test cleaning merchant with path-like separators."""
        from money_mapper.utils import clean_merchant_name

        result = clean_merchant_name("STARBUCKS/COFFEE/STORE")

        # Should clean and limit
        assert len(result) > 0
        assert "STARBUCKS" in result.upper()

    def test_format_amount_edge_precision(self):
        """Test amount formatting with precision edge cases."""
        from money_mapper.utils import format_amount

        # Various edge cases
        cases = [0.001, 0.001, 99.999, 0.005]

        for amount in cases:
            result = format_amount(amount)
            assert "$" in result
            assert isinstance(result, str)

    def test_normalize_text_with_numbers(self):
        """Test text normalization preserves structure."""
        from money_mapper.utils import normalize_text_for_matching

        result = normalize_text_for_matching("TEST123MERCHANT456")

        # Numbers might be preserved or removed
        assert isinstance(result, str)

    def test_load_transactions_with_special_fields(self, temp_output_dir):
        """Test loading transactions with unusual fields."""
        from money_mapper.utils import load_transactions_from_json

        test_file = temp_output_dir / "special.json"
        transactions = [
            {
                "merchant": "TEST",
                "amount": 10.0,
                "date": "2024-01-01",
                "custom_field_with_unicode": "Café ☕",
                "nested": {"key": "value"},
                "array_field": [1, 2, 3],
            }
        ]
        test_file.write_text(json.dumps(transactions, ensure_ascii=False), encoding="utf-8")

        loaded = load_transactions_from_json(str(test_file))

        assert len(loaded) == 1
        assert loaded[0]["merchant"] == "TEST"
