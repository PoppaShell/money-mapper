"""Tests for money_mapper.cli module."""

import pytest


class TestCLI:
    """Test CLI module functionality."""

    def test_cli_module_imports(self):
        """Test that CLI module can be imported."""
        try:
            from money_mapper.cli import main
            assert main is not None
            assert callable(main)
        except ImportError:
            pytest.fail("Could not import main from cli module")

    def test_cli_entry_point_exists(self):
        """Test that CLI entry point is accessible."""
        try:
            from money_mapper import main
            assert main is not None
            assert callable(main)
        except ImportError:
            pytest.fail("Could not import main from money_mapper package")
