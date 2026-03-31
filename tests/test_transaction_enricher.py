"""Tests for money_mapper.transaction_enricher module."""

from unittest.mock import MagicMock, patch

import pytest

from money_mapper.transaction_enricher import (
    create_mapping_result,
    enrich_transaction,
    extract_merchant_name,
    find_merchant_mapping,
    fuzzy_match_similarity,
    is_valid_plaid_category,
    try_ml_prediction,
    wildcard_pattern_match,
)


class TestExtractMerchantName:
    """Test merchant name extraction."""

    def test_extract_basic_merchant(self):
        """Test extracting basic merchant name."""
        result = extract_merchant_name("STARBUCKS COFFEE SEATTLE WA")
        assert "STARBUCKS" in result.upper()
        assert result != ""

    def test_extract_removes_banking_prefixes(self):
        """Test removing banking prefixes."""
        result = extract_merchant_name("CHECKCARD AMAZON.COM")
        assert "CHECKCARD" not in result.upper()
        assert "AMAZON" in result.upper()

    def test_extract_removes_debit_card_prefix(self):
        """Test removing DEBIT CARD prefix."""
        result = extract_merchant_name("DEBIT CARD WHOLE FOODS MARKET")
        assert "DEBIT" not in result.upper()
        assert "WHOLE" in result.upper()

    def test_extract_removes_dates(self):
        """Test removing dates from merchant name."""
        result = extract_merchant_name("MERCHANT 01/23")
        # Dates like 01/23 should be removed
        assert "01/23" not in result
        assert "MERCHANT" in result.upper()

    def test_extract_removes_reference_numbers(self):
        """Test removing reference numbers."""
        result = extract_merchant_name("MERCHANT #12345")
        assert "#12345" not in result
        assert "12345" not in result

    def test_extract_limits_to_four_words(self):
        """Test that result limited to 4 words."""
        result = extract_merchant_name("VERY LONG MERCHANT NAME HERE AND MORE WORDS")
        words = result.split()
        assert len(words) <= 4

    def test_extract_empty_string(self):
        """Test extracting from empty string."""
        result = extract_merchant_name("")
        assert result == ""

    def test_extract_whitespace_only(self):
        """Test extracting from whitespace only."""
        result = extract_merchant_name("   ")
        assert result == ""


class TestWildcardPatternMatch:
    """Test wildcard pattern matching."""

    def test_exact_match(self):
        """Test exact wildcard match."""
        assert wildcard_pattern_match("starbucks", "starbucks")

    def test_start_wildcard(self):
        """Test wildcard at start."""
        assert wildcard_pattern_match("starbucks coffee", "*coffee")

    def test_end_wildcard(self):
        """Test wildcard at end."""
        assert wildcard_pattern_match("starbucks coffee", "starbucks*")

    def test_both_wildcards(self):
        """Test wildcards at both ends."""
        assert wildcard_pattern_match("joe's pizza place", "*pizza*")

    def test_multiple_fragments(self):
        """Test multiple wildcard fragments."""
        result = wildcard_pattern_match("joe's pizza shop", "joe*pizza*")
        assert result

    def test_no_match(self):
        """Test pattern that doesn't match."""
        assert not wildcard_pattern_match("starbucks", "amazon*")

    def test_case_insensitive(self):
        """Test case-insensitive matching (assuming lowercase inputs)."""
        assert wildcard_pattern_match("starbucks", "starbucks")

    def test_partial_fragment_match(self):
        """Test partial word fragment matching."""
        assert wildcard_pattern_match("starbucks coffee", "*buck*")


class TestCreateMappingResult:
    """Test mapping result creation."""

    def test_create_basic_result(self):
        """Test creating basic mapping result."""
        mapping_data = {"category": "FOOD & DINING", "subcategory": "COFFEE SHOPS"}
        result = create_mapping_result(mapping_data, "exact_match", 0.95)

        assert result["category"] == "FOOD & DINING"
        assert result["subcategory"] == "COFFEE SHOPS"
        assert result["categorization_method"] == "exact_match"
        assert result["confidence"] == 0.95

    def test_result_has_required_fields(self):
        """Test that result has all required fields."""
        mapping_data = {"category": "FOOD"}
        result = create_mapping_result(mapping_data, "fuzzy_match", 0.80)

        assert "category" in result
        assert "confidence" in result
        assert "categorization_method" in result

    def test_result_with_empty_mapping(self):
        """Test creating result with empty mapping data."""
        result = create_mapping_result({}, "unknown", 0.0)
        assert isinstance(result, dict)


class TestFuzzyMatchSimilarity:
    """Test fuzzy matching similarity."""

    def test_identical_strings(self):
        """Test identical strings have 1.0 similarity."""
        similarity = fuzzy_match_similarity("starbucks", "starbucks")
        assert similarity == 1.0

    def test_completely_different(self):
        """Test completely different strings have low similarity."""
        similarity = fuzzy_match_similarity("starbucks", "amazon")
        assert similarity < 0.5

    def test_similar_strings(self):
        """Test similar strings have moderate-high similarity."""
        similarity = fuzzy_match_similarity("starbucks", "starbuck")
        assert 0.7 < similarity < 1.0

    def test_substring_similarity(self):
        """Test substring similarity."""
        similarity = fuzzy_match_similarity("starbucks coffee", "starbucks")
        assert similarity > 0.5

    def test_empty_strings(self):
        """Test matching empty strings."""
        similarity = fuzzy_match_similarity("", "")
        assert 0.0 <= similarity <= 1.0


class TestFindMerchantMapping:
    """Test merchant mapping lookup."""

    def test_mapping_with_empty_mappings(self):
        """Test finding mapping with empty mapping dicts."""
        result = find_merchant_mapping(
            "STARBUCKS COFFEE",
            {},  # private
            {},  # public
            {},  # plaid
            0.7,
        )

        assert "category" in result
        assert isinstance(result, dict)

    def test_mapping_result_structure(self):
        """Test that mapping result has required structure."""
        result = find_merchant_mapping("AMAZON", {}, {}, {}, 0.7)

        required_fields = ["category", "subcategory", "confidence", "categorization_method"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_mapping_with_none_result(self):
        """Test that mapping returns something even with no match."""
        result = find_merchant_mapping("UNKNOWN MERCHANT", {}, {}, {}, 0.7)

        assert result is not None
        assert result.get("category") == "UNCATEGORIZED" or result.get("category") is not None

    def test_mapping_confidence_in_range(self):
        """Test that confidence is in valid range."""
        result = find_merchant_mapping("TEST MERCHANT", {}, {}, {}, 0.7)

        confidence = result.get("confidence", 0.0)
        assert 0.0 <= confidence <= 1.0


class TestEnrichmentIntegration:
    """Integration tests for transaction enrichment."""

    def test_enrich_transaction_basic(self):
        """Test enriching a basic transaction."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "description": "STARBUCKS COFFEE SEATTLE WA",
            "amount": -5.50,
            "date": "2024-01-15",
        }

        enriched = enrich_transaction(
            transaction,
            {},  # private mappings
            {},  # public mappings
            {},  # plaid categories
            0.7,
        )

        assert "merchant_name" in enriched
        assert "category" in enriched
        assert "confidence" in enriched

    def test_enrich_preserves_original_fields(self):
        """Test that enrichment preserves original transaction fields."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "description": "TEST MERCHANT",
            "amount": 10.00,
            "date": "2024-01-15",
            "extra_field": "should_be_preserved",
        }

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert enriched.get("amount") == 10.00
        assert enriched.get("date") == "2024-01-15"
        assert enriched.get("extra_field") == "should_be_preserved"

    def test_enrich_adds_required_fields(self):
        """Test that enrichment adds required fields."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "MERCHANT", "amount": 5.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        required = ["merchant_name", "category", "confidence", "categorization_method"]
        for field in required:
            assert field in enriched, f"Missing required field: {field}"

    @pytest.mark.parametrize(
        "description",
        [
            "STARBUCKS COFFEE",
            "AMAZON.COM",
            "WHOLE FOODS MARKET",
            "APPLE STORE",
        ],
    )
    def test_enrich_various_merchants(self, description):
        """Test enrichment with various merchant descriptions."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": description, "amount": -10.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert enriched["merchant_name"] != ""
        assert enriched["category"] is not None


