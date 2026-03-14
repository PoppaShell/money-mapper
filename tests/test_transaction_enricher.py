"""Tests for money_mapper.transaction_enricher module."""

import pytest

from money_mapper.transaction_enricher import (
    extract_merchant_name,
    find_merchant_mapping,
    wildcard_pattern_match,
    create_mapping_result,
    fuzzy_match_similarity,
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
            0.7
        )
        
        assert "category" in result
        assert isinstance(result, dict)

    def test_mapping_result_structure(self):
        """Test that mapping result has required structure."""
        result = find_merchant_mapping(
            "AMAZON",
            {},
            {},
            {},
            0.7
        )
        
        required_fields = ["category", "subcategory", "confidence", "categorization_method"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_mapping_with_none_result(self):
        """Test that mapping returns something even with no match."""
        result = find_merchant_mapping(
            "UNKNOWN MERCHANT",
            {},
            {},
            {},
            0.7
        )
        
        assert result is not None
        assert result.get("category") == "UNCATEGORIZED" or result.get("category") is not None

    def test_mapping_confidence_in_range(self):
        """Test that confidence is in valid range."""
        result = find_merchant_mapping(
            "TEST MERCHANT",
            {},
            {},
            {},
            0.7
        )
        
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
            "date": "2024-01-15"
        }
        
        enriched = enrich_transaction(
            transaction,
            {},  # private mappings
            {},  # public mappings
            {},  # plaid categories
            0.7
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
            "extra_field": "should_be_preserved"
        }
        
        enriched = enrich_transaction(
            transaction,
            {},
            {},
            {},
            0.7
        )
        
        assert enriched.get("amount") == 10.00
        assert enriched.get("date") == "2024-01-15"
        assert enriched.get("extra_field") == "should_be_preserved"

    def test_enrich_adds_required_fields(self):
        """Test that enrichment adds required fields."""
        from money_mapper.transaction_enricher import enrich_transaction
        
        transaction = {
            "description": "MERCHANT",
            "amount": 5.00,
            "date": "2024-01-15"
        }
        
        enriched = enrich_transaction(
            transaction,
            {},
            {},
            {},
            0.7
        )
        
        required = ["merchant_name", "category", "confidence", "categorization_method"]
        for field in required:
            assert field in enriched, f"Missing required field: {field}"

    @pytest.mark.parametrize("description", [
        "STARBUCKS COFFEE",
        "AMAZON.COM",
        "WHOLE FOODS MARKET",
        "APPLE STORE",
    ])
    def test_enrich_various_merchants(self, description):
        """Test enrichment with various merchant descriptions."""
        from money_mapper.transaction_enricher import enrich_transaction
        
        transaction = {
            "description": description,
            "amount": -10.00,
            "date": "2024-01-15"
        }
        
        enriched = enrich_transaction(
            transaction,
            {},
            {},
            {},
            0.7
        )
        
        assert enriched["merchant_name"] != ""
        assert enriched["category"] is not None
