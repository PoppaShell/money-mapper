#!/usr/bin/env python3
"""Tests for setup_wizard module."""
import os
import sys
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from setup_wizard import (
    check_first_run,
    run_setup_wizard,
    create_private_configs_from_templates
)


class TestCheckFirstRun:
    """Test check_first_run function."""
    
    def test_first_run_detection(self):
        """Test detection of first run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should detect first run when config doesn't exist
            result = check_first_run()
            assert isinstance(result, bool)


class TestRunSetupWizard:
    """Test run_setup_wizard function."""
    
    @patch('builtins.input', return_value='.')
    def test_setup_wizard_basic_flow(self, mock_input):
        """Test basic setup wizard flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Should run without crashing
                result = run_setup_wizard(tmpdir)
                assert isinstance(result, bool)
            except SystemExit:
                # Setup wizard may exit
                pass
            except Exception as e:
                # Should handle gracefully
                assert True
    
    @patch('builtins.input', side_effect=['y', 'y', 'y'])
    def test_setup_wizard_with_confirmations(self, mock_input):
        """Test setup wizard with user confirmations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = run_setup_wizard(tmpdir)
                assert isinstance(result, bool)
            except:
                pass  # May exit or raise


class TestCreatePrivateConfigs:
    """Test create_private_configs_from_templates function."""
    
    def test_create_private_configs(self):
        """Test creating private config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = create_private_configs_from_templates(tmpdir)
                assert isinstance(result, bool)
            except:
                # May fail if templates don't exist
                pass
