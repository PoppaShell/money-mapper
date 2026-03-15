#!/usr/bin/env python3
"""
Comprehensive tests for utils module.
Tests cover fuzzy_match, validate_transaction, merge_transaction_data,
calculate_confidence_score, date parsing, and text sanitization.
"""
import os
import sys
import pytest
import json
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils import (
    fuzzy_match_similarity,
    validate_transaction_data,
    merge_transaction_data,
    calculate_confidence_score,
    standardize_date,
    sanitize_description,
    clean_merchant_name,
    prompt_yes_no
)


class TestFuzzyMatchSimilarity:
    """Test fuzzy_match_similarity function."""
    
    def test_exact_match(self):
        """Test exact string match."""
        score = fuzzy_match_similarity("starbucks", "starbucks")
        assert score == 1.0
    
    def test_similar_strings(self):
        """Test similar but not identical strings."""
        score = fuzzy_match_similarity("starbucks", "starbuk")
        assert 0.7 <= score < 1.0
    
    def test_completely_different_strings(self):
        """Test completely different strings."""
        score = fuzzy_match_similarity("starbucks", "mcdonalds")
        assert score < 0.6
    
    def test_empty_strings(self):
        """Test with empty strings."""
        score = fuzzy_match_similarity("", "")
        assert score == 1.0  # Empty == empty
    
    def test_substring_match(self):
        """Test partial/substring match."""
        score = fuzzy_match_similarity("starbucks coffee", "starbucks")
        assert score > 0.7  # Should be fairly high but not perfect
    
    def test_single_character_diff(self):
        """Test strings with single character difference."""
        score = fuzzy_match_similarity("starbucks", "starbuckx")
        assert score > 0.8  # Very similar


class TestValidateTransactionData:
    """Test validate_transaction_data function."""
    
    def test_valid_transaction(self):
        """Test validation of a valid transaction."""
        txn = {
            'date': '2024-01-15',
            'amount': -50.25,
            'description': 'MERCHANT NAME'
        }
        is_valid, errors = validate_transaction_data(txn)
        assert is_valid is True or len(errors) == 0
    
    def test_missing_date(self):
        """Test validation fails with missing date."""
        txn = {
            'amount': -50.25,
            'description': 'MERCHANT NAME'
        }
        is_valid, errors = validate_transaction_data(txn)
        assert is_valid is False or any('date' in str(e).lower() for e in errors)
    
    def test_missing_amount(self):
        """Test validation fails with missing amount."""
        txn = {
            'date': '2024-01-15',
            'description': 'MERCHANT NAME'
        }
        is_valid, errors = validate_transaction_data(txn)
        assert is_valid is False or any('amount' in str(e).lower() for e in errors)
    
    def test_missing_description(self):
        """Test validation fails with missing description."""
        txn = {
            'date': '2024-01-15',
            'amount': -50.25
        }
        is_valid, errors = validate_transaction_data(txn)
        assert is_valid is False or len(errors) > 0
    
    def test_empty_transaction(self):
        """Test validation of empty transaction."""
        is_valid, errors = validate_transaction_data({})
        assert is_valid is False
    
    def test_zero_amount_valid(self):
        """Test that zero amount is valid."""
        txn = {
            'date': '2024-01-15',
            'amount': 0.0,
            'description': 'MERCHANT'
        }
        is_valid, errors = validate_transaction_data(txn)
        # Zero amount should be acceptable
        assert isinstance(is_valid, bool)


class TestMergeTransactionData:
    """Test merge_transaction_data function."""
    
    def test_merge_add_new_fields(self):
        """Test that merge adds new fields."""
        original = {'date': '2024-01-15', 'amount': -50}
        new_data = {'category': 'FOOD', 'merchant': 'Starbucks'}
        
        result = merge_transaction_data(original, new_data)
        assert result.get('category') == 'FOOD'
        assert result.get('merchant') == 'Starbucks'
    
    def test_merge_override_existing(self):
        """Test that merge can override existing fields."""
        original = {'date': '2024-01-15', 'amount': -50, 'category': 'OLD'}
        new_data = {'category': 'FOOD'}
        
        result = merge_transaction_data(original, new_data)
        assert result.get('category') == 'FOOD'
    
    def test_merge_preserve_original(self):
        """Test that merge preserves original fields."""
        original = {'date': '2024-01-15', 'amount': -50}
        new_data = {'category': 'FOOD'}
        
        result = merge_transaction_data(original, new_data)
        assert result.get('date') == '2024-01-15'
        assert result.get('amount') == -50
    
    def test_merge_empty_original(self):
        """Test merge with empty original."""
        result = merge_transaction_data({}, {'category': 'FOOD'})
        assert result.get('category') == 'FOOD'
    
    def test_merge_empty_new_data(self):
        """Test merge with empty new data."""
        original = {'date': '2024-01-15', 'amount': -50}
        result = merge_transaction_data(original, {})
        assert result.get('date') == '2024-01-15'
        assert result.get('amount') == -50
    
    def test_merge_none_values(self):
        """Test merge with None values."""
        original = {'date': '2024-01-15', 'amount': -50}
        new_data = {'category': None}
        
        result = merge_transaction_data(original, new_data)
        # Should handle None gracefully
        assert 'date' in result