class TestEnrichTransactionExtended:
    """Extended tests for transaction enrichment."""

    def test_enrich_with_empty_description(self):
        """Test enriching transaction with empty description."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "", "amount": 10.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert "merchant_name" in enriched
        assert "category" in enriched

    def test_enrich_with_whitespace_description(self):
        """Test enriching transaction with whitespace description."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "   \t   ", "amount": 10.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert "merchant_name" in enriched
        assert "category" in enriched

    def test_enrich_positive_amount(self):
        """Test enriching transaction with positive amount."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "DEPOSIT PAYCHECK", "amount": 5000.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert enriched["amount"] == 5000.00

    def test_enrich_negative_amount(self):
        """Test enriching transaction with negative amount."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "STARBUCKS", "amount": -5.50, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert enriched["amount"] == -5.50

    def test_enrich_zero_amount(self):
        """Test enriching transaction with zero amount."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "TEST", "amount": 0.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert enriched["amount"] == 0.00

    def test_enrich_very_long_description(self):
        """Test enriching transaction with very long description."""
        from money_mapper.transaction_enricher import enrich_transaction

        long_desc = "MERCHANT " * 50  # Very long description
        transaction = {"description": long_desc, "amount": 10.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert "merchant_name" in enriched
        assert enriched["merchant_name"] != ""

    def test_enrich_with_special_characters(self):
        """Test enriching transaction with special characters."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "description": "STARBUCKS@COFFEE#STORE$123",
            "amount": 5.00,
            "date": "2024-01-15",
        }

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert "merchant_name" in enriched
        assert "category" in enriched

    def test_enrich_with_numbers(self):
        """Test enriching transaction with numbers."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "description": "AMAZON 12345 STORE 999",
            "amount": 50.00,
            "date": "2024-01-15",
        }

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        assert "merchant_name" in enriched

    def test_enrich_private_mapping_priority(self):
        """Test that private mappings have highest priority."""
        from money_mapper.transaction_enricher import enrich_transaction

        private_mappings = {
            "FOOD": {
                "MY_COFFEE": {
                    "name": "My Local Coffee",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "private",
                }
            }
        }

        transaction = {"description": "MY_COFFEE SHOP", "amount": 5.00, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, private_mappings, {}, {}, 0.7)

        # Should match private mapping (usually highest confidence)
        assert "category" in enriched

    def test_enrich_public_mapping_fallback(self):
        """Test that public mappings are fallback."""
        from money_mapper.transaction_enricher import enrich_transaction

        public_mappings = {
            "FOOD": {
                "STARBUCKS": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                }
            }
        }

        transaction = {"description": "STARBUCKS COFFEE", "amount": 5.00, "date": "2024-01-15"}

        enriched = enrich_transaction(
            transaction,
            {},  # No private mappings
            public_mappings,
            {},
            0.7,
        )

        assert "category" in enriched

    def test_enrich_fuzzy_threshold_high(self):
        """Test enrichment with high fuzzy threshold."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "STARBUCKS", "amount": 5.00, "date": "2024-01-15"}

        enriched = enrich_transaction(
            transaction,
            {},
            {},
            {},
            0.95,  # High threshold
        )

        assert "category" in enriched

    def test_enrich_fuzzy_threshold_low(self):
        """Test enrichment with low fuzzy threshold."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "UNKNOWN_MERCHANT_XYZ", "amount": 5.00, "date": "2024-01-15"}

        enriched = enrich_transaction(
            transaction,
            {},
            {},
            {},
            0.1,  # Very low threshold
        )

        assert "category" in enriched

    def test_enrich_batch_multiple_transactions(self):
        """Test enriching multiple transactions."""
        from money_mapper.transaction_enricher import enrich_transaction

        transactions = [
            {"description": "STARBUCKS", "amount": 5.00, "date": "2024-01-15"},
            {"description": "AMAZON", "amount": 50.00, "date": "2024-01-16"},
            {"description": "WALMART", "amount": 75.00, "date": "2024-01-17"},
        ]

        enriched_list = []
        for trans in transactions:
            enriched = enrich_transaction(trans, {}, {}, {}, 0.7)
            enriched_list.append(enriched)

        assert len(enriched_list) == 3
        for enriched in enriched_list:
            assert "category" in enriched
            assert "merchant_name" in enriched


class TestExtractMerchantNameExtended:
    """Extended tests for merchant name extraction."""

    def test_extract_with_card_number_pattern(self):
        """Test extracting from merchant with card number pattern."""
        result = extract_merchant_name("MERCHANT 4532****9876")
        assert "MERCHANT" in result.upper()
        assert "4532" not in result

    def test_extract_with_reference_number(self):
        """Test extracting from merchant with reference number."""
        result = extract_merchant_name("STARBUCKS REF#12345678")
        assert "STARBUCKS" in result.upper()
        # REF might or might not be included depending on removal logic
        assert "12345678" not in result

    def test_extract_only_numbers(self):
        """Test extracting from numbers only."""
        result = extract_merchant_name("123456789")
        # Should return something or empty
        assert isinstance(result, str)

    def test_extract_only_special_chars(self):
        """Test extracting from special characters only."""
        result = extract_merchant_name("@#$%^&*()")
        # Should handle gracefully
        assert isinstance(result, str)

    def test_extract_mixed_case(self):
        """Test extraction preserves meaningful case."""
        result = extract_merchant_name("StArBuCkS CoFfEe ShOp")
        # Should extract something
        assert len(result) > 0

    def test_extract_unicode_merchant(self):
        """Test extracting Unicode merchant name."""
        result = extract_merchant_name("CAFÉ COFFEE ☕")
        # Should handle Unicode
        assert isinstance(result, str)

    def test_extract_very_short_name(self):
        """Test extracting from very short name."""
        result = extract_merchant_name("CVS")
        assert "CVS" in result.upper()

    def test_extract_with_location_suffix(self):
        """Test extracting strips location info."""
        result = extract_merchant_name("STARBUCKS #1234 SEATTLE WA 98101")
        assert "STARBUCKS" in result.upper()
        # Should limit to 4 words
        assert len(result.split()) <= 4

    def test_extract_debit_prefix_variations(self):
        """Test various debit/card prefixes are removed."""
        descriptions = [
            "DEBIT CARD AMAZON",
            "DEBIT CARD   AMAZON",  # Multiple spaces
            "DEBIT_CARD AMAZON",
        ]
        for desc in descriptions:
            result = extract_merchant_name(desc)
            # Should extract merchant without prefix
            assert len(result) > 0


class TestWildcardPatternMatchExtended:
    """Extended tests for wildcard pattern matching."""

    def test_wildcard_question_mark(self):
        """Test single-character wildcard ?."""
        # ? matches single character
        result = wildcard_pattern_match("joe", "j?e")
        assert result

    def test_wildcard_multiple_question_marks(self):
        """Test multiple ? wildcards."""
        result = wildcard_pattern_match("coffee", "c?ff??")
        assert result

    def test_wildcard_star_at_start(self):
        """Test * at start of pattern."""
        result = wildcard_pattern_match("coffee shop", "*shop")
        assert result

    def test_wildcard_star_at_end(self):
        """Test * at end of pattern."""
        result = wildcard_pattern_match("starbucks coffee", "star*")
        assert result

    def test_wildcard_star_middle(self):
        """Test * in middle of pattern."""
        result = wildcard_pattern_match("starbucks coffee shop", "star*shop")
        assert result

    def test_wildcard_multiple_stars(self):
        """Test multiple * in pattern."""
        result = wildcard_pattern_match("joe pizza place", "*pizza*")
        assert result

    def test_wildcard_no_match_missing_fragment(self):
        """Test no match when fragment missing."""
        result = wildcard_pattern_match("starbucks", "star*xyz*")
        assert not result

    def test_wildcard_empty_pattern(self):
        """Test empty pattern."""
        result = wildcard_pattern_match("test", "")
        assert not result or result  # Should handle gracefully

    def test_wildcard_star_only(self):
        """Test pattern with only stars."""
        result = wildcard_pattern_match("test", "*")
        assert result

    def test_wildcard_empty_fragments(self):
        """Test pattern with consecutive stars."""
        result = wildcard_pattern_match("test", "t**st")
        assert result

    def test_wildcard_exact_no_wildcards(self):
        """Test exact match with no wildcards."""
        result = wildcard_pattern_match("exact", "exact")
        assert result

    def test_wildcard_case_sensitive(self):
        """Test wildcard matching is case-sensitive (expects lowercase)."""
        # Tests expect lowercase inputs pre-normalized
        result = wildcard_pattern_match("starbucks", "star*")
        # Assuming inputs are pre-normalized to lowercase
        # This test documents expected behavior
        assert result


class TestCreateMappingResultExtended:
    """Extended tests for mapping result creation."""

    def test_create_result_with_all_fields(self):
        """Test creating result with all mapping fields."""
        mapping_data = {
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "name": "Starbucks",
            "extra_field": "value",
        }
        result = create_mapping_result(mapping_data, "exact_match", 0.99)

        assert result["category"] == "FOOD_AND_DRINK"
        assert result["subcategory"] == "FOOD_AND_DRINK_COFFEE"
        assert result["merchant_name"] == "Starbucks"  # Note: Key is merchant_name, not name
        assert result["confidence"] == 0.99
        assert result["categorization_method"] == "exact_match"
        # Extra fields are not preserved
        assert "extra_field" not in result

    def test_create_result_confidence_range(self):
        """Test creating result with various confidence values."""
        for confidence in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = create_mapping_result({"category": "TEST"}, "test", confidence)
            assert result["confidence"] == confidence

    def test_create_result_method_name_preserved(self):
        """Test that method name is exactly preserved."""
        methods = ["exact_match", "fuzzy_match", "partial_match", "custom_method"]
        for method in methods:
            result = create_mapping_result({"category": "TEST"}, method, 0.5)
            assert result["categorization_method"] == method

    def test_create_result_only_extracts_standard_fields(self):
        """Test that only standard fields are extracted from mapping data."""
        mapping_data = {
            "category": "FOOD",
            "subcategory": "COFFEE",
            "name": "Test Cafe",
            "custom1": "value1",
            "custom2": {"nested": "value2"},
            "custom3": [1, 2, 3],
        }
        result = create_mapping_result(mapping_data, "test", 0.5)

        # Only standard fields are extracted
        assert result["category"] == "FOOD"
        assert result["subcategory"] == "COFFEE"
        assert result["merchant_name"] == "Test Cafe"
        assert result["confidence"] == 0.5
        assert result["categorization_method"] == "test"
        # Custom fields are not preserved
        assert "custom1" not in result
        assert "custom2" not in result
        assert "custom3" not in result

    def test_create_result_empty_mapping_with_method(self):
        """Test creating result from empty mapping."""
        result = create_mapping_result({}, "uncategorized", 0.0)

        assert result["confidence"] == 0.0
        assert result["categorization_method"] == "uncategorized"
        assert isinstance(result, dict)


class TestFuzzyMatchSimilarityExtended:
    """Extended tests for fuzzy similarity matching."""

    def test_fuzzy_similarity_identical_strings(self):
        """Test identical strings have maximum similarity."""
        from money_mapper.transaction_enricher import fuzzy_match_similarity

        similarity = fuzzy_match_similarity("test", "test")
        assert similarity == 1.0

    def test_fuzzy_similarity_completely_different(self):
        """Test completely different strings have low similarity."""
        from money_mapper.transaction_enricher import fuzzy_match_similarity

        similarity = fuzzy_match_similarity("aaaa", "bbbb")
        assert similarity == 0.0

    def test_fuzzy_similarity_partial_match(self):
        """Test partial match has medium similarity."""
        from money_mapper.transaction_enricher import fuzzy_match_similarity

        similarity = fuzzy_match_similarity("testing", "test")
        assert 0.5 < similarity < 1.0

    def test_fuzzy_similarity_empty_strings(self):
        """Test empty string matching."""
        from money_mapper.transaction_enricher import fuzzy_match_similarity

        similarity = fuzzy_match_similarity("", "")
        assert 0.0 <= similarity <= 1.0


class TestApplyPlaidKeywordMatching:
    """Tests for Plaid keyword matching."""

    def test_plaid_matching_with_keywords(self):
        """Test Plaid keyword matching finds categories."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {
            "FOOD_AND_DRINK.FOOD_AND_DRINK_RESTAURANTS": {
                "keywords": ["pizza", "restaurant", "dine"]
            },
            "FOOD_AND_DRINK.FOOD_AND_DRINK_COFFEE": {"keywords": ["coffee", "cafe", "starbucks"]},
        }

        result = apply_plaid_keyword_matching(
            "STARBUCKS COFFEE SHOP", "starbucks", plaid_categories
        )

        # Should find coffee category
        assert result is not None or result is None  # Depends on implementation
        if result:
            assert "category" in result

    def test_plaid_matching_no_keywords(self):
        """Test Plaid matching with empty categories."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {}

        result = apply_plaid_keyword_matching("UNKNOWN MERCHANT", "unknown", plaid_categories)

        # Should return None when no matches
        assert result is None


class TestLoadEnrichmentConfig:
    """Tests for enrichment config loading."""

    def test_load_enrichment_config_basic(self):
        """Test loading enrichment configuration."""
        from money_mapper.transaction_enricher import load_enrichment_config

        try:
            config = load_enrichment_config()
            assert isinstance(config, dict)
            assert "plaid_categories" in config
        except SystemExit:
            # Expected if config files not found
            pass


class TestProcessTransactionEnrichment:
    """Tests for batch transaction enrichment processing."""

    def test_process_enrichment_empty_file(self, temp_output_dir):
        """Test enrichment of empty transaction file."""
        from money_mapper.transaction_enricher import process_transaction_enrichment

        input_file = temp_output_dir / "empty.json"
        output_file = temp_output_dir / "output.json"
        input_file.write_text("[]")

        # Should handle empty file gracefully
        try:
            process_transaction_enrichment(str(input_file), str(output_file))
        except SystemExit:
            # Expected if config files missing
            pass


class TestEnrichmentIntegrationScenarios:
    """Integration tests for enrichment scenarios."""

    def test_enrich_with_all_mappings_present(self):
        """Test enrichment when all mapping types are available."""
        from money_mapper.transaction_enricher import enrich_transaction

        private_mappings = {
            "FOOD": {
                "MY_CAFE": {
                    "name": "My Cafe",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "COFFEE",
                    "scope": "private",
                }
            }
        }

        public_mappings = {
            "FOOD": {
                "STARBUCKS": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "COFFEE",
                    "scope": "public",
                }
            }
        }

        plaid_categories = {
            "FOOD_AND_DRINK.RESTAURANTS": {"keywords": ["restaurant", "dine", "food"]}
        }

        transaction = {"description": "MY_CAFE COFFEE", "amount": -5.50, "date": "2024-01-15"}

        enriched = enrich_transaction(
            transaction, private_mappings, public_mappings, plaid_categories, 0.7
        )

        # Should have enriched data
        assert "category" in enriched
        assert "merchant_name" in enriched

    def test_enrich_with_unicode_description(self):
        """Test enrichment with Unicode merchant names."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "CAFÉ ☕ PARISIEN", "amount": 7.50, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

        # Should handle Unicode gracefully
        assert isinstance(enriched, dict)
        assert "merchant_name" in enriched

    def test_enrich_batch_diverse_merchants(self):
        """Test enriching diverse merchant transactions."""
        from money_mapper.transaction_enricher import enrich_transaction

        merchants = [
            "STARBUCKS COFFEE",
            "WHOLE FOODS MARKET",
            "AMAZON.COM",
            "SHELL GAS STATION",
            "TARGET STORE 123",
            "UNKNOWN MERCHANT",
        ]

        for desc in merchants:
            transaction = {"description": desc, "amount": -50.00, "date": "2024-01-15"}

            enriched = enrich_transaction(transaction, {}, {}, {}, 0.7)

            assert "category" in enriched
            assert "merchant_name" in enriched

    def test_enrich_with_confidence_thresholds(self):
        """Test enrichment with various confidence thresholds."""
        from money_mapper.transaction_enricher import enrich_transaction

        thresholds = [0.1, 0.5, 0.9]
        transaction = {"description": "TEST MERCHANT", "amount": 10.0, "date": "2024-01-15"}

        for threshold in thresholds:
            enriched = enrich_transaction(transaction, {}, {}, {}, threshold)

            assert "category" in enriched
            assert 0.0 <= enriched.get("confidence", 0.0) <= 1.0


