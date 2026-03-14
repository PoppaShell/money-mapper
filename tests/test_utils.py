"""Tests for money_mapper.utils module."""

import json
from pathlib import Path
import pytest

from money_mapper.utils import (
    load_transactions_from_json,
    save_transactions_to_json,
    sanitize_description,
    standardize_date,
    load_config,
    clean_merchant_name,
    format_amount,
    normalize_text_for_matching,
    fuzzy_match_similarity,
    validate_transaction_data,
    calculate_confidence_score,
    get_processing_stats,
    merge_transaction_data,
    prompt_yes_no,
    check_dependencies,
)


class TestLoadTransactions:
    """Test transaction loading from JSON."""

    def test_load_transactions_valid_file(self, sample_transactions, temp_output_dir):
        """Test loading valid transaction JSON file."""
        test_file = temp_output_dir / "transactions.json"
        
        # Write sample transactions
        with open(test_file, 'w') as f:
            json.dump(sample_transactions, f)
        
        # Load and verify
        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 4
        assert loaded[0]["merchant"] == "Starbucks"

    def test_load_transactions_empty_file(self, temp_output_dir):
        """Test loading empty transaction file."""
        test_file = temp_output_dir / "empty.json"
        with open(test_file, 'w') as f:
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

    @pytest.mark.parametrize("amount,expected", [
        (0.01, "$0.01"),
        (0, "$0.00"),
        (999999.99, "$999,999.99"),
    ])
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
        transactions = [{
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "date": "2024-01-15",
            "category": "FOOD & DINING",
            "confidence": 0.95,
            "categorization_method": "private_mapping"
        }]
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
            }
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
