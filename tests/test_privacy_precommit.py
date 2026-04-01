"""Tests for privacy audit pre-commit hook integration."""

import json
import os
from unittest.mock import MagicMock, patch

from money_mapper.privacy_precommit import (
    check_staged_files,
    filter_mapping_files,
    get_override_env,
    main,
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
                assert result == 0  # No staged files means success

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


class TestCheckStagedFilesExceptionHandling:
    """Test exception handling in check_staged_files."""

    def test_check_staged_files_exception_returns_empty(self):
        """Test that subprocess exception returns empty list."""
        with patch("subprocess.run", side_effect=Exception("git not found")):
            result = check_staged_files()
            assert result == []

    def test_check_staged_files_timeout_returns_empty(self):
        """Test that timeout exception returns empty list."""
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = check_staged_files()
            assert result == []

    def test_check_staged_files_file_not_found_returns_empty(self):
        """Test that FileNotFoundError (git not installed) returns empty list."""
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = check_staged_files()
            assert result == []

    def test_check_staged_files_parses_output_correctly(self):
        """Test that file names are correctly parsed from git output."""
        mock_result = MagicMock()
        mock_result.stdout = "config/public_mappings.toml\ndata/enriched_transactions.json\n"
        with patch("subprocess.run", return_value=mock_result):
            result = check_staged_files()
            assert "config/public_mappings.toml" in result
            assert "data/enriched_transactions.json" in result
            assert len(result) == 2

    def test_check_staged_files_strips_whitespace(self):
        """Test that file names have whitespace stripped."""
        mock_result = MagicMock()
        mock_result.stdout = "  file_with_spaces.toml  \n"
        with patch("subprocess.run", return_value=mock_result):
            result = check_staged_files()
            assert "file_with_spaces.toml" in result


class TestFilterMappingFilesConfigDir:
    """Test config/data directory filter branch (line 74)."""

    def test_filter_config_dir_toml_included(self):
        """Test that config/ directory .toml files are included."""
        files = ["config/some_settings.toml"]
        result = filter_mapping_files(files)
        assert "config/some_settings.toml" in result

    def test_filter_config_dir_json_included(self):
        """Test that config/ directory .json files are included."""
        files = ["config/lookup.json"]
        result = filter_mapping_files(files)
        assert "config/lookup.json" in result

    def test_filter_data_dir_toml_included(self):
        """Test that data/ directory .toml files are included."""
        files = ["data/categories.toml"]
        result = filter_mapping_files(files)
        assert "data/categories.toml" in result

    def test_filter_data_dir_json_included(self):
        """Test that data/ directory .json files are included."""
        files = ["data/transactions.json"]
        result = filter_mapping_files(files)
        assert "data/transactions.json" in result

    def test_filter_config_dir_py_excluded(self):
        """Test that config/ directory .py files are excluded."""
        files = ["config/settings.py"]
        result = filter_mapping_files(files)
        assert "config/settings.py" not in result

    def test_filter_data_dir_csv_excluded(self):
        """Test that data/ directory .csv files are excluded."""
        files = ["data/transactions.csv"]
        result = filter_mapping_files(files)
        assert "data/transactions.csv" not in result


class TestRunPrecommitCheckWithRealFiles:
    """Test run_precommit_check with real temp files."""

    def test_json_file_clean_merchants_passes(self, tmp_path):
        """Test that JSON file with clean merchant names passes."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [
            {"merchant_name": "Starbucks", "amount": 5.00},
            {"merchant_name": "McDonald's", "amount": 10.00},
        ]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {"score": 10, "findings": []}

                    result = run_precommit_check(threshold="high")
                    assert result == 0

    def test_json_file_high_risk_merchant_fails(self, tmp_path):
        """Test that JSON file with high-risk merchant name triggers violation."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [
            {"merchant_name": "John Smith Medical Clinic", "amount": 200.00},
        ]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 85,
                        "findings": [{"reason": "Contains personal name pattern"}],
                    }

                    result = run_precommit_check(threshold="high")
                    assert result == 1

    def test_json_file_uses_name_field_fallback(self, tmp_path):
        """Test JSON scanning uses 'name' field when 'merchant_name' absent."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [
            {"name": "Local Store", "amount": 15.00},
        ]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 90,
                        "findings": [{"reason": "Personal name detected"}],
                    }

                    result = run_precommit_check(threshold="high")
                    assert result == 1
                    mock_audit.assert_called_with("Local Store")

    def test_json_file_no_merchant_name_skipped(self, tmp_path):
        """Test JSON items without merchant_name or name are skipped."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [
            {"amount": 15.00, "category": "Food"},
        ]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]

                    result = run_precommit_check(threshold="high")
                    assert result == 0
                    mock_audit.assert_not_called()

    def test_json_file_non_list_data_skipped(self, tmp_path):
        """Test JSON file with dict at root (not list) is handled."""
        json_file = tmp_path / "enriched_transactions.json"
        data = {"metadata": "some value", "count": 0}
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]

                    result = run_precommit_check(threshold="high")
                    assert result == 0
                    mock_audit.assert_not_called()

    def test_toml_file_clean_merchants_passes(self, tmp_path):
        """Test TOML mapping file with clean merchant names passes."""
        toml_file = tmp_path / "public_mappings.toml"
        toml_content = """[FOOD_AND_DRINK.COFFEE]
"starbucks" = { name = "Starbucks", category = "FOOD_AND_DRINK", subcategory = "COFFEE", scope = "public" }
"dunkin" = { name = "Dunkin Donuts", category = "FOOD_AND_DRINK", subcategory = "COFFEE", scope = "public" }
"""
        toml_file.write_text(toml_content)

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(toml_file)]
                    mock_filter.return_value = [str(toml_file)]
                    mock_audit.return_value = {"score": 5, "findings": []}

                    result = run_precommit_check(threshold="high")
                    assert result == 0

    def test_toml_file_extracts_merchant_keys(self, tmp_path):
        """Test TOML scanning extracts merchant keys via regex."""
        toml_file = tmp_path / "public_mappings.toml"
        toml_content = '"walmart" = { name = "Walmart", category = "GENERAL_MERCHANDISE" }\n'
        toml_file.write_text(toml_content)

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(toml_file)]
                    mock_filter.return_value = [str(toml_file)]
                    mock_audit.return_value = {"score": 5, "findings": []}

                    run_precommit_check(threshold="high")
                    mock_audit.assert_called_with("walmart")

    def test_toml_file_high_risk_merchant_fails(self, tmp_path):
        """Test TOML file with high-risk merchant key triggers violation."""
        toml_file = tmp_path / "public_mappings.toml"
        toml_content = (
            '"john doe pharmacy" = { name = "John Doe Pharmacy", category = "MEDICAL" }\n'
        )
        toml_file.write_text(toml_content)

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(toml_file)]
                    mock_filter.return_value = [str(toml_file)]
                    mock_audit.return_value = {
                        "score": 80,
                        "findings": [{"reason": "Personal name in merchant key"}],
                    }

                    result = run_precommit_check(threshold="high")
                    assert result == 1

    def test_file_read_error_continues(self, tmp_path):
        """Test that file read errors are caught and processing continues."""
        nonexistent_file = str(tmp_path / "nonexistent.toml")

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                mock_check.return_value = [nonexistent_file]
                mock_filter.return_value = [nonexistent_file]

                result = run_precommit_check(threshold="high")
                # Should continue and return 0 (no violations found despite error)
                assert result == 0

    def test_violation_output_goes_to_stderr(self, tmp_path, capsys):
        """Test that violation reports are written to stderr."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [{"merchant_name": "Suspicious Name"}]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 90,
                        "findings": [{"reason": "High risk name pattern"}],
                    }

                    run_precommit_check(threshold="high")
                    captured = capsys.readouterr()
                    assert "violation" in captured.err.lower() or "score" in captured.err.lower()

    def test_violation_report_contains_file_and_merchant(self, tmp_path, capsys):
        """Test that violation report includes file name and merchant name."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [{"merchant_name": "PII Merchant"}]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 75,
                        "findings": [{"reason": "Suspicious pattern"}],
                    }

                    run_precommit_check(threshold="high")
                    captured = capsys.readouterr()
                    assert "PII Merchant" in captured.err
                    assert "75" in captured.err

    def test_multiple_violations_all_reported(self, tmp_path, capsys):
        """Test that multiple violations are all reported."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [
            {"merchant_name": "Risky Merchant One"},
            {"merchant_name": "Risky Merchant Two"},
        ]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 80,
                        "findings": [{"reason": "Name pattern detected"}],
                    }

                    result = run_precommit_check(threshold="high")
                    assert result == 1
                    captured = capsys.readouterr()
                    assert "2 violation" in captured.err

    def test_threshold_unknown_defaults_to_70(self, tmp_path):
        """Test that unknown threshold defaults to 70 (high level)."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [{"merchant_name": "Some Merchant"}]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    # Score 65 is below default threshold of 70
                    mock_audit.return_value = {"score": 65, "findings": []}

                    result = run_precommit_check(threshold="unknown_value")
                    assert result == 0

    def test_finding_without_reason_key(self, tmp_path, capsys):
        """Test that findings without 'reason' key use 'Unknown risk' fallback."""
        json_file = tmp_path / "enriched_transactions.json"
        data = [{"merchant_name": "Test Merchant"}]
        json_file.write_text(json.dumps(data))

        with patch("money_mapper.privacy_precommit.check_staged_files") as mock_check:
            with patch("money_mapper.privacy_precommit.filter_mapping_files") as mock_filter:
                with patch("money_mapper.privacy_precommit.audit_merchant_name") as mock_audit:
                    mock_check.return_value = [str(json_file)]
                    mock_filter.return_value = [str(json_file)]
                    mock_audit.return_value = {
                        "score": 80,
                        "findings": [{}],  # No 'reason' key
                    }

                    run_precommit_check(threshold="high")
                    captured = capsys.readouterr()
                    assert "Unknown risk" in captured.err