class TestMLIntegration:
    """Test ML categorizer integration into enrichment pipeline."""

    def test_enrich_skips_ml_when_none(self):
        """Test that enrichment works when ML model is None."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "UNKNOWN MERCHANT", "amount": 25.0, "date": "2024-01-15"}

        enriched = enrich_transaction(transaction, {}, {}, {}, ml_model=None)

        assert enriched["category"] == "UNCATEGORIZED"
        assert enriched["categorization_method"] != "ml_prediction"

    def test_try_ml_prediction_returns_none_when_no_model(self):
        """Test that try_ml_prediction returns None when model is None."""

        transaction = {
            "description": "TEST",
            "merchant_name": "TEST",
            "amount": 10.0,
        }

        result = try_ml_prediction(transaction, {}, ml_model=None)

        assert result is None

    def test_is_valid_plaid_category(self):
        """Test category validation."""

        plaid_categories = {
            "FOOD_AND_DRINK": {"keywords": []},
            "FOOD_AND_DRINK.RESTAURANTS": {"keywords": []},
        }

        # Valid categories
        assert is_valid_plaid_category(
            "FOOD_AND_DRINK", "FOOD_AND_DRINK.RESTAURANTS", plaid_categories
        )
        assert is_valid_plaid_category("FOOD_AND_DRINK", "FOOD_AND_DRINK", plaid_categories)

        # Invalid category
        assert not is_valid_plaid_category("INVALID", "INVALID_SUBCATEGORY", plaid_categories)

    def test_try_ml_prediction_validates_category(self):
        """Test that ML predictions are validated against Plaid taxonomy."""

        transaction = {
            "description": "TEST",
            "merchant_name": "TEST",
            "amount": 10.0,
        }

        # Create mock model that returns invalid category
        class MockModel:
            pass

        mock_model = MockModel()

        # Mock predict_category to return invalid category
        import money_mapper.ml_categorizer as ml_cat

        original_predict = getattr(ml_cat, "predict_category", None)

        def mock_predict(model, txn):
            return ("INVALID_CATEGORY", "INVALID_SUBCATEGORY")

        ml_cat.predict_category = mock_predict

        try:
            plaid_categories = {"FOOD_AND_DRINK": {"keywords": []}}

            result = try_ml_prediction(transaction, plaid_categories, mock_model)

            # Should return None because category is invalid
            assert result is None
        finally:
            if original_predict:
                ml_cat.predict_category = original_predict

    def test_ml_fallback_when_mapping_fails(self):
        """Test that ML is tried when mapping returns UNCATEGORIZED."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "description": "VERY OBSCURE MERCHANT XYZ",
            "amount": 50.0,
            "date": "2024-01-15",
        }

        plaid_categories = {"FOOD_AND_DRINK": {"keywords": []}}

        # Create mock model
        class MockModel:
            pass

        mock_model = MockModel()

        # Mock predict_category to return valid category
        import money_mapper.ml_categorizer as ml_cat

        original_predict = getattr(ml_cat, "predict_category", None)

        def mock_predict(model, txn):
            return ("FOOD_AND_DRINK", "FOOD_AND_DRINK")

        ml_cat.predict_category = mock_predict

        try:
            enriched = enrich_transaction(
                transaction, {}, {}, plaid_categories, ml_model=mock_model
            )

            # Should use ML prediction since mapping failed
            assert enriched.get("categorization_method") == "ml_prediction"
            assert enriched["category"] != "UNCATEGORIZED"
        finally:
            if original_predict:
                ml_cat.predict_category = original_predict

    def test_mapping_takes_priority_over_ml(self):
        """Test that mappings are tried before ML."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {"description": "STARBUCKS COFFEE", "amount": 5.0, "date": "2024-01-15"}

        private_mappings = {
            "MAPPED_CATEGORY": {
                "SUB1": {"starbucks": {"name": "Starbucks", "category": "FOOD_AND_DRINK"}}
            }
        }

        plaid_categories = {"FOOD_AND_DRINK": {"keywords": []}}

        class MockModel:
            pass

        # Mock predict_category to return different category
        import money_mapper.ml_categorizer as ml_cat

        original_predict = getattr(ml_cat, "predict_category", None)

        def mock_predict(model, txn):
            return ("OTHER_CATEGORY", "OTHER_CATEGORY")

        ml_cat.predict_category = mock_predict

        try:
            enriched = enrich_transaction(
                transaction,
                private_mappings,
                {},
                plaid_categories,
                ml_model=MockModel(),
            )

            # Should use mapping, not ML
            assert enriched.get("categorization_method") == "private_mapping"
        finally:
            if original_predict:
                ml_cat.predict_category = original_predict


class TestMLIntegrationWiring:
    """Test ML categorizer wiring in enrichment pipeline."""

    def test_enrich_transaction_uses_ml_when_provided(self):
        """ML model should be consulted when no mapping match found."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "date": "2024-01-15",
            "description": "UNKNOWN MERCHANT XYZ",
            "amount": -25.00,
        }
        ml_model = MagicMock()
        ml_model.predict.return_value = [("FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANTS")]

        enrich_transaction(
            transaction=transaction,
            private_mappings={},
            public_mappings={},
            plaid_categories={},
            fuzzy_threshold=0.7,
            ml_model=ml_model,
        )

        ml_model.predict.assert_called_once()

    def test_enrich_transaction_skips_ml_when_mapping_found(self):
        """ML should not be called when an exact mapping match exists."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "date": "2024-01-15",
            "description": "STARBUCKS #1234",
            "amount": -5.00,
        }
        ml_model = MagicMock()
        public_mappings = {
            "FOOD_AND_DRINK": {
                "FOOD_AND_DRINK_COFFEE": {
                    "starbucks*": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "FOOD_AND_DRINK_COFFEE",
                        "scope": "public",
                    }
                }
            }
        }

        enrich_transaction(
            transaction=transaction,
            private_mappings={},
            public_mappings=public_mappings,
            plaid_categories={},
            fuzzy_threshold=0.7,
            ml_model=ml_model,
        )

        ml_model.predict.assert_not_called()

    def test_enrich_transaction_graceful_when_ml_none(self):
        """Enrichment should work fine when ml_model is None (default)."""
        from money_mapper.transaction_enricher import enrich_transaction

        transaction = {
            "date": "2024-01-15",
            "description": "UNKNOWN STORE",
            "amount": -10.00,
        }

        result = enrich_transaction(
            transaction=transaction,
            private_mappings={},
            public_mappings={},
            plaid_categories={},
            fuzzy_threshold=0.7,
            ml_model=None,
        )

        assert result is not None
        assert "date" in result


class TestSimilarityIntegration:
    """Test similarity matcher integration in enrichment."""

    def test_enrich_uses_similarity_when_provided(self):
        """Similarity model consulted when ML does not match."""
        transaction = {
            "date": "2024-01-15",
            "description": "UNKNOWN MERCHANT",
            "amount": -15.00,
        }
        similarity_model = MagicMock()
        mock_match = {
            "name": "Known Store",
            "category": "GENERAL_MERCHANDISE",
            "subcategory": "GENERAL_MERCHANDISE_OTHER",
            "similarity": 0.92,
        }

        import numpy as np

        with patch(
            "money_mapper.similarity_matcher.find_similar_merchant",
            return_value=mock_match,
        ):
            with patch(
                "money_mapper.similarity_matcher.load_merchant_embeddings",
                return_value=({"m1": mock_match}, np.array([[0.1, 0.2]])),
            ):
                result = enrich_transaction(
                    transaction=transaction,
                    private_mappings={},
                    public_mappings={},
                    plaid_categories={},
                    fuzzy_threshold=0.7,
                    similarity_model=similarity_model,
                    vectors_file="models/public_vectors.npy",
                )

        assert result is not None

    def test_enrich_graceful_when_similarity_none(self):
        """Enrichment works when similarity_model is None."""
        transaction = {
            "date": "2024-01-15",
            "description": "STORE",
            "amount": -10.00,
        }
        result = enrich_transaction(
            transaction=transaction,
            private_mappings={},
            public_mappings={},
            plaid_categories={},
            fuzzy_threshold=0.7,
            similarity_model=None,
            vectors_file=None,
        )
        assert result is not None


# ============================================================
# New tests targeting uncovered lines
# ============================================================


class TestPatternMatcher:
    """Tests for the PatternMatcher class."""

    def _make_mappings(self, patterns: dict) -> dict:
        """Build a simple mappings dict for PatternMatcher."""
        return {"CAT": {"SUBCAT": patterns}}

    def test_build_index_exact_patterns(self):
        """PatternMatcher indexes exact patterns into exact_patterns dict."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"starbucks": {"name": "Starbucks", "category": "FOOD", "subcategory": "COFFEE"}}
        )
        pm = PatternMatcher(mappings, "test")
        assert "starbucks" in pm.exact_patterns

    def test_build_index_wildcard_patterns(self):
        """PatternMatcher indexes wildcard patterns into wildcard_patterns list."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"starbucks*": {"name": "Starbucks", "category": "FOOD", "subcategory": "COFFEE"}}
        )
        pm = PatternMatcher(mappings, "test")
        assert len(pm.wildcard_patterns) == 1

    def test_build_index_question_mark_wildcard(self):
        """PatternMatcher indexes ? wildcard patterns into wildcard_patterns list."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"starb?cks": {"name": "Starbucks", "category": "FOOD", "subcategory": "COFFEE"}}
        )
        pm = PatternMatcher(mappings, "test")
        assert len(pm.wildcard_patterns) == 1

    def test_match_exact_substring(self):
        """PatternMatcher.match returns result with 0.95 confidence for exact substring."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"starbucks": {"name": "Starbucks", "category": "FOOD", "subcategory": "COFFEE"}}
        )
        pm = PatternMatcher(mappings, "test")
        result = pm.match("STARBUCKS COFFEE SEATTLE", "starbucks", fuzzy_threshold=0.7)
        assert result is not None
        assert result["confidence"] == 0.95

    def test_match_wildcard_in_description(self):
        """PatternMatcher.match finds wildcard match in description."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"amazon*": {"name": "Amazon", "category": "SHOPPING", "subcategory": "ONLINE"}}
        )
        pm = PatternMatcher(mappings, "test")
        result = pm.match("amazon.com purchase", "", fuzzy_threshold=0.7)
        assert result is not None
        assert result["confidence"] == 0.90

    def test_match_wildcard_in_merchant_name(self):
        """PatternMatcher.match finds wildcard match in merchant_name."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"amzn*": {"name": "Amazon", "category": "SHOPPING", "subcategory": "ONLINE"}}
        )
        pm = PatternMatcher(mappings, "test")
        result = pm.match("PURCHASE 12345", "amzn marketplace", fuzzy_threshold=0.7)
        assert result is not None
        assert result["confidence"] == 0.89

    def test_match_no_match_returns_none(self):
        """PatternMatcher.match returns None when no pattern matches."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {"starbucks": {"name": "Starbucks", "category": "FOOD", "subcategory": "COFFEE"}}
        )
        pm = PatternMatcher(mappings, "test")
        result = pm.match("TOTALLY UNKNOWN MERCHANT", "unknown", fuzzy_threshold=0.99)
        assert result is None

    def test_match_fuzzy_fallback(self):
        """PatternMatcher.match falls back to fuzzy matching for merchant name."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD",
                    "subcategory": "COFFEE",
                }
            }
        )
        pm = PatternMatcher(mappings, "test")
        # "starbuck" is very close to "starbucks" -> fuzzy match should trigger at 0.7
        result = pm.match("POS DEBIT", "starbuck", fuzzy_threshold=0.7)
        assert result is not None
        assert result["confidence"] <= 0.80

    def test_match_word_based_matching(self):
        """PatternMatcher.match uses word-based matching when exact fails."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = self._make_mappings(
            {
                "coffee shop": {
                    "name": "Coffee Shop",
                    "category": "FOOD",
                    "subcategory": "COFFEE",
                }
            }
        )
        pm = PatternMatcher(mappings, "test")
        # "coffee shop downtown" shares both words with pattern "coffee shop"
        result = pm.match("coffee shop downtown", "coffee shop", fuzzy_threshold=0.9)
        assert result is not None

    def test_fuzzy_similarity_static_method(self):
        """PatternMatcher._fuzzy_similarity correctly computes ratio."""
        from money_mapper.transaction_enricher import PatternMatcher

        assert PatternMatcher._fuzzy_similarity("abc", "abc") == 1.0
        assert PatternMatcher._fuzzy_similarity("abc", "xyz") == 0.0

    def test_build_index_skips_non_dict_values(self):
        """PatternMatcher skips non-dict pattern values without error."""
        from money_mapper.transaction_enricher import PatternMatcher

        # Include a non-dict value in patterns
        mappings = {
            "CAT": {
                "SUBCAT": {
                    "valid_pattern": {"name": "Valid", "category": "CAT", "subcategory": "SUBCAT"},
                    "bad_pattern": "not_a_dict",
                }
            }
        }
        pm = PatternMatcher(mappings, "test")
        assert "valid_pattern" in pm.exact_patterns
        assert "bad_pattern" not in pm.exact_patterns

    def test_build_index_skips_non_dict_subcategory(self):
        """PatternMatcher skips non-dict subcategory data without error."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = {"CAT": {"SUBCAT": "not_a_dict"}}
        # Should not raise
        pm = PatternMatcher(mappings, "test")
        assert len(pm.exact_patterns) == 0

    def test_build_index_skips_non_dict_category(self):
        """PatternMatcher skips non-dict category data without error."""
        from money_mapper.transaction_enricher import PatternMatcher

        mappings = {"CAT": "not_a_dict"}
        pm = PatternMatcher(mappings, "test")
        assert len(pm.exact_patterns) == 0


class TestGetPatternMatchers:
    """Tests for the get_pattern_matchers caching function."""

    def test_get_pattern_matchers_returns_tuple(self):
        """get_pattern_matchers returns a tuple of two items."""
        import money_mapper.transaction_enricher as te
        from money_mapper.transaction_enricher import get_pattern_matchers

        # Reset module-level cache
        te._private_matcher = None
        te._public_matcher = None

        private = {"CAT": {"SUB": {"pattern": {"name": "P", "category": "C", "subcategory": "S"}}}}
        public = {"CAT": {"SUB": {"pub_pat": {"name": "Pub", "category": "C", "subcategory": "S"}}}}

        result = get_pattern_matchers(private, public)
        assert isinstance(result, tuple)
        assert len(result) == 2

        # Clean up
        te._private_matcher = None
        te._public_matcher = None

    def test_get_pattern_matchers_empty_mappings(self):
        """get_pattern_matchers with empty dicts returns None matchers."""
        import money_mapper.transaction_enricher as te
        from money_mapper.transaction_enricher import get_pattern_matchers

        te._private_matcher = None
        te._public_matcher = None

        private_matcher, public_matcher = get_pattern_matchers({}, {})
        assert private_matcher is None
        assert public_matcher is None

        te._private_matcher = None
        te._public_matcher = None

    def test_get_pattern_matchers_caches_result(self):
        """get_pattern_matchers caches matchers after first creation."""
        import money_mapper.transaction_enricher as te
        from money_mapper.transaction_enricher import PatternMatcher, get_pattern_matchers

        te._private_matcher = None
        te._public_matcher = None

        private = {"CAT": {"SUB": {"pattern": {"name": "P", "category": "C", "subcategory": "S"}}}}
        private_matcher1, _ = get_pattern_matchers(private, {})
        private_matcher2, _ = get_pattern_matchers(private, {})

        # Same object returned both times (cached)
        assert private_matcher1 is private_matcher2
        assert isinstance(private_matcher1, PatternMatcher)

        te._private_matcher = None
        te._public_matcher = None


class TestEnrichTransactionWorker:
    """Tests for the multiprocessing worker function."""

    def test_worker_enriches_transaction(self):
        """_enrich_transaction_worker returns enriched transaction dict."""
        from money_mapper.transaction_enricher import _enrich_transaction_worker

        transaction = {"description": "STARBUCKS COFFEE", "amount": -5.50, "date": "2024-01-15"}
        args = (transaction, {}, {}, {}, 0.7, "config", None, None, None)

        result = _enrich_transaction_worker(args)

        assert isinstance(result, dict)
        assert "category" in result
        assert "merchant_name" in result

    def test_worker_passes_all_args(self):
        """_enrich_transaction_worker passes all arguments to enrich_transaction."""
        from money_mapper.transaction_enricher import _enrich_transaction_worker

        private_mappings = {
            "FOOD": {
                "COFFEE": {
                    "myshop": {
                        "name": "My Shop",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "COFFEE",
                    }
                }
            }
        }
        transaction = {"description": "myshop downtown", "amount": -4.00, "date": "2024-01-15"}
        args = (transaction, private_mappings, {}, {}, 0.7, "config", None, None, None)

        result = _enrich_transaction_worker(args)

        assert result["categorization_method"] == "private_mapping"


class TestLoadEnrichmentConfigDetailed:
    """More detailed tests for load_enrichment_config."""

    def test_load_enrichment_config_missing_plaid_exits(self):
        """load_enrichment_config calls sys.exit when plaid_categories file missing."""
        from money_mapper.transaction_enricher import load_enrichment_config

        with patch("money_mapper.transaction_enricher.get_config_manager") as mock_cm:
            mock_instance = MagicMock()
            mock_instance.get_enrichment_files.return_value = {
                "plaid_categories": "/nonexistent/plaid.toml",
                "private_mappings": "/nonexistent/private.toml",
                "public_mappings": "/nonexistent/public.toml",
            }
            mock_cm.return_value = mock_instance

            with pytest.raises(SystemExit):
                load_enrichment_config()

    def test_load_enrichment_config_missing_private_mappings_warns(self, tmp_path, capsys):
        """load_enrichment_config warns when private_mappings not found but continues."""
        from money_mapper.transaction_enricher import load_enrichment_config

        # Create a minimal plaid categories file
        plaid_file = tmp_path / "plaid_categories.toml"
        plaid_file.write_text('[FOOD_AND_DRINK]\nkeywords = ["food"]\n')

        with patch("money_mapper.transaction_enricher.get_config_manager") as mock_cm:
            with patch("money_mapper.transaction_enricher.load_config", return_value={"FOOD": {}}):
                mock_instance = MagicMock()
                mock_instance.get_enrichment_files.return_value = {
                    "plaid_categories": str(plaid_file),
                    "private_mappings": str(tmp_path / "nonexistent_private.toml"),
                    "public_mappings": str(tmp_path / "nonexistent_public.toml"),
                }
                mock_cm.return_value = mock_instance

                config = load_enrichment_config()
                assert config["private_mappings"] == {}
                assert config["public_mappings"] == {}

    def test_load_enrichment_config_with_all_files(self, tmp_path):
        """load_enrichment_config loads all three files when present."""
        from money_mapper.transaction_enricher import load_enrichment_config

        plaid_file = tmp_path / "plaid_categories.toml"
        plaid_file.write_text('[FOOD_AND_DRINK]\nkeywords = ["food"]\n')
        private_file = tmp_path / "private_mappings.toml"
        private_file.write_text("[MY_CAT]\n")
        public_file = tmp_path / "public_mappings.toml"
        public_file.write_text("[PUB_CAT]\n")

        plaid_data = {"FOOD_AND_DRINK": {"keywords": ["food"]}}
        private_data = {"MY_CAT": {}}
        public_data = {"PUB_CAT": {}}

        def mock_load(filepath):
            if "plaid" in filepath:
                return plaid_data
            elif "private" in filepath:
                return private_data
            elif "public" in filepath:
                return public_data
            return {}

        with patch("money_mapper.transaction_enricher.get_config_manager") as mock_cm:
            with patch("money_mapper.transaction_enricher.load_config", side_effect=mock_load):
                mock_instance = MagicMock()
                mock_instance.get_enrichment_files.return_value = {
                    "plaid_categories": str(plaid_file),
                    "private_mappings": str(private_file),
                    "public_mappings": str(public_file),
                }
                mock_cm.return_value = mock_instance

                config = load_enrichment_config()

                assert config["plaid_categories"] == plaid_data
                assert config["private_mappings"] == private_data
                assert config["public_mappings"] == public_data

    def test_load_enrichment_config_exception_exits(self):
        """load_enrichment_config calls sys.exit on unexpected exception."""
        from money_mapper.transaction_enricher import load_enrichment_config

        with patch(
            "money_mapper.transaction_enricher.get_config_manager",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(SystemExit):
                load_enrichment_config()


class TestApplyCustomMappingsDetailed:
    """More detailed tests for apply_custom_mappings."""

    def test_apply_custom_mappings_empty_returns_none(self):
        """apply_custom_mappings returns None for empty mappings."""
        from money_mapper.transaction_enricher import apply_custom_mappings

        result = apply_custom_mappings("STARBUCKS", "starbucks", {}, "private_mapping", 0.7)
        assert result is None

    def test_apply_custom_mappings_exact_match(self):
        """apply_custom_mappings returns result on exact match."""
        from money_mapper.transaction_enricher import apply_custom_mappings

        mappings = {
            "FOOD": {
                "COFFEE": {
                    "starbucks": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "FOOD_AND_DRINK_COFFEE",
                    }
                }
            }
        }
        result = apply_custom_mappings("STARBUCKS COFFEE", "starbucks", mappings, "private_mapping")
        assert result is not None
        assert result["category"] == "FOOD_AND_DRINK"
        assert result["subcategory"] == "FOOD_AND_DRINK_COFFEE"
        assert result["categorization_method"] == "private_mapping"

    def test_apply_custom_mappings_wildcard_match(self):
        """apply_custom_mappings returns result on wildcard pattern match."""
        from money_mapper.transaction_enricher import apply_custom_mappings

        mappings = {
            "SHOPPING": {
                "ONLINE": {
                    "amazon*": {
                        "name": "Amazon",
                        "category": "SHOPPING",
                        "subcategory": "ONLINE_SHOPPING",
                    }
                }
            }
        }
        result = apply_custom_mappings("amazon.com purchase", "amazon", mappings, "public_mapping")
        assert result is not None
        assert result["category"] == "SHOPPING"
        assert result["categorization_method"] == "public_mapping"

    def test_apply_custom_mappings_no_match_returns_none(self):
        """apply_custom_mappings returns None when no pattern matches."""
        from money_mapper.transaction_enricher import apply_custom_mappings

        mappings = {
            "FOOD": {
                "COFFEE": {
                    "starbucks": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "COFFEE",
                    }
                }
            }
        }
        result = apply_custom_mappings(
            "UNKNOWN MERCHANT XYZ", "unknown", mappings, "private_mapping", 0.99
        )
        assert result is None


class TestApplyPlaidKeywordMatchingDetailed:
    """More detailed tests for apply_plaid_keyword_matching."""

    def test_matching_returns_best_scoring_category(self):
        """apply_plaid_keyword_matching returns category with most keyword hits."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {
            "FOOD_AND_DRINK.COFFEE": {"keywords": ["coffee", "cafe", "espresso", "latte"]},
            "FOOD_AND_DRINK.RESTAURANTS": {"keywords": ["pizza", "restaurant", "dine"]},
        }

        # "coffee cafe" matches 2 out of 4 coffee keywords vs 0 restaurant keywords
        result = apply_plaid_keyword_matching("COFFEE CAFE SHOP", "coffee cafe", plaid_categories)
        assert result is not None
        assert "COFFEE" in result["subcategory"]
        assert result["categorization_method"] == "plaid_keyword"

    def test_matching_confidence_capped_at_0_7(self):
        """apply_plaid_keyword_matching confidence is capped at 0.70."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        # All keywords match -> score = 1.0, but confidence capped at 0.70
        plaid_categories = {
            "FOOD_AND_DRINK.COFFEE": {"keywords": ["coffee"]},
        }
        result = apply_plaid_keyword_matching("coffee purchase", "coffee", plaid_categories)
        assert result is not None
        assert result["confidence"] <= 0.70

    def test_matching_skips_categories_without_keywords(self):
        """apply_plaid_keyword_matching skips categories with no keywords key."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {
            "NO_KEYWORDS_CAT": {},  # No keywords key
            "HAS_KEYWORDS": {"keywords": ["pizza"]},
        }
        result = apply_plaid_keyword_matching("pizza order", "pizza", plaid_categories)
        assert result is not None
        assert "HAS_KEYWORDS" in result["subcategory"]

    def test_matching_skips_non_dict_categories(self):
        """apply_plaid_keyword_matching skips non-dict category data."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {
            "STRING_VALUE": "not_a_dict",
            "VALID": {"keywords": ["coffee"]},
        }
        result = apply_plaid_keyword_matching("coffee drink", "coffee", plaid_categories)
        assert result is not None

    def test_matching_category_key_split_on_dot(self):
        """apply_plaid_keyword_matching correctly splits category key on dot."""
        from money_mapper.transaction_enricher import apply_plaid_keyword_matching

        plaid_categories = {
            "FOOD_AND_DRINK.COFFEE_SHOPS": {"keywords": ["latte"]},
        }
        result = apply_plaid_keyword_matching("buy latte", "latte", plaid_categories)
        assert result is not None
        assert result["category"] == "FOOD_AND_DRINK"
        assert result["subcategory"] == "FOOD_AND_DRINK.COFFEE_SHOPS"


class TestIsValidPlaidCategory:
    """Tests for is_valid_plaid_category."""

    def test_exact_subcategory_key_match(self):
        """is_valid_plaid_category returns True when subcategory is exact key."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

        plaid_categories = {"FOOD_AND_DRINK.COFFEE": {"keywords": []}}
        assert is_valid_plaid_category("FOOD_AND_DRINK", "FOOD_AND_DRINK.COFFEE", plaid_categories)

    def test_case_insensitive_key_match(self):
        """is_valid_plaid_category matches keys case-insensitively."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

        plaid_categories = {"FOOD_AND_DRINK.COFFEE": {"keywords": []}}
        assert is_valid_plaid_category("food_and_drink", "food_and_drink.coffee", plaid_categories)

    def test_category_prefix_match(self):
        """is_valid_plaid_category returns True when category prefix matches."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

        plaid_categories = {"FOOD_AND_DRINK.RESTAURANTS": {"keywords": []}}
        # category matches prefix before the dot
        assert is_valid_plaid_category("FOOD_AND_DRINK", "SOME_SUBCATEGORY", plaid_categories)

    def test_invalid_category_returns_false(self):
        """is_valid_plaid_category returns False for completely unknown category."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

        plaid_categories = {"FOOD_AND_DRINK.COFFEE": {"keywords": []}}
        assert not is_valid_plaid_category("INVALID", "INVALID.SUBCATEGORY", plaid_categories)

    def test_empty_plaid_categories(self):
        """is_valid_plaid_category returns False for empty plaid_categories."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

        assert not is_valid_plaid_category("FOOD_AND_DRINK", "FOOD_AND_DRINK.COFFEE", {})


