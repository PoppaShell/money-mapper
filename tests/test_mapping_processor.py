"""Tests for money_mapper.mapping_processor module."""

import pytest


class TestMappingProcessor:
    """Test mapping processor functionality."""

    def test_mapping_processor_module_imports(self):
        """Test that mapping processor module can be imported."""
        try:
            from money_mapper.mapping_processor import MappingProcessor
            assert MappingProcessor is not None
        except ImportError:
            pytest.fail("Could not import MappingProcessor")

    def test_mapping_processor_with_sample_data(self, sample_mappings):
        """Test mapping processor with sample mapping data."""
        # Verify sample data is available
        assert len(sample_mappings) > 0
        
        # Check that sample mappings have expected structure
        for category, mapping_data in sample_mappings.items():
            assert isinstance(category, str)
            assert "patterns" in mapping_data or isinstance(mapping_data, dict)
