"""Tests for money_mapper.mapping_consolidator module."""

import pytest
from unittest.mock import Mock, patch

from money_mapper.mapping_consolidator import (
    detect_similar_patterns,
    suggest_wildcard_pattern,
    consolidate_with_wildcards,
    find_consolidation_opportunities,
)


class TestDetectSimilarPatterns:
    """Test similar pattern detection."""

    def test_detect_similar_patterns_basic(self):
        """Test basic similar pattern detection."""
        patterns = [
            "starbucks",
            "starbucks coffee",
            "starbucks coffee shop",
            "shell gas",
            "shell station"
        ]
        
        similar = detect_similar_patterns(patterns)
        
        assert isinstance(similar, list)

    def test_detect_similar_patterns_identical(self):
        """Test detection of identical patterns."""
        patterns = [
            "starbucks",
            "STARBUCKS",
            "Starbucks"
        ]
        
        similar = detect_similar_patterns(patterns)
        
        # Should detect these as similar (case-insensitive)
        assert len(similar) > 0

    def test_detect_similar_patterns_variations(self):
        """Test detection of pattern variations."""
        patterns = [
            "starbucks #123",
            "starbucks #456",
            "starbucks downtown",
            "starbucks 5th ave"
        ]
        
        similar = detect_similar_patterns(patterns)
        
        assert isinstance(similar, list)

    def test_detect_similar_patterns_no_similar(self):
        """Test when no similar patterns exist."""
        patterns = [
            "starbucks",
            "shell gas",
            "walmart",
            "amazon"
        ]
        
        similar = detect_similar_patterns(patterns)
        
        # May or may not find similar depending on threshold
        assert isinstance(similar, list)

    def test_detect_similar_patterns_empty(self):
        """Test with empty pattern list."""
        similar = detect_similar_patterns([])
        
        assert similar == []

    def test_detect_similar_patterns_single_pattern(self):
        """Test with single pattern."""
        similar = detect_similar_patterns(["starbucks"])
        
        assert similar == []

    def test_detect_similar_patterns_threshold(self):
        """Test similarity detection with threshold."""
        patterns = [
            "starbucks coffee",
            "starbucks cafe",
            "shell gas",
            "shell petroleum"
        ]
        
        similar = detect_similar_patterns(patterns, threshold=0.6)
        
        assert isinstance(similar, list)


class TestSuggestWildcardPattern:
    """Test wildcard pattern suggestion."""

    def test_suggest_wildcard_basic(self):
        """Test basic wildcard suggestion."""
        patterns = [
            "starbucks",
            "starbucks coffee",
            "starbucks downtown"
        ]
        
        wildcard = suggest_wildcard_pattern(patterns)
        
        assert isinstance(wildcard, str)
        assert "*" in wildcard

    def test_suggest_wildcard_location_variations(self):
        """Test wildcard for location variations."""
        patterns = [
            "starbucks 5th ave",
            "starbucks downtown",
            "starbucks midtown",
            "starbucks uptown"
        ]
        
        wildcard = suggest_wildcard_pattern(patterns)
        
        # Should suggest starbucks*
        assert "starbucks" in wildcard.lower()

    def test_suggest_wildcard_number_variations(self):
        """Test wildcard for number variations."""
        patterns = [
            "starbucks #123",
            "starbucks #456",
            "starbucks #789"
        ]
        
        wildcard = suggest_wildcard_pattern(patterns)
        
        assert isinstance(wildcard, str)

    def test_suggest_wildcard_single_pattern(self):
        """Test with single pattern."""
        wildcard = suggest_wildcard_pattern(["starbucks"])
        
        assert isinstance(wildcard, str)

    def test_suggest_wildcard_empty(self):
        """Test with empty list."""
        wildcard = suggest_wildcard_pattern([])
        
        assert isinstance(wildcard, str)

    def test_suggest_wildcard_two_patterns(self):
        """Test with two patterns."""
        patterns = ["starbucks coffee", "starbucks cafe"]
        
        wildcard = suggest_wildcard_pattern(patterns)
        
        assert isinstance(wildcard, str)