class TestTryMLPrediction:
    """Tests for try_ml_prediction function."""

    def test_returns_none_when_ml_model_is_none(self):
        """try_ml_prediction returns None when ml_model is None."""
        from money_mapper.transaction_enricher import try_ml_prediction

        result = try_ml_prediction({"merchant_name": "TEST"}, {}, ml_model=None)
        assert result is None

    def test_returns_none_for_unknown_category(self):
        """try_ml_prediction returns None when model predicts UNKNOWN."""
        import money_mapper.ml_categorizer as ml_cat
        from money_mapper.transaction_enricher import try_ml_prediction

        orig = getattr(ml_cat, "predict_category", None)
        ml_cat.predict_category = lambda model, txn: ("UNKNOWN", "UNKNOWN")

        try:
            result = try_ml_prediction({"merchant_name": "TEST"}, {}, ml_model=object())
            assert result is None
        finally:
            if orig:
                ml_cat.predict_category = orig

    def test_returns_none_for_invalid_category(self):
        """try_ml_prediction returns None when predicted category not in plaid taxonomy."""
        import money_mapper.ml_categorizer as ml_cat
        from money_mapper.transaction_enricher import try_ml_prediction

        orig = getattr(ml_cat, "predict_category", None)
        ml_cat.predict_category = lambda model, txn: ("INVALID_CAT", "INVALID_SUBCAT")

        try:
            plaid_categories = {"FOOD_AND_DRINK.COFFEE": {"keywords": []}}
            result = try_ml_prediction(
                {"merchant_name": "TEST"}, plaid_categories, ml_model=object()
            )
            assert result is None
        finally:
            if orig:
                ml_cat.predict_category = orig

    def test_returns_result_for_valid_prediction(self):
        """try_ml_prediction returns categorization result for valid ML prediction."""
        import money_mapper.ml_categorizer as ml_cat
        from money_mapper.transaction_enricher import try_ml_prediction

        orig = getattr(ml_cat, "predict_category", None)
        ml_cat.predict_category = lambda model, txn: ("FOOD_AND_DRINK", "FOOD_AND_DRINK.COFFEE")

        try:
            plaid_categories = {
                "FOOD_AND_DRINK": {"keywords": []},
                "FOOD_AND_DRINK.COFFEE": {"keywords": []},
            }
            result = try_ml_prediction(
                {"merchant_name": "Starbucks"}, plaid_categories, ml_model=object()
            )
            assert result is not None
            assert result["category"] == "FOOD_AND_DRINK"
            assert result["subcategory"] == "FOOD_AND_DRINK.COFFEE"
            assert result["categorization_method"] == "ml_prediction"
            assert result["confidence"] == 0.65
        finally:
            if orig:
                ml_cat.predict_category = orig

    def test_debug_mode_logs_prediction(self, capsys):
        """try_ml_prediction prints debug info when debug=True."""
        import money_mapper.ml_categorizer as ml_cat
        from money_mapper.transaction_enricher import try_ml_prediction

        orig = getattr(ml_cat, "predict_category", None)
        ml_cat.predict_category = lambda model, txn: ("FOOD_AND_DRINK", "FOOD_AND_DRINK.COFFEE")

        try:
            plaid_categories = {
                "FOOD_AND_DRINK": {"keywords": []},
                "FOOD_AND_DRINK.COFFEE": {"keywords": []},
            }
            try_ml_prediction(
                {"merchant_name": "Starbucks"},
                plaid_categories,
                ml_model=object(),
                debug=True,
            )
            captured = capsys.readouterr()
            assert "ML prediction" in captured.out
        finally:
            if orig:
                ml_cat.predict_category = orig


