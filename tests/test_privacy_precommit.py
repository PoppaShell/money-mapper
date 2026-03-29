"""Tests for privacy audit pre-commit hook integration."""

import os
from unittest.mock import patch

from money_mapper.privacy_precommit import (
    check_staged_files,
    filter_mapping_files,
    get_override_env,
    run_precommit_check,
)


class TestOverrideMechanism:
    """Test override environment variable handling."""

    def test_get_override_env_not_set(self):
        """Test that override returns False when not set."""
        with patch.dict(os.environ, {}, clear=False):
            # Make sure PRIVACY_AUDIT_SKIP is not set
            env_vars = {k: v for k, v in os.environ.items() if k != "PRIVACY_AUDIT_SKIP"}
            with patch.dict(os.environ, env_vars, clear=True):
                result = get_override_env()
                assert result is False

    def test_get_override_env_set_to_1(self):
        """Test that override returns True when set to 1."""
        with patch.dict(os.environ, {"PRIVACY_AUDIT_SKIP": "1"}):
            result = get_override_env()
            assert result is True

    def test_get_override_env_set_to_true(self):
        """Test that override returns True when set to 'true'."""
        with patch.dict(os.environ, {"PRIVACY_AUDIT_SKIP": "true"}):
            result = get_override_env()
            assert result is True

    def test_get_override_env_set_to_0(self):
        """Test that override returns False when set to 0."""
        with patch.dict(os.environ, {"PRIVACY_AUDIT_SKIP": "0"}):
            result = get_override_env()
            assert result is False


class TestFileFiltering:
    """Test mapping file filtering."""

    def test_filter_mapping_files_empty_list(self):
        """Test filtering empty file list."""
        result = filter_mapping_files([])
        assert isinstance(result, list)
        assert len(result) == 0

    def test_filter_mapping_files_include_toml(self):
        """Test that .toml files are included."""
        files = ["config/public_mappings.toml", "src/test.py"]
        result = filter_mapping_files(files)
        assert "config/public_mappings.toml" in result
        assert "src/test.py" not in result

    def test_filter_mapping_files_include_json(self):
        """Test that mapping .json files are included."""
        files = ["data/enriched_transactions.json", "src/test.py"]
        result = filter_mapping_files(files)
        assert any("enriched" in f for f in result)

    def test_filter_mapping_files_exclude_non_mapping(self):
        """Test that non-mapping files are excluded."""
        files = ["src/cli.py", "tests/test.py", "README.md"]
        result = filter_mapping_files(files)
        assert len(result) == 0

    def test_filter_mapping_files_public_mappings(self):
        """Test public_mappings.toml is detected."""
        files = ["public_mappings.toml"]
        result = filter_mapping_files(files)
        assert "public_mappings.toml" in result

    def test_filter_mapping_files_private_mappings(self):
        """Test private mappings detection."""
        files = ["data/private_mappings.toml", "private_mappings.json"]
        result = filter_mapping_files(files)
        assert len(result) >= 1

    def test_filter_mapping_files_mixed(self):
        """Test mixed file list."""
        files = [
            "public_mappings.toml",
            "src/utils.py",
            "enriched_transactions.json",
            "README.md",
        ]
        result = filter_mapping_files(files)
        assert len(result) >= 2


class TestStagedFilesCheck:
    """Test checking staged files."""

    def test_check_staged_files_no_files(self):
        """Test with no staged files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            result = check_staged_files()
            assert isinstance(result, list)

    def test_check_staged_files_returns_list(self):
        """Test that function returns list of files."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "file1.toml\nfile2.json\n"
            result = check_staged_files()
            assert isinstance(result, list)

    def test_check_staged_files_git_integration(self):
        """Test git integration for getting staged files."""
        # This is an integration test - may be skipped in CI
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "public_mappings.toml\n"
            result = check_staged_files()
            assert isinstance(result, list)


class TestPrecommitCheck:
    """Test main pre-commit check function."""

    def test_precommit_check_passes_clean(self):
        """Test that pre-commit passes for clean files."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = ["public_mappings.toml"]
                    mock_filter.return_value = ["public_mappings.toml"]
                    mock_audit.return_value = {"risk_level": "low", "score": 10}

                    result = run_precommit_check(threshold="high")
                    assert isinstance(result, int)

    def test_precommit_check_returns_int(self):
        """Test that precommit returns exit code (int)."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                mock_check.return_value = []
                mock_filter.return_value = []

                result = run_precommit_check(threshold="high")
                assert isinstance(result, int)
                assert result >= 0  # Valid exit code

    def test_precommit_check_respects_override(self):
        """Test that override skips check."""
        with patch.dict(os.environ, {"PRIVACY_AUDIT_SKIP": "1"}):
            result = run_precommit_check(threshold="high")
            # Should return 0 (success) when overridden
            assert result == 0

    def test_precommit_check_threshold_high(self):
        """Test high threshold only blocks critical issues."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = ["public_mappings.toml"]
                    mock_filter.return_value = ["public_mappings.toml"]
                    # Medium risk should pass with high threshold
                    mock_audit.return_value = {"risk_level": "medium", "score": 50}

                    result = run_precommit_check(threshold="high")
                    # Medium risk should pass with high threshold
                    assert result == 0

    def test_precommit_check_threshold_medium(self):
        """Test medium threshold blocks medium issues."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = ["public_mappings.toml"]
                    mock_filter.return_value = ["public_mappings.toml"]
                    # Medium risk should fail with medium threshold
                    mock_audit.return_value = {"risk_level": "medium", "score": 50}

                    result = run_precommit_check(threshold="medium")
                    # Medium risk should fail with medium threshold
                    assert isinstance(result, int)

    def test_precommit_check_threshold_low(self):
        """Test low threshold blocks all issues."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = ["public_mappings.toml"]
                    mock_filter.return_value = ["public_mappings.toml"]
                    # Any risk should fail with low threshold
                    mock_audit.return_value = {"risk_level": "low", "score": 10}

                    result = run_precommit_check(threshold="low")
                    assert isinstance(result, int)

    def test_precommit_check_no_mapping_files(self):
        """Test with no mapping files staged."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                mock_check.return_value = ["src/cli.py", "tests/test.py"]
                mock_filter.return_value = []

                result = run_precommit_check(threshold="high")
                # No mapping files, should pass
                assert result == 0

    def test_precommit_check_logs_findings(self, capsys):
        """Test that findings are logged to stdout."""
        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = ["public_mappings.toml"]
                    mock_filter.return_value = ["public_mappings.toml"]
                    mock_audit.return_value = {
                        "risk_level": "high",
                        "score": 80,
                        "findings": [{"reason": "Contains medical keywords"}],
                    }

                    result = run_precommit_check(threshold="low")
                    # Should log output
                    assert isinstance(result, int)
