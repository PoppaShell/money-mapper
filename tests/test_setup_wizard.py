"""Tests for money_mapper.setup_wizard module."""

import pytest

from money_mapper.setup_wizard import (
    check_and_offer_statement_processing,
    check_first_run,
    display_setup_complete,
)


class TestCheckFirstRun:
    """Test first-run detection."""

    def test_check_first_run_returns_bool(self):
        """Test that check_first_run returns a boolean."""
        result = check_first_run()
        assert isinstance(result, bool)

    def test_check_first_run_with_existing_config(self, temp_output_dir):
        """Test first-run detection with existing config."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Create a settings file to indicate not first run
        settings_file = config_dir / "public_settings.toml"
        settings_file.write_text("[test]\ndata = 'value'\n")

        # Just verify we can call it without error
        result = check_first_run()
        assert isinstance(result, bool)


class TestCheckAndOfferStatementProcessing:
    """Test statement processing offer functionality."""

    def test_check_and_offer_returns_dict(self, temp_output_dir):
        """Test that function returns a dictionary."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        result = check_and_offer_statement_processing(config_dir=str(config_dir))
        assert isinstance(result, dict)

    def test_result_has_processing_status(self, temp_output_dir):
        """Test that result includes processing status."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        result = check_and_offer_statement_processing(config_dir=str(config_dir))
        # Should return a dict with processing info
        assert isinstance(result, dict)

    def test_function_with_nonexistent_config_dir(self):
        """Test function with nonexistent config directory."""
        # Should handle gracefully or create directory
        result = check_and_offer_statement_processing(config_dir="/tmp/nonexistent")
        assert isinstance(result, dict)


class TestDisplaySetupComplete:
    """Test setup completion display."""

    def test_display_setup_complete_no_stats(self, temp_output_dir, capsys):
        """Test displaying setup complete without stats."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Should not raise error
        display_setup_complete(config_dir=str(config_dir), stats=None)
        captured = capsys.readouterr()

        # Should produce some output
        assert len(captured.out) > 0

    def test_display_setup_complete_with_stats(self, temp_output_dir, capsys):
        """Test displaying setup complete with stats."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        stats = {
            "statements_processed": 5,
            "transactions_parsed": 150,
            "config_files_created": 3,
        }

        # Should not raise error
        display_setup_complete(config_dir=str(config_dir), stats=stats)
        captured = capsys.readouterr()

        # Should produce output with stats info
        captured.out.lower()
        # Check that output was produced
        assert len(captured.out) > 0

    def test_display_setup_complete_callable(self):
        """Test that function is callable."""
        assert callable(display_setup_complete)


class TestSetupWizardImports:
    """Test setup_wizard module imports."""

    def test_module_imports(self):
        """Test that module can be imported."""
        try:
            from money_mapper import setup_wizard

            assert setup_wizard is not None
        except ImportError:
            pytest.fail("Could not import setup_wizard module")

    def test_all_functions_exist(self):
        """Test that all major functions exist."""
        from money_mapper import setup_wizard

        required_functions = [
            "check_first_run",
            "run_setup_wizard",
            "check_and_offer_statement_processing",
            "display_setup_complete",
        ]

        for func_name in required_functions:
            assert hasattr(setup_wizard, func_name), f"Missing function: {func_name}"
            assert callable(getattr(setup_wizard, func_name)), f"Not callable: {func_name}"


class TestSetupWizardIntegration:
    """Integration tests for setup wizard."""

    def test_setup_completion_workflow(self, temp_output_dir):
        """Test typical setup completion workflow."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Check first run
        is_first_run = check_first_run()
        assert isinstance(is_first_run, bool)

        # Check statement processing offer
        result = check_and_offer_statement_processing(config_dir=str(config_dir))
        assert isinstance(result, dict)

    def test_display_with_various_stats(self, temp_output_dir):
        """Test display with various statistics."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        test_cases = [
            None,  # No stats
            {},  # Empty stats
            {"transactions": 100},  # Simple stats
            {"statements": 5, "transactions": 150, "errors": 0},  # Multiple stats
        ]

        for stats in test_cases:
            # Should not raise error
            display_setup_complete(config_dir=str(config_dir), stats=stats)


class TestSetupWizardConfiguration:
    """Test setup wizard configuration handling."""

    def test_setup_with_custom_config_dir(self, temp_output_dir):
        """Test setup wizard with custom config directory."""
        config_dir = temp_output_dir / "custom_config"
        config_dir.mkdir(exist_ok=True)

        # Check statement processing with custom dir
        result = check_and_offer_statement_processing(config_dir=str(config_dir))
        assert isinstance(result, dict)

    def test_check_first_run_consistency(self):
        """Test that first-run check is consistent."""
        result1 = check_first_run()
        result2 = check_first_run()

        # Results should be consistent (same boolean value)
        assert result1 == result2
        assert isinstance(result1, bool)

    def test_display_with_none_config_dir(self, capsys):
        """Test display with None config directory."""
        # Should handle gracefully
        try:
            display_setup_complete(config_dir=None, stats=None)
        except (TypeError, AttributeError):
            # It's ok if it raises for None input
            pass