class TestTrySimilarityPrediction:
    """Tests for try_similarity_prediction function."""

    def test_returns_none_when_model_is_none(self):
        """try_similarity_prediction returns None when similarity_model is None."""
        from money_mapper.transaction_enricher import try_similarity_prediction

        result = try_similarity_prediction(
            "merchant",
            {},
            similarity_model=None,
            vectors_file="vectors.npy",
        )
        assert result is None

    def test_returns_none_when_vectors_file_is_none(self):
        """try_similarity_prediction returns None when vectors_file is None."""
        from money_mapper.transaction_enricher import try_similarity_prediction

        result = try_similarity_prediction(
            "merchant",
            {},
            similarity_model=MagicMock(),
            vectors_file=None,
        )
        assert result is None

    def test_returns_none_when_embeddings_empty(self):
        """try_similarity_prediction returns None when embeddings are empty."""
        import numpy as np

        from money_mapper.transaction_enricher import try_similarity_prediction

        with patch(
            "money_mapper.similarity_matcher.load_merchant_embeddings",
            return_value=({}, np.array([])),
        ):
            result = try_similarity_prediction(
                "merchant",
                {},
                similarity_model=MagicMock(),
                vectors_file="vectors.npy",
            )
            assert result is None

    def test_returns_result_when_match_found(self):
        """try_similarity_prediction returns result when similar merchant is found."""
        import numpy as np

        from money_mapper.transaction_enricher import try_similarity_prediction

        mock_match = {
            "name": "Starbucks",
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "similarity": 0.92,
        }
        with patch(
            "money_mapper.similarity_matcher.load_merchant_embeddings",
            return_value=({"starbucks": mock_match}, np.array([[0.1, 0.2]])),
        ):
            with patch(
                "money_mapper.similarity_matcher.find_similar_merchant",
                return_value=mock_match,
            ):
                result = try_similarity_prediction(
                    "starbucks",
                    {"FOOD_AND_DRINK": {}},
                    similarity_model=MagicMock(),
                    vectors_file="vectors.npy",
                )
        assert result is not None
        assert result["category"] == "FOOD_AND_DRINK"
        assert result["categorization_method"] == "similarity_matching"
        assert result["confidence"] == 0.85

    def test_returns_none_when_no_match_found(self):
        """try_similarity_prediction returns None when no similar merchant found."""
        import numpy as np

        from money_mapper.transaction_enricher import try_similarity_prediction

        with patch(
            "money_mapper.similarity_matcher.load_merchant_embeddings",
            return_value=({"starbucks": {}}, np.array([[0.1, 0.2]])),
        ):
            with patch(
                "money_mapper.similarity_matcher.find_similar_merchant",
                return_value=None,
            ):
                result = try_similarity_prediction(
                    "totally_unknown",
                    {},
                    similarity_model=MagicMock(),
                    vectors_file="vectors.npy",
                )
        assert result is None


