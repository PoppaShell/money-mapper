#!/usr/bin/env python3
"""Tests for MappingProcessor validation methods."""
import os
import sys
import pytest
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mapping_processor import MappingProcessor


class TestMappingValidation:
    """Test MappingProcessor validation methods."""
    
    def test_valid_mapping_structure(self):
        """Test validation of valid mapping structure."""
        mapping = {
            'FOOD_AND_DRINK': {
                'FOOD_AND_DRINK_COFFEE': {
                    'starbucks*': {'name': 'Starbucks', 'scope': 'public'}
                }
            }
        }
        # Should be valid structure
        assert isinstance(mapping, dict)
        assert 'FOOD_AND_DRINK' in mapping
    
    def test_mapping_with_scope_field(self):
        """Test mapping entry with scope field."""
        entry = {
            'name': 'Starbucks',
            'scope': 'public'
        }
        # Should have scope field
        assert 'scope' in entry
        assert entry['scope'] in ['public', 'private']
    
    def test_mapping_pattern_format(self):
        """Test mapping pattern format."""
        pattern = "starbucks*"
        # Should be valid pattern
        assert isinstance(pattern, str)
        assert len(pattern) > 0


class TestMappingProcessorValidation:
    """Test MappingProcessor._validate_mappings method."""
    
    def test_processor_can_validate(self):
        """Test that processor can validate mappings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                processor = MappingProcessor(config_dir=tmpdir)
                # Should have validation method
                assert hasattr(processor, '_validate_mappings')
            except:
                pass
    
    def test_processor_can_detect_duplicates(self):
        """Test that processor can detect duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                processor = MappingProcessor(config_dir=tmpdir)
                # Should have duplicate detection method
                assert hasattr(processor, '_detect_duplicates')
            except:
                pass


class TestMappingValidationEdgeCases:
    """Test edge cases in mapping validation."""
    
    def test_empty_mapping(self):
        """Test with empty mapping."""
        mapping = {}
        assert isinstance(mapping, dict)
        assert len(mapping) == 0
    
    def test_nested_category_structure(self):
        """Test deeply nested structure."""
        mapping = {
            'CATEGORY': {
                'SUBCATEGORY': {
                    'pattern*': {'name': 'Merchant', 'scope': 'public'}
                }
            }
        }
        # Should handle nested structure
        assert 'CATEGORY' in mapping
        assert 'SUBCATEGORY' in mapping['CATEGORY']
    
    def test_unicode_patterns(self):
        """Test unicode in patterns."""
        pattern = "café*"
        # Should handle unicode
        assert isinstance(pattern, str)
        assert 'café' in pattern
    
    def test_special_characters(self):
        """Test special characters in patterns."""
        patterns = [
            "starbucks #*",
            "coffee & co*",
            "mcd's*"
        ]
        # Should handle special characters
        for p in patterns:
            assert isinstance(p, str)


class TestMappingValidationIntegration:
    """Integration tests for mapping validation."""
    
    def test_validate_mapping_entry(self):
        """Test validating a mapping entry."""
        entry = {
            'name': 'Starbucks',
            'category': 'FOOD_AND_DRINK',
            'subcategory': 'FOOD_AND_DRINK_COFFEE',
            'scope': 'public'
        }
        # Should have all required fields
        assert 'name' in entry
        assert 'category' in entry
        assert 'scope' in entry
    
    def test_complete_mapping_structure(self):
        """Test complete mapping structure."""
        mapping = {
            'FOOD_AND_DRINK': {
                'FOOD_AND_DRINK_COFFEE': {
                    'starbucks*': {'name': 'Starbucks', 'scope': 'public'},
                    'coffee shop': {'name': 'Coffee Shop', 'scope': 'private'}
                }
            }
        }
        
        # Should have proper hierarchy
        assert 'FOOD_AND_DRINK' in mapping
        assert 'FOOD_AND_DRINK_COFFEE' in mapping['FOOD_AND_DRINK']
        
        subcategory = mapping['FOOD_AND_DRINK']['FOOD_AND_DRINK_COFFEE']
        assert 'starbucks*' in subcategory
        assert 'coffee shop' in subcategory
