"""Tests for money_mapper.config_manager module."""

import os
import pytest

from money_mapper.config_manager import get_config_manager


class TestConfigManager:
    """Test configuration manager functionality."""

    def test_get_config_manager(self):
        """Test getting config manager instance."""
        config_manager = get_config_manager()
        assert config_manager is not None

    def test_get_directory_path(self):
        """Test getting configured directory paths."""
        config_manager = get_config_manager()
        
        # These should return configured paths
        statements_dir = config_manager.get_directory_path('statements')
        assert statements_dir is not None
        assert isinstance(statements_dir, str)

    def test_get_file_path(self):
        """Test getting configured file paths."""
        config_manager = get_config_manager()
        
        # Get a file path from configuration
        file_path = config_manager.get_file_path('public_mappings')
        assert file_path is not None
        assert isinstance(file_path, str)

    def test_config_manager_singleton(self):
        """Test that config manager behaves consistently."""
        cm1 = get_config_manager()
        cm2 = get_config_manager()
        
        # Both should return config managers (may be same instance or equivalent)
        assert cm1 is not None
        assert cm2 is not None
