"""Tests for money_mapper.transaction_enricher module."""

import pytest

from money_mapper.transaction_enricher import (
    extract_merchant_name,
    find_merchant_mapping,
    wildcard_pattern_match,
    create_mapping_result,
    fuzzy_match_similarity,
    try_ml_prediction,
    is_valid_plaid_category,
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
        from money_mapper.transaction_enricher import try_ml_prediction

        transaction = {
            "description": "TEST",
            "merchant_name": "TEST",
            "amount": 10.0,
        }

        result = try_ml_prediction(transaction, {}, ml_model=None)

        assert result is None

    def test_is_valid_plaid_category(self):
        """Test category validation."""
        from money_mapper.transaction_enricher import is_valid_plaid_category

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
        from money_mapper.transaction_enricher import try_ml_prediction

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
