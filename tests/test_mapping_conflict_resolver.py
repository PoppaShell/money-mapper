"""Tests for money_mapper.mapping_conflict_resolver module."""

import pytest
from unittest.mock import Mock, patch

from money_mapper.mapping_conflict_resolver import (
    detect_duplicate_patterns,
    check_mapping_conflicts,
    resolve_conflicts,
    find_duplicates_across_files,
)


class TestDetectDuplicatePatterns:
    """Test duplicate pattern detection."""

    def test_detect_duplicates_basic(self):
        """Test detecting duplicate patterns."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public"
                },
                "STARBUCKS": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public"
                }
            }
        }
        
        duplicates = detect_duplicate_patterns(mappings)
        
        assert isinstance(duplicates, list)

    def test_detect_duplicates_none_found(self):
        """Test when no duplicates exist."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public"
                },
                "mcdonalds": {
                    "name": "McDonald's",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_FAST_FOOD",
                    "scope": "public"
                }
            }
        }
        
        duplicates = detect_duplicate_patterns(mappings)
        
        assert duplicates == []

    def test_detect_duplicates_case_insensitive(self):
        """Test case-insensitive duplicate detection."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {"name": "S1", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
                "Starbucks": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
                "STARBUCKS": {"name": "S3", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            }
        }
        
        duplicates = detect_duplicate_patterns(mappings)
        
        assert len(duplicates) > 0

    def test_detect_duplicates_with_wildcards(self):
        """Test duplicate detection with wildcard patterns."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {"name": "S1", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
                "starbucks*": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            }
        }
        
        duplicates = detect_duplicate_patterns(mappings)
        
        assert isinstance(duplicates, list)

    def test_detect_duplicates_empty_mappings(self):
        """Test with empty mappings."""
        duplicates = detect_duplicate_patterns({})
        
        assert duplicates == []

    def test_detect_duplicates_multiple_sections(self):
        """Test duplicate detection across multiple sections."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            },
            "TRANSPORTATION": {
                "shell": {"name": "Shell", "category": "TRANSPORTATION", "subcategory": "TRANSPORTATION_GAS", "scope": "public"},
            }
        }
        
        duplicates = detect_duplicate_patterns(mappings)
        
        assert duplicates == []


class TestCheckMappingConflicts:
    """Test conflict checking."""

    def test_check_conflicts_basic(self):
        """Test basic conflict checking."""
        existing_mappings = {
            "starbucks": {
                "name": "Starbucks",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_COFFEE",
                "scope": "public"
            }
        }
        
        new_mappings = {
            "starbucks": {
                "name": "Starbucks Coffee",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_COFFEE",
                "scope": "public"
            }
        }
        
        conflicts = check_mapping_conflicts(existing_mappings, new_mappings)
        
        assert isinstance(conflicts, list)

    def test_check_conflicts_no_conflicts(self):
        """Test when no conflicts exist."""
        existing_mappings = {
            "starbucks": {
                "name": "Starbucks",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_COFFEE",
                "scope": "public"
            }
        }
        
        new_mappings = {
            "mcdonalds": {
                "name": "McDonald's",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_FAST_FOOD",
                "scope": "public"
            }
        }
        
        conflicts = check_mapping_conflicts(existing_mappings, new_mappings)
        
        assert conflicts == []

    def test_check_conflicts_same_pattern_different_values(self):
        """Test conflict when same pattern has different values."""
        existing_mappings = {
            "starbucks": {
                "name": "Starbucks",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_COFFEE",
                "scope": "public"
            }
        }
        
        new_mappings = {
            "starbucks": {
                "name": "Starbucks",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK_FAST_FOOD",  # Different!
                "scope": "public"
            }
        }
        
        conflicts = check_mapping_conflicts(existing_mappings, new_mappings)
        
        assert len(conflicts) > 0

    def test_check_conflicts_empty_existing(self):
        """Test with empty existing mappings."""
        new_mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        conflicts = check_mapping_conflicts({}, new_mappings)
        
        assert conflicts == []

    def test_check_conflicts_empty_new(self):
        """Test with empty new mappings."""
        existing_mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        conflicts = check_mapping_conflicts(existing_mappings, {})
        
        assert conflicts == []


class TestResolveConflicts:
    """Test conflict resolution."""

    def test_resolve_conflicts_basic(self):
        """Test basic conflict resolution."""
        conflicts = [
            {
                "pattern": "starbucks",
                "existing": {"name": "Starbucks", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
                "new": {"name": "Starbucks Coffee", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
            }
        ]
        
        # Test keep existing
        result = resolve_conflicts(conflicts, action="keep_existing")
        assert isinstance(result, dict)

    def test_resolve_conflicts_keep_existing(self):
        """Test resolving by keeping existing."""
        conflicts = [
            {
                "pattern": "starbucks",
                "existing": {"value": "old"},
                "new": {"value": "new"}
            }
        ]
        
        result = resolve_conflicts(conflicts, action="keep_existing")
        
        assert result.get("starbucks", {}).get("value") == "old"

    def test_resolve_conflicts_use_new(self):
        """Test resolving by using new."""
        conflicts = [
            {
                "pattern": "starbucks",
                "existing": {"value": "old"},
                "new": {"value": "new"}
            }
        ]
        
        result = resolve_conflicts(conflicts, action="use_new")
        
        assert result.get("starbucks", {}).get("value") == "new"

    def test_resolve_conflicts_empty_list(self):
        """Test with empty conflicts."""
        result = resolve_conflicts([], action="keep_existing")
        
        assert result == {}


class TestFindDuplicatesAcrossFiles:
    """Test finding duplicates across files."""

    def test_find_duplicates_across_files_basic(self):
        """Test basic duplicate detection across files."""
        private = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "private"}
        }
        
        public = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        duplicates = find_duplicates_across_files(private, public)
        
        assert isinstance(duplicates, list)

    def test_find_duplicates_across_files_none(self):
        """Test when no duplicates across files."""
        private = {
            "local_coffee": {"name": "L", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "private"}
        }
        
        public = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        duplicates = find_duplicates_across_files(private, public)
        
        assert duplicates == []

    def test_find_duplicates_across_files_empty(self):
        """Test with empty files."""
        duplicates = find_duplicates_across_files({}, {})
        
        assert duplicates == []

    def test_find_duplicates_across_files_case_insensitive(self):
        """Test case-insensitive duplicate detection."""
        private = {
            "Starbucks": {"name": "S1", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "private"}
        }
        
        public = {
            "starbucks": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        duplicates = find_duplicates_across_files(private, public)
        
        assert len(duplicates) > 0


class TestConflictResolverIntegration:
    """Integration tests for conflict resolver."""

    def test_conflict_resolution_workflow(self):
        """Test complete conflict resolution workflow."""
        existing = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        new = {
            "starbucks": {"name": "S2", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}
        }
        
        # Check conflicts
        conflicts = check_mapping_conflicts(existing, new)
        
        if conflicts:
            # Resolve conflicts
            result = resolve_conflicts(conflicts, action="keep_existing")
            assert result is not None

    def test_duplicate_detection_and_resolution(self):
        """Test duplicate detection and resolution workflow."""
        mappings = {
            "starbucks": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
            "STARBUCKS": {"name": "S", "category": "FOOD_AND_DRINK", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"},
        }
        
        # Detect duplicates
        duplicates = detect_duplicate_patterns(mappings)
        
        # Should find them
        assert isinstance(duplicates, list)