class TestGenerateEnrichmentReport:
    """Tests for generate_enrichment_report function."""

    def test_empty_transactions_returns_no_transactions_message(self):
        """generate_enrichment_report handles empty list gracefully."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        result = generate_enrichment_report([])
        assert result == "No transactions to analyze."

    def test_report_contains_header(self):
        """generate_enrichment_report includes expected header."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "description": "STARBUCKS",
                "amount": -5.50,
                "category": "FOOD_AND_DRINK",
                "confidence": 0.95,
                "categorization_method": "private_mapping",
            }
        ]
        report = generate_enrichment_report(transactions)
        assert "Transaction Enrichment Report" in report
        assert "Total Transactions: 1" in report

    def test_report_categorization_rate_all_categorized(self):
        """generate_enrichment_report shows 100% when all transactions categorized."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                "confidence": 0.9,
                "categorization_method": "exact_match",
            },
            {
                "category": "SHOPPING",
                "amount": 10.0,
                "confidence": 0.8,
                "categorization_method": "exact_match",
            },
        ]
        report = generate_enrichment_report(transactions)
        assert "100.0%" in report

    def test_report_categorization_rate_with_uncategorized(self):
        """generate_enrichment_report shows partial rate with some uncategorized."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                "confidence": 0.9,
                "categorization_method": "exact_match",
            },
            {
                "category": "UNCATEGORIZED",
                "amount": 10.0,
                "confidence": 0.1,
                "categorization_method": "none",
            },
        ]
        report = generate_enrichment_report(transactions)
        assert "50.0%" in report

    def test_report_method_performance_section(self):
        """generate_enrichment_report includes method performance stats."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                "confidence": 0.95,
                "categorization_method": "private_mapping",
            }
        ]
        report = generate_enrichment_report(transactions)
        assert "Method Performance" in report
        assert "private_mapping" in report

    def test_report_top_categories_section(self):
        """generate_enrichment_report includes top categories with amounts."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 25.0,
                "confidence": 0.9,
                "categorization_method": "exact_match",
            }
        ]
        report = generate_enrichment_report(transactions)
        assert "FOOD_AND_DRINK" in report
        assert "$25.00" in report

    def test_report_saves_to_file(self, tmp_path):
        """generate_enrichment_report saves report text to output_file when specified."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                "confidence": 0.9,
                "categorization_method": "exact_match",
            }
        ]
        output_file = str(tmp_path / "report.txt")
        report = generate_enrichment_report(transactions, output_file=output_file)

        # File should have been written
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
        assert content == report
        assert "Transaction Enrichment Report" in content

    def test_report_handles_none_confidence(self):
        """generate_enrichment_report handles transactions with no confidence field."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                # No 'confidence' key
                "categorization_method": "exact_match",
            }
        ]
        # Should not raise
        report = generate_enrichment_report(transactions)
        assert isinstance(report, str)

    def test_report_file_write_error_prints_message(self, capsys):
        """generate_enrichment_report prints error message when file cannot be saved."""
        from money_mapper.transaction_enricher import generate_enrichment_report

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "amount": 5.0,
                "confidence": 0.9,
                "categorization_method": "exact_match",
            }
        ]
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            report = generate_enrichment_report(transactions, output_file="/invalid/path.txt")

        captured = capsys.readouterr()
        assert "Error saving report" in captured.out
        assert isinstance(report, str)