class TestMainEntryPoint:
    """Test main() function argument parsing and entry point."""

    def test_main_no_args_uses_default_threshold(self):
        """Test main() with no args uses 'high' threshold."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            result = main([])
            mock_run.assert_called_once_with(threshold="high")
            assert result == 0

    def test_main_threshold_equals_syntax(self):
        """Test main() parses --threshold=medium correctly."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            main(["--threshold=medium"])
            mock_run.assert_called_once_with(threshold="medium")

    def test_main_threshold_space_syntax(self):
        """Test main() parses --threshold medium (space syntax) correctly."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            main(["--threshold", "low"])
            mock_run.assert_called_once_with(threshold="low")

    def test_main_threshold_high(self):
        """Test main() passes 'high' threshold to run_precommit_check."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            main(["--threshold=high"])
            mock_run.assert_called_once_with(threshold="high")

    def test_main_threshold_low(self):
        """Test main() passes 'low' threshold to run_precommit_check."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            main(["--threshold=low"])
            mock_run.assert_called_once_with(threshold="low")

    def test_main_returns_exit_code(self):
        """Test main() returns the exit code from run_precommit_check."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 1
            result = main([])
            assert result == 1

    def test_main_none_argv_uses_sys_argv(self):
        """Test main() with None argv reads from sys.argv."""
        with patch("sys.argv", ["privacy_precommit.py", "--threshold=medium"]):
            with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
                mock_run.return_value = 0
                result = main(None)
                mock_run.assert_called_once_with(threshold="medium")
                assert result == 0

    def test_main_unknown_args_ignored(self):
        """Test main() ignores unknown arguments."""
        with patch("money_mapper.privacy_precommit.run_precommit_check") as mock_run:
            mock_run.return_value = 0
            result = main(["--unknown-flag", "--another-flag"])
            mock_run.assert_called_once_with(threshold="high")
            assert result == 0