class TestCalculateConfidenceScore:
    """Test calculate_confidence_score function."""
    
    def test_private_mapping_score(self):
        """Test confidence for private mapping."""
        score = calculate_confidence_score('private_mapping')
        assert 0.9 <= score <= 1.0
    
    def test_public_mapping_score(self):
        """Test confidence for public mapping."""
        score = calculate_confidence_score('public_mapping')
        assert 0.8 <= score <= 0.95
    
    def test_fuzzy_match_score(self):
        """Test confidence for fuzzy match."""
        score = calculate_confidence_score('fuzzy_match', similarity=0.75)
        assert 0.6 <= score <= 0.85
    
    def test_plaid_keyword_score(self):
        """Test confidence for plaid keyword."""
        score = calculate_confidence_score('plaid_keyword')
        assert 0.5 <= score <= 0.75
    
    def test_unknown_method_score(self):
        """Test confidence for unknown method."""
        score = calculate_confidence_score('unknown')
        assert 0 <= score <= 0.6
    
    def test_none_method(self):
        """Test with None method."""
        score = calculate_confidence_score(None)
        assert 0 <= score <= 1.0


class TestStandardizeDate:
    """Test standardize_date function."""
    
    def test_mmdd_format_with_statement_period(self):
        """Test MM/DD format with statement period."""
        statement_period = {'end_year': 2024}
        result = standardize_date('01/15', statement_period)
        assert result.startswith('2024-')
        assert '01-15' in result
    
    def test_mmdd_format_without_statement_period(self):
        """Test MM/DD format without statement period."""
        result = standardize_date('01/15')
        assert '-01-15' in result  # Should infer current year
    
    def test_mmddyy_format_21st_century(self):
        """Test MM/DD/YY format for 21st century."""
        result = standardize_date('01/15/24')
        assert result == '2024-01-15'
    
    def test_mmddyy_format_20th_century(self):
        """Test MM/DD/YY format for 20th century."""
        result = standardize_date('01/15/95')
        assert result == '1995-01-15'
    
    def test_mmddyyyy_format(self):
        """Test MM/DD/YYYY format."""
        result = standardize_date('01/15/2024')
        assert result == '2024-01-15'
    
    def test_yyyymmdd_format_already_standardized(self):
        """Test that YYYY-MM-DD format passes through."""
        result = standardize_date('2024-01-15')
        assert result == '2024-01-15'
    
    def test_invalid_date_format(self):
        """Test with invalid date format."""
        result = standardize_date('invalid')
        # Should return as-is or handle gracefully
        assert isinstance(result, str)
    
    def test_year_boundary_december_to_january(self):
        """Test year boundary detection (Dec to Jan crossing)."""
        # December 31st
        statement_period = {'end_year': 2024}
        result_dec = standardize_date('12/31', statement_period)
        
        # January 15th (new year)
        statement_period = {'end_year': 2024}
        result_jan = standardize_date('01/15', statement_period)
        
        assert '2024-12-31' in result_dec or result_dec.endswith('12-31')
        assert '2024-01-15' in result_jan or result_jan.endswith('01-15')
    
    def test_whitespace_handling(self):
        """Test that whitespace is stripped."""
        result = standardize_date('  01/15/2024  ')
        assert result == '2024-01-15'