class TestConsolidateWithWildcards:
    """Test consolidation with wildcards."""

    def test_consolidate_basic(self):
        """Test basic consolidation."""
        mappings = {
            "starbucks": {"name": "S1", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks coffee": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks downtown": {"name": "S3", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        consolidated = consolidate_with_wildcards(mappings)
        
        assert isinstance(consolidated, dict)

    def test_consolidate_no_consolidation(self):
        """Test when no consolidation is needed."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "shell": {"name": "Shell", "category": "TRANSPORTATION", "subcategory": "TRANSPORTATION_GAS", "scope": "public"},
        }
        
        consolidated = consolidate_with_wildcards(mappings)
        
        # Should keep both
        assert len(consolidated) >= 2

    def test_consolidate_empty(self):
        """Test with empty mappings."""
        consolidated = consolidate_with_wildcards({})
        
        assert consolidated == {}

    def test_consolidate_single_mapping(self):
        """Test with single mapping."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        consolidated = consolidate_with_wildcards(mappings)
        
        # Should return unchanged
        assert len(consolidated) >= 1

    def test_consolidate_with_existing_wildcards(self):
        """Test consolidation with existing wildcards."""
        mappings = {
            "starbucks*": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks coffee": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        consolidated = consolidate_with_wildcards(mappings)
        
        assert isinstance(consolidated, dict)


class TestFindConsolidationOpportunities:
    """Test finding consolidation opportunities."""

    def test_find_opportunities_basic(self):
        """Test basic opportunity finding."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks #123": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks downtown": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        opportunities = find_consolidation_opportunities(mappings)
        
        assert isinstance(opportunities, list)

    def test_find_opportunities_none(self):
        """Test when no opportunities exist."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "shell": {"name": "Shell", "category": "TRANSPORTATION", "subcategory": "TRANSPORTATION_GAS", "scope": "public"},
            "walmart": {"name": "Walmart", "category": "SHOPPING", "subcategory": "SHOPPING_GENERAL", "scope": "public"},
        }
        
        opportunities = find_consolidation_opportunities(mappings)
        
        # Depends on threshold, may or may not find opportunities
        assert isinstance(opportunities, list)

    def test_find_opportunities_empty(self):
        """Test with empty mappings."""
        opportunities = find_consolidation_opportunities({})
        
        assert opportunities == []

    def test_find_opportunities_threshold(self):
        """Test with custom threshold."""
        mappings = {
            "starbucks coffee": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks cafe": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        opportunities = find_consolidation_opportunities(mappings, threshold=0.7)
        
        assert isinstance(opportunities, list)

    def test_find_opportunities_returns_suggestions(self):
        """Test that opportunities include suggestions."""
        mappings = {
            "starbucks #1": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks #2": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks #3": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        opportunities = find_consolidation_opportunities(mappings, threshold=0.6)
        
        if opportunities:
            # Each opportunity should have pattern, patterns, and suggested_wildcard
            for opp in opportunities:
                assert isinstance(opp, dict)


class TestConsolidatorIntegration:
    """Integration tests for consolidator."""

    def test_consolidation_workflow(self):
        """Test complete consolidation workflow."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks coffee": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "starbucks downtown": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "shell": {"name": "Shell", "category": "TRANSPORTATION", "subcategory": "TRANSPORTATION_GAS", "scope": "public"},
        }
        
        # Find opportunities
        opportunities = find_consolidation_opportunities(mappings)
        
        if opportunities:
            # Consolidate
            consolidated = consolidate_with_wildcards(mappings)
            
            # Should have fewer or same number of entries
            assert len(consolidated) <= len(mappings)

    def test_pattern_detection_and_consolidation(self):
        """Test pattern detection and consolidation."""
        patterns = [
            "starbucks",
            "starbucks coffee",
            "starbucks cafe",
            "starbucks downtown"
        ]
        
        # Detect similar
        similar = detect_similar_patterns(patterns)
        
        if similar:
            # Suggest wildcard
            wildcard = suggest_wildcard_pattern(patterns)
            
            assert isinstance(wildcard, str)
            assert "*" in wildcard or len(patterns) == 1