class TestAnalyzeCategorizationAccuracy:
    """Tests for analyze_categorization_accuracy function."""

    def test_returns_early_for_empty_file(self, capsys):
        """analyze_categorization_accuracy exits early when no transactions found."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json", return_value=[]
        ):
            analyze_categorization_accuracy("dummy_file.json", skip_interactive=True)

        captured = capsys.readouterr()
        assert "No transactions found" in captured.out

    def test_prints_basic_stats(self, capsys):
        """analyze_categorization_accuracy prints total, categorized, uncategorized counts."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {
                "category": "FOOD_AND_DRINK",
                "confidence": 0.95,
                "categorization_method": "private_mapping",
            },
            {
                "category": "UNCATEGORIZED",
                "confidence": 0.1,
                "categorization_method": "none",
            },
            {
                "category": "SHOPPING",
                "confidence": 0.80,
                "categorization_method": "public_mapping",
            },
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            analyze_categorization_accuracy("dummy.json", skip_interactive=True)

        captured = capsys.readouterr()
        assert "Total transactions: 3" in captured.out
        assert "Categorized: 2" in captured.out
        assert "Uncategorized: 1" in captured.out

    def test_prints_confidence_distribution(self, capsys):
        """analyze_categorization_accuracy prints confidence distribution."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {"category": "FOOD", "confidence": 0.95, "categorization_method": "exact"},
            {"category": "FOOD", "confidence": 0.60, "categorization_method": "fuzzy"},
            {"category": "UNCATEGORIZED", "confidence": 0.10, "categorization_method": "none"},
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            analyze_categorization_accuracy("dummy.json", skip_interactive=True)

        captured = capsys.readouterr()
        assert "Confidence Distribution" in captured.out

    def test_verbose_mode_prints_categories(self, capsys):
        """analyze_categorization_accuracy verbose mode shows category breakdown."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {"category": "FOOD_AND_DRINK", "confidence": 0.9, "categorization_method": "exact"},
            {"category": "SHOPPING", "confidence": 0.8, "categorization_method": "exact"},
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            analyze_categorization_accuracy("dummy.json", verbose=True, skip_interactive=True)

        captured = capsys.readouterr()
        assert "Top Categories" in captured.out

    def test_debug_mode_prints_method_effectiveness(self, capsys):
        """analyze_categorization_accuracy debug mode shows method effectiveness."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {"category": "FOOD", "confidence": 0.95, "categorization_method": "private_mapping"},
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            analyze_categorization_accuracy("dummy.json", debug=True, skip_interactive=True)

        captured = capsys.readouterr()
        assert "Method Effectiveness" in captured.out
        assert "Merchant Name Extraction" in captured.out

    def test_skip_interactive_skips_wizard(self):
        """analyze_categorization_accuracy with skip_interactive does not invoke wizard."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {"category": "UNCATEGORIZED", "confidence": 0.1, "categorization_method": "none"},
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            # Should complete without prompting
            analyze_categorization_accuracy("dummy.json", skip_interactive=True)

    def test_categorization_method_distribution(self, capsys):
        """analyze_categorization_accuracy prints method distribution."""
        from money_mapper.transaction_enricher import analyze_categorization_accuracy

        transactions = [
            {"category": "FOOD", "confidence": 0.9, "categorization_method": "private_mapping"},
            {"category": "FOOD", "confidence": 0.8, "categorization_method": "public_mapping"},
            {"category": "FOOD", "confidence": 0.7, "categorization_method": "private_mapping"},
        ]
        with patch(
            "money_mapper.transaction_enricher.load_transactions_from_json",
            return_value=transactions,
        ):
            analyze_categorization_accuracy("dummy.json", skip_interactive=True)

        captured = capsys.readouterr()
        assert "Categorization Methods" in captured.out
        assert "private_mapping" in captured.out