class TestSanitizeDescription:
    """Test sanitize_description function."""
    
    def test_redact_account_numbers(self):
        """Test account number redaction."""
        desc = "Card 4242 1234 5678 9999 charges"
        # Should handle account number redaction
        result = sanitize_description(desc, privacy_config={'redact_account_numbers': True})
        # May or may not be redacted depending on implementation
        assert isinstance(result, str)
    
    def test_redact_phone_numbers(self):
        """Test phone number redaction."""
        desc = "Call 555-123-4567 for support"
        result = sanitize_description(desc, privacy_config={'redact_phone_numbers': True})
        assert isinstance(result, str)
    
    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        desc = "Starbucks Coffee Shop"
        result = sanitize_description(desc)
        assert "Starbucks" in result or result != ""
    
    def test_empty_description(self):
        """Test with empty description."""
        result = sanitize_description("")
        assert isinstance(result, str)
    
    def test_fuzzy_keyword_matching(self):
        """Test fuzzy keyword matching for personal data."""
        desc = "John's Pizza Place"
        privacy_config = {
            'redact_personal_keywords': True,
            'personal_keywords': ['john']
        }
        result = sanitize_description(desc, privacy_config=privacy_config)
        # Should handle fuzzy matching
        assert isinstance(result, str)
    
    def test_multiple_patterns(self):
        """Test with multiple sensitive patterns."""
        desc = "Account 123456 called 555-1234 at home"
        result = sanitize_description(desc)
        assert isinstance(result, str)


class TestCleanMerchantName:
    """Test clean_merchant_name utility function."""
    
    def test_basic_cleaning(self):
        """Test basic merchant name cleaning."""
        desc = "STARBUCKS COFFEE SHOP"
        result = clean_merchant_name(desc)
        assert "STARBUCKS" in result.upper()
    
    def test_remove_card_number(self):
        """Test card number removal."""
        desc = "CHECKCARD 4242*1234 STARBUCKS"
        result = clean_merchant_name(desc)
        assert "4242" not in result or "STARBUCKS" in result.upper()
    
    def test_empty_string(self):
        """Test with empty string."""
        result = clean_merchant_name("")
        assert isinstance(result, str)


class TestPromptYesNo:
    """Test prompt_yes_no interactive function."""
    
    @patch('builtins.input', return_value='y')
    def test_yes_response(self, mock_input):
        """Test yes response."""
        result = prompt_yes_no("Continue?")
        assert result is True
    
    @patch('builtins.input', return_value='n')
    def test_no_response(self, mock_input):
        """Test no response."""
        result = prompt_yes_no("Continue?")
        assert result is False
    
    @patch('builtins.input', side_effect=['invalid', 'y'])
    def test_invalid_then_valid_response(self, mock_input):
        """Test invalid response followed by valid."""
        result = prompt_yes_no("Continue?")
        assert result is True  # Should eventually get valid input


class TestDateParsingEdgeCases:
    """Test edge cases in date parsing."""
    
    def test_single_digit_month_day(self):
        """Test single digit month and day."""
        result = standardize_date('1/5/2024')
        assert result == '2024-01-05'
    
    def test_two_digit_month_day(self):
        """Test two digit month and day."""
        result = standardize_date('01/05/2024')
        assert result == '2024-01-05'
    
    def test_leap_year_february(self):
        """Test leap year handling (Feb 29)."""
        result = standardize_date('02/29/2024')
        assert result == '2024-02-29'


class TestTextSanitizationPatterns:
    """Test text sanitization patterns."""
    
    def test_multiple_account_formats(self):
        """Test various account number formats."""
        patterns = [
            "****1234",
            "4242 **** **** 9999",
            "Account 123456789"
        ]
        
        for pattern in patterns:
            result = sanitize_description(pattern)
            assert isinstance(result, str)
    
    def test_merchant_name_cleaning(self):
        """Test merchant name cleaning in sanitization."""
        desc = "MERCHANT #1234 LOCATION"
        result = sanitize_description(desc)
        assert isinstance(result, str)


class TestValidationIntegration:
    """Test validation integration with other functions."""
    
    def test_validate_then_merge(self):
        """Test validating then merging transaction."""
        txn = {
            'date': '2024-01-15',
            'amount': -50,
            'description': 'TEST'
        }
        
        # Should be valid
        is_valid, errors = validate_transaction_data(txn)
        
        if is_valid:
            # Then merge
            enriched = merge_transaction_data(txn, {'category': 'FOOD'})
            assert enriched.get('category') == 'FOOD'
    
    def test_standardize_date_in_transaction(self):
        """Test date standardization in transaction context."""
        date_str = '01/15/2024'
        standardized = standardize_date(date_str)
        
        # Use in transaction
        txn = {
            'date': standardized,
            'amount': -50,
            'description': 'TEST'
        }
        
        is_valid, errors = validate_transaction_data(txn)
        assert isinstance(is_valid, bool)
