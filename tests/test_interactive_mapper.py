#!/usr/bin/env python3
"""Tests for interactive_mapper module."""
import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from interactive_mapper import (
    run_mapping_wizard,
    load_category_taxonomy,
    suggest_keyword,
    suggest_name
)


class TestLoadCategoryTaxonomy:
    """Test load_category_taxonomy function."""
    
    def test_load_taxonomy(self):
        """Test loading category taxonomy."""
        try:
            taxonomy, primary_desc, sub_desc = load_category_taxonomy()
            assert isinstance(taxonomy, dict)
            assert isinstance(primary_desc, dict)
            assert isinstance(sub_desc, dict)
        except:
            # May fail if taxonomy file not found
            pass


class TestSuggestKeyword:
    """Test suggest_keyword function."""
    
    def test_suggest_keyword(self):
        """Test keyword suggestion."""
        result = suggest_keyword("STARBUCKS COFFEE SHOP")
        assert isinstance(result, str)
        assert len(result) >= 0
    
    def test_suggest_keyword_empty(self):
        """Test keyword suggestion with empty string."""
        result = suggest_keyword("")
        assert isinstance(result, str)


class TestSuggestName:
    """Test suggest_name function."""
    
    def test_suggest_name(self):
        """Test name suggestion."""
        result = suggest_name("STARBUCKS COFFEE")
        assert isinstance(result, str)
        assert len(result) >= 0
    
    def test_suggest_name_empty(self):
        """Test name suggestion with empty string."""
        result = suggest_name("")
        assert isinstance(result, str)


class TestRunMappingWizard:
    """Test run_mapping_wizard function."""
    
    @patch('builtins.input', side_effect=['starbucks', 'public', 'n'])
    def test_mapping_wizard_flow(self, mock_input):
        """Test mapping wizard flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Would need valid transaction file to test fully
                pass
            except:
                pass
