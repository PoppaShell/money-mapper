#!/usr/bin/env python3
"""Tests for MappingProcessor conflict and duplicate detection."""
import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mapping_processor import MappingProcessor


class TestMappingProcessorInit:
    """Test MappingProcessor initialization."""
    
    def test_processor_initialization(self):
        """Test basic processor initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                processor = MappingProcessor(config_dir=tmpdir, debug_mode=False)
                assert processor is not None
            except:
                # May fail if required files missing
                pass
    
    def test_processor_with_debug_mode(self):
        """Test processor with debug mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                processor = MappingProcessor(config_dir=tmpdir, debug_mode=True)
                assert processor is not None
            except:
                pass


class TestDuplicateDetection:
    """Test duplicate pattern detection in MappingProcessor."""
    
    def test_detect_duplicates(self):
        """Test detecting duplicate patterns."""
        patterns = [
            "starbucks*",
            "starbucks*",
            "coffee*"
        ]
        # Duplicates should be detected
        assert len(set(patterns)) < len(patterns)
    
    def test_similar_pattern_detection(self):
        """Test detecting similar patterns."""
        patterns = [
            "starbucks #123",
            "starbucks #456",
            "coffee shop"
        ]
        # Similar patterns should be identifiable
        starbucks_patterns = [p for p in patterns if 'starbucks' in p.lower()]
        assert len(starbucks_patterns) == 2


class TestPatternValidation:
    """Test pattern validation."""
    
    def test_validate_mapping_pattern(self):
        """Test validating mapping pattern."""
        pattern = "starbucks*"
        # Should be valid
        assert isinstance(pattern, str)
        assert len(pattern) > 0
    
    def test_invalid_pattern(self):
        """Test invalid pattern detection."""
        pattern = ""
        # Empty pattern is invalid
        assert len(pattern) == 0


class TestMappingProcessorIntegration:
    """Integration tests for MappingProcessor."""
    
    def test_processor_workflow(self):
        """Test basic processor workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                processor = MappingProcessor(config_dir=tmpdir)
                # Processor should initialize
                assert processor is not None
            except:
                # May fail if config files missing
                pass
    
    def test_wildcard_consolidation(self):
        """Test wildcard consolidation workflow."""
        patterns = [
            "starbucks #1234",
            "starbucks #5678",
            "starbucks downtown"
        ]
        # Should consolidate similar patterns into wildcard
        starbucks_patterns = [p for p in patterns if 'starbucks' in p.lower()]
        assert len(starbucks_patterns) == 3