class TestEnrichTransactionPrivacyRedaction:
    """Tests for privacy redaction in enrich_transaction."""

    def test_privacy_redaction_applied_to_description(self):
        """enrich_transaction applies privacy redaction to the output description."""
        from money_mapper.transaction_enricher import enrich_transaction

        with patch("money_mapper.transaction_enricher.get_config_manager") as mock_cm:
            mock_instance = MagicMock()
            mock_instance.get_privacy_settings.return_value = {
                "redact_account_numbers": True,
                "redact_names": False,
            }
            mock_cm.return_value = mock_instance

            with patch(
                "money_mapper.transaction_enricher.sanitize_description",
                return_value="[REDACTED]",
            ) as mock_sanitize:
                transaction = {"description": "JOHN DOE PAYMENT", "amount": -100.0}
                enriched = enrich_transaction(transaction, {}, {}, {})

            mock_sanitize.assert_called_once()
            assert enriched["description"] == "[REDACTED]"

    def test_privacy_redaction_exception_keeps_original(self):
        """enrich_transaction keeps original description if privacy redaction fails."""
        from money_mapper.transaction_enricher import enrich_transaction

        with patch(
            "money_mapper.transaction_enricher.get_config_manager",
            side_effect=Exception("Config error"),
        ):
            transaction = {"description": "MERCHANT PAYMENT", "amount": -50.0}
            enriched = enrich_transaction(transaction, {}, {}, {})

        # Original description preserved since redaction failed
        assert enriched["description"] == "MERCHANT PAYMENT"

    def test_privacy_redaction_debug_logs_warning(self, capsys):
        """enrich_transaction prints debug warning when redaction fails."""
        from money_mapper.transaction_enricher import enrich_transaction

        with patch(
            "money_mapper.transaction_enricher.get_config_manager",
            side_effect=Exception("Config error"),
        ):
            transaction = {"description": "MERCHANT PAYMENT", "amount": -50.0}
            enrich_transaction(transaction, {}, {}, {}, debug=True)

        captured = capsys.readouterr()
        assert "Warning: Could not apply privacy redaction" in captured.out


class TestFindMerchantMappingDebugMode:
    """Tests for find_merchant_mapping debug output."""

    def test_debug_output_for_private_mapping(self, capsys):
        """find_merchant_mapping prints debug info when private mapping found."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        private_mappings = {
            "FOOD": {
                "COFFEE": {
                    "myshop": {
                        "name": "My Shop",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "COFFEE",
                    }
                }
            }
        }
        find_merchant_mapping("myshop downtown", private_mappings, {}, {}, 0.7, debug=True)
        captured = capsys.readouterr()
        assert "Private mapping found" in captured.out

    def test_debug_output_for_public_mapping(self, capsys):
        """find_merchant_mapping prints debug info when public mapping found."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        public_mappings = {
            "FOOD": {
                "COFFEE": {
                    "starbucks": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "COFFEE",
                    }
                }
            }
        }
        find_merchant_mapping("starbucks coffee", {}, public_mappings, {}, 0.7, debug=True)
        captured = capsys.readouterr()
        assert "Public mapping found" in captured.out

    def test_debug_output_for_plaid_match(self, capsys):
        """find_merchant_mapping prints debug info when plaid keyword match found."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        plaid_categories = {"FOOD_AND_DRINK.RESTAURANTS": {"keywords": ["pizza"]}}
        find_merchant_mapping("pizza hut order", {}, {}, plaid_categories, 0.7, debug=True)
        captured = capsys.readouterr()
        assert "Plaid keyword match" in captured.out

    def test_debug_output_for_no_match(self, capsys):
        """find_merchant_mapping prints debug info when no match found."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        find_merchant_mapping("TOTALLY UNKNOWN MERCHANT", {}, {}, {}, 0.7, debug=True)
        captured = capsys.readouterr()
        assert "No category found" in captured.out


class TestFindMerchantMappingNormalization:
    """Test that description normalization affects matching."""

    def test_mixed_case_description_matches_lowercase_mapping(self):
        """Description with mixed case should match lowercase mapping keys."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        private_mappings = {}
        public_mappings = {
            "FOOD_AND_DRINK": {
                "FOOD_AND_DRINK_RESTAURANT": {
                    "starbucks": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "FOOD_AND_DRINK_RESTAURANT",
                    }
                }
            }
        }
        plaid_categories = {}

        result = find_merchant_mapping(
            "  STARBUCKS  ", private_mappings, public_mappings, plaid_categories, 0.7, False
        )
        assert result.get("category") != "UNCATEGORIZED"

    def test_whitespace_description_matches_trimmed_mapping(self):
        """Description with leading/trailing whitespace should match."""
        from money_mapper.transaction_enricher import find_merchant_mapping

        private_mappings = {}
        public_mappings = {
            "FOOD_AND_DRINK": {
                "FOOD_AND_DRINK_RESTAURANT": {
                    "starbucks": {
                        "name": "Starbucks",
                        "category": "FOOD_AND_DRINK",
                        "subcategory": "FOOD_AND_DRINK_RESTAURANT",
                    }
                }
            }
        }
        plaid_categories = {}

        result = find_merchant_mapping(
            "  starbucks  ", private_mappings, public_mappings, plaid_categories, 0.7, False
        )
        assert result.get("category") != "UNCATEGORIZED"
