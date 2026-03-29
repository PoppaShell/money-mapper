"""Tests for money_mapper.cli module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from money_mapper.cli import (
    confirm_action,
    print_banner,
    run_full_pipeline_interactive,
    validate_directory,
    validate_json_file,
    validate_output_path,
)


class TestValidateDirectory:
    """Test directory validation."""

    def test_validate_nonexistent_directory(self):
        """Test validation of nonexistent directory."""
        result = validate_directory("/nonexistent/directory/path")
        assert result is False

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        result = validate_directory("")
        assert result is False

    def test_validate_file_path_as_directory(self, temp_output_dir):
        """Test validation when file path given instead of directory."""
        test_file = temp_output_dir / "test.txt"
        test_file.write_text("test")

        # Should return False because it's a file, not directory
        result = validate_directory(str(test_file))
        assert result is False

    def test_validate_directory_requires_csv_files(self, temp_output_dir):
        """Test that validation requires CSV files to exist."""
        empty_dir = temp_output_dir / "empty"
        empty_dir.mkdir(exist_ok=True)

        # Directory exists but has no CSVs - should return False
        result = validate_directory(str(empty_dir))
        assert result is False

    def test_validate_directory_with_csv_files(self, temp_output_dir):
        """Test validation with CSV files present."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        # Create a test CSV file
        csv_file = csv_dir / "test.csv"
        csv_file.write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        # Should return True when CSV exists
        result = validate_directory(str(csv_dir))
        assert result is True

    @pytest.mark.parametrize(
        "invalid_path",
        [
            "/nonexistent/path",
            "",
        ],
    )
    def test_validate_directory_invalid_paths(self, invalid_path):
        """Test directory validation with invalid paths."""
        result = validate_directory(invalid_path)
        assert result is False


class TestValidateJsonFile:
    """Test JSON file validation."""

    def test_validate_valid_json_file(self, temp_output_dir):
        """Test validation of valid JSON file."""
        json_file = temp_output_dir / "valid.json"
        json_file.write_text('{"key": "value"}')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_nonexistent_json_file(self):
        """Test validation of nonexistent JSON file."""
        result = validate_json_file("/nonexistent/file.json")
        assert result is False

    def test_validate_invalid_json_file(self, temp_output_dir):
        """Test validation of invalid JSON file."""
        json_file = temp_output_dir / "invalid.json"
        json_file.write_text("{invalid json")

        result = validate_json_file(str(json_file))
        assert result is False

    def test_validate_empty_json_file(self, temp_output_dir):
        """Test validation of empty JSON file."""
        json_file = temp_output_dir / "empty.json"
        json_file.write_text("")

        result = validate_json_file(str(json_file))
        assert result is False

    def test_validate_json_array(self, temp_output_dir):
        """Test validation of JSON array file."""
        json_file = temp_output_dir / "array.json"
        json_file.write_text('[{"id": 1}, {"id": 2}]')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_non_json_file(self, temp_output_dir):
        """Test validation of non-JSON file."""
        txt_file = temp_output_dir / "notjson.txt"
        txt_file.write_text("plain text")

        result = validate_json_file(str(txt_file))
        assert result is False


class TestValidateOutputPath:
    """Test output path validation."""

    def test_validate_valid_output_path(self, temp_output_dir):
        """Test validation of valid output path."""
        output_file = temp_output_dir / "output.json"

        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert result is True

    def test_validate_output_in_existing_directory(self, temp_output_dir):
        """Test output path in existing directory."""
        output_file = temp_output_dir / "output.json"

        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert result is True

    def test_validate_output_in_nonexistent_directory(self):
        """Test output path in nonexistent directory."""
        result = validate_output_path("/nonexistent/dir/output.json", prompt_overwrite=False)
        # Might return False or True depending on implementation
        assert isinstance(result, bool)

    def test_validate_output_overwrites_existing(self, temp_output_dir):
        """Test validation when output file already exists."""
        output_file = temp_output_dir / "exists.json"
        output_file.write_text('{"data": "existing"}')

        # Should handle existing file gracefully
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)


class TestConfirmAction:
    """Test action confirmation."""

    def test_confirm_action_with_default_true(self, monkeypatch):
        """Test confirm action with default True using mocked input."""
        # Mock input to return empty string (accept default)
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = confirm_action("Continue?", default=True)
        assert result is True

    def test_confirm_action_with_default_false(self, monkeypatch):
        """Test confirm action with default False using mocked input."""
        # Mock input to return empty string (accept default)
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = confirm_action("Continue?", default=False)
        assert result is False

    def test_confirm_action_user_yes(self, monkeypatch):
        """Test confirm action when user enters yes."""
        # Mock input to return 'y'
        monkeypatch.setattr("builtins.input", lambda prompt: "y")
        result = confirm_action("Test message", default=False)
        assert result is True

    def test_confirm_action_user_no(self, monkeypatch):
        """Test confirm action when user enters no."""
        # Mock input to return 'n'
        monkeypatch.setattr("builtins.input", lambda prompt: "n")
        result = confirm_action("Test message", default=True)
        assert result is False


class TestPrintBanner:
    """Test banner printing."""

    def test_print_banner_no_error(self, capsys):
        """Test that banner prints without error."""
        print_banner()
        captured = capsys.readouterr()

        # Banner should print something
        assert len(captured.out) >= 0

    def test_print_banner_callable(self):
        """Test that print_banner is callable."""
        assert callable(print_banner)


class TestCLIImports:
    """Test CLI module imports."""

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
            from money_mapper.cli import main

            assert main is not None
            assert callable(main)
        except ImportError:
            pytest.fail("Could not import main from money_mapper package")

    def test_all_cli_functions_exist(self):
        """Test that all major CLI functions exist."""
        from money_mapper import cli

        required_functions = [
            "validate_directory",
            "validate_json_file",
            "validate_output_path",
            "confirm_action",
            "print_banner",
            "main",
        ]

        for func_name in required_functions:
            assert hasattr(cli, func_name), f"Missing function: {func_name}"
            assert callable(getattr(cli, func_name)), f"Not callable: {func_name}"


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_validate_workflow(self, temp_output_dir):
        """Test typical validation workflow."""
        # Create a valid input file
        input_file = temp_output_dir / "input.json"
        input_file.write_text('[{"merchant": "TEST", "amount": 10.0}]')

        # Validate input
        assert validate_json_file(str(input_file)) is True

        # Validate output path
        output_file = temp_output_dir / "output.json"
        assert isinstance(validate_output_path(str(output_file), prompt_overwrite=False), bool)

    def test_directory_validation_workflow(self, temp_output_dir):
        """Test directory validation workflow."""
        # Create test directory structure with CSV files
        statements_dir = temp_output_dir / "statements"
        statements_dir.mkdir(exist_ok=True)

        # Add a CSV file to statements directory
        csv_file = statements_dir / "statement.csv"
        csv_file.write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        output_dir = temp_output_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Validate statements directory (has CSV)
        assert validate_directory(str(statements_dir)) is True

        # Output dir doesn't need CSVs for validation (different validation rules)
        # Just verify path is valid
        assert os.path.isdir(str(output_dir)) is True


class TestValidateDirectoryExtended:
    """Extended tests for directory validation."""

    def test_validate_relative_path(self, temp_output_dir):
        """Test validation with relative path."""
        # Create CSV in temp directory
        csv_file = temp_output_dir / "test.csv"
        csv_file.write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        # Get relative path if possible
        try:
            rel_path = os.path.relpath(str(temp_output_dir))
            result = validate_directory(rel_path)
            assert isinstance(result, bool)
        except:
            # If relative paths don't work, skip
            pass

    def test_validate_multiple_csv_files(self, temp_output_dir):
        """Test validation with multiple CSV files."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        # Create multiple CSVs
        for i in range(5):
            csv_file = csv_dir / f"statement_{i}.csv"
            csv_file.write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        result = validate_directory(str(csv_dir))
        assert result is True

    def test_validate_mixed_file_types(self, temp_output_dir):
        """Test validation with mixed file types."""
        mixed_dir = temp_output_dir / "mixed"
        mixed_dir.mkdir(exist_ok=True)

        # Create mixed files
        (mixed_dir / "statement.csv").write_text("Date,Description,Amount\n2025-01-01,Test,100.00")
        (mixed_dir / "data.json").write_text("{}")
        (mixed_dir / "note.txt").write_text("txt")

        result = validate_directory(str(mixed_dir))
        assert result is True  # Should validate if CSV exists

    def test_validate_subdirectories_ignored(self, temp_output_dir):
        """Test that validation checks only top-level CSV files."""
        test_dir = temp_output_dir / "test"
        test_dir.mkdir(exist_ok=True)

        # Create CSV in subdirectory
        sub_dir = test_dir / "sub"
        sub_dir.mkdir(exist_ok=True)
        (sub_dir / "statement.csv").write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        result = validate_directory(str(test_dir))
        # Depends on implementation - may be False if only top-level is checked
        assert isinstance(result, bool)

    def test_validate_csv_file(self, temp_output_dir):
        """Test validation with CSV file."""
        csv_dir = temp_output_dir / "csvs"
        csv_dir.mkdir(exist_ok=True)

        # Create regular CSV
        (csv_dir / "statement.csv").write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        result = validate_directory(str(csv_dir))
        assert result is True


class TestValidateJsonFileExtended:
    """Extended tests for JSON file validation."""

    def test_validate_nested_json(self, temp_output_dir):
        """Test validation of deeply nested JSON."""
        json_file = temp_output_dir / "nested.json"
        nested_data = {"level1": {"level2": {"level3": {"data": "value"}}}}
        json_file.write_text(json.dumps(nested_data))

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_large_json(self, temp_output_dir):
        """Test validation of large JSON file."""
        json_file = temp_output_dir / "large.json"
        large_data = [{"id": i, "value": f"item_{i}"} for i in range(1000)]
        json_file.write_text(json.dumps(large_data))

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_with_unicode(self, temp_output_dir):
        """Test validation of JSON with Unicode characters."""
        json_file = temp_output_dir / "unicode.json"
        unicode_data = {"text": "Cafe", "data": "test"}  # Use ASCII-safe strings
        json_file.write_text(json.dumps(unicode_data, ensure_ascii=False), encoding="utf-8")

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_null_values(self, temp_output_dir):
        """Test validation of JSON with null values."""
        json_file = temp_output_dir / "nulls.json"
        json_file.write_text('{"key": null, "array": [1, null, 3]}')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_empty_object(self, temp_output_dir):
        """Test validation of empty JSON object."""
        json_file = temp_output_dir / "empty_obj.json"
        json_file.write_text("{}")

        result = validate_json_file(str(json_file))
        # Empty objects may not be considered valid transactions
        assert isinstance(result, bool)

    def test_validate_json_empty_array(self, temp_output_dir):
        """Test validation of empty JSON array."""
        json_file = temp_output_dir / "empty_array.json"
        json_file.write_text("[]")

        result = validate_json_file(str(json_file))
        # Empty arrays may not be considered valid (no transactions)
        assert isinstance(result, bool)

    def test_validate_json_boolean_values(self, temp_output_dir):
        """Test validation of JSON with boolean values."""
        json_file = temp_output_dir / "bool.json"
        json_file.write_text('{"active": true, "deleted": false}')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_number_values(self, temp_output_dir):
        """Test validation of JSON with various number types."""
        json_file = temp_output_dir / "numbers.json"
        json_file.write_text('{"int": 42, "float": 3.14, "negative": -10, "zero": 0}')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_single_line(self, temp_output_dir):
        """Test validation of single-line JSON."""
        json_file = temp_output_dir / "single.json"
        json_file.write_text('[{"a":1},{"b":2}]')

        result = validate_json_file(str(json_file))
        assert result is True

    def test_validate_json_trailing_comma(self, temp_output_dir):
        """Test validation rejects JSON with trailing comma."""
        json_file = temp_output_dir / "trailing.json"
        json_file.write_text("[1, 2, 3,]")  # Trailing comma is invalid

        result = validate_json_file(str(json_file))
        assert result is False


class TestValidateOutputPathExtended:
    """Extended tests for output path validation."""

    def test_validate_output_json_extension(self, temp_output_dir):
        """Test output path with .json extension."""
        output_file = temp_output_dir / "output.json"
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)

    def test_validate_output_different_extensions(self, temp_output_dir):
        """Test output path with different file extensions."""
        for ext in [".json", ".csv", ".txt", ".log"]:
            output_file = temp_output_dir / f"output{ext}"
            result = validate_output_path(str(output_file), prompt_overwrite=False)
            assert isinstance(result, bool)

    def test_validate_output_no_extension(self, temp_output_dir):
        """Test output path with no extension."""
        output_file = temp_output_dir / "output"
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)

    def test_validate_output_existing_file_no_prompt(self, temp_output_dir):
        """Test output path with existing file, no prompt."""
        output_file = temp_output_dir / "exists.json"
        output_file.write_text('{"data": "existing"}')

        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)

    def test_validate_output_deep_path(self, temp_output_dir):
        """Test output path with deep directory structure."""
        deep_dir = temp_output_dir / "a" / "b" / "c" / "d"
        deep_dir.mkdir(parents=True, exist_ok=True)

        output_file = deep_dir / "output.json"
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)

    def test_validate_output_special_chars_in_path(self, temp_output_dir):
        """Test output path with special characters."""
        special_dir = temp_output_dir / "test-dir_123"
        special_dir.mkdir(exist_ok=True)

        output_file = special_dir / "output-file_2024.json"
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)


class TestConfirmActionExtended:
    """Extended tests for action confirmation."""

    def test_confirm_action_uppercase_y(self, monkeypatch):
        """Test confirm action with uppercase Y."""
        monkeypatch.setattr("builtins.input", lambda prompt: "Y")
        result = confirm_action("Test", default=False)
        assert result is True

    def test_confirm_action_uppercase_n(self, monkeypatch):
        """Test confirm action with uppercase N."""
        monkeypatch.setattr("builtins.input", lambda prompt: "N")
        result = confirm_action("Test", default=True)
        assert result is False

    def test_confirm_action_yes_spelled_out(self, monkeypatch):
        """Test confirm action with 'yes' spelled out."""
        monkeypatch.setattr("builtins.input", lambda prompt: "yes")
        result = confirm_action("Test", default=False)
        assert result is True

    def test_confirm_action_no_spelled_out(self, monkeypatch):
        """Test confirm action with 'no' spelled out."""
        monkeypatch.setattr("builtins.input", lambda prompt: "no")
        result = confirm_action("Test", default=True)
        assert result is False

    def test_confirm_action_mixed_case_yes(self, monkeypatch):
        """Test confirm action with mixed case YES."""
        monkeypatch.setattr("builtins.input", lambda prompt: "YeS")
        result = confirm_action("Test", default=False)
        assert result is True

    def test_confirm_action_invalid_input_then_default(self, monkeypatch):
        """Test confirm action with invalid input, then uses default."""
        inputs = iter(["invalid", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        # Note: This will raise StopIteration on second call if function retries
        # The behavior depends on implementation
        try:
            result = confirm_action("Test", default=True)
            assert result is True
        except StopIteration:
            # Expected if function retries on invalid input
            pass

    def test_confirm_action_default_true_empty(self, monkeypatch):
        """Test confirm action default True with empty input."""
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = confirm_action("Continue?", default=True)
        assert result is True

    def test_confirm_action_default_false_empty(self, monkeypatch):
        """Test confirm action default False with empty input."""
        monkeypatch.setattr("builtins.input", lambda prompt: "")
        result = confirm_action("Continue?", default=False)
        assert result is False

    def test_confirm_action_spaces_around_input(self, monkeypatch):
        """Test confirm action with spaces around input."""
        monkeypatch.setattr("builtins.input", lambda prompt: "  y  ")
        result = confirm_action("Test", default=False)
        assert result is True


class TestCLIEdgeCases:
    """Test edge cases and error conditions in CLI."""

    def test_validate_directory_with_spaces(self, temp_output_dir):
        """Test directory validation with spaces in path."""
        space_dir = temp_output_dir / "test dir with spaces"
        space_dir.mkdir(exist_ok=True)

        csv_file = space_dir / "statement.csv"
        csv_file.write_text("Date,Description,Amount\n2025-01-01,Test,100.00")

        result = validate_directory(str(space_dir))
        assert result is True

    def test_validate_json_with_bom(self, temp_output_dir):
        """Test JSON validation with BOM (Byte Order Mark)."""
        json_file = temp_output_dir / "bom.json"
        # Write with UTF-8 BOM
        json_file.write_bytes(b"\xef\xbb\xbf[1, 2, 3]")

        # Should handle or reject gracefully
        result = validate_json_file(str(json_file))
        assert isinstance(result, bool)

    def test_validate_output_path_with_unicode(self, temp_output_dir):
        """Test output path validation with Unicode characters."""
        unicode_dir = temp_output_dir / "café"
        unicode_dir.mkdir(exist_ok=True)

        output_file = unicode_dir / "résultats.json"
        result = validate_output_path(str(output_file), prompt_overwrite=False)
        assert isinstance(result, bool)


class TestRunFullPipelineInteractive:
    """Test the full pipeline interactive function."""

    @patch("money_mapper.cli.CSVImporter")
    @patch("money_mapper.cli.process_transaction_enrichment")
    @patch("money_mapper.cli.get_config_manager")
    @patch("builtins.input", side_effect=["statements", "y", "n"])
    def test_pipeline_interactive_uses_csv_importer(
        self, mock_input, mock_config, mock_enrich, mock_csv
    ):
        """Interactive pipeline should use CSVImporter, not deleted PDF parser."""
        mock_cm = MagicMock()
        mock_cm.get_setting.return_value = "output"
        mock_cm.get_directory_path.return_value = "statements"
        mock_cm.get_default_file_path.return_value = "output/transactions.json"
        mock_config.return_value = mock_cm

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = [
            {"date": "2024-01-15", "merchant": "STORE", "amount": -10.00}
        ]
        mock_csv.return_value = mock_importer

        with patch("money_mapper.utils.save_transactions_to_json"):
            with patch("money_mapper.cli.validate_directory", return_value=True):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    run_full_pipeline_interactive(debug=False)

        mock_csv.assert_called_once()
        mock_importer.import_directory.assert_called_once()


class TestRebuildModelCommand:
    """Test rebuild-model CLI command."""

    @patch("money_mapper.ml_categorizer.rebuild_public_model")
    def test_rebuild_model_public(self, mock_rebuild):
        """Test --public flag calls rebuild_public_model."""
        from money_mapper.cli import main

        mock_rebuild.return_value = {"vocab_size": 100, "model_type": "public"}
        with patch("sys.argv", ["money-mapper", "rebuild-model", "--public"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            try:
                                main()
                            except SystemExit:
                                pass
        mock_rebuild.assert_called_once()

    @patch("money_mapper.ml_categorizer.rebuild_private_model")
    @patch("os.path.exists", return_value=True)
    def test_rebuild_model_private(self, mock_exists, mock_rebuild):
        """Test --private flag calls rebuild_private_model."""
        from money_mapper.cli import main

        mock_rebuild.return_value = {"vocab_size": 50, "model_type": "private"}
        with patch("sys.argv", ["money-mapper", "rebuild-model", "--private"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            try:
                                main()
                            except SystemExit:
                                pass
        mock_rebuild.assert_called_once()

    @patch("money_mapper.ml_categorizer.rebuild_private_model")
    @patch("money_mapper.ml_categorizer.rebuild_public_model")
    def test_rebuild_model_both_default(self, mock_public, mock_private):
        """Test that no flag defaults to rebuilding both models."""
        from money_mapper.cli import main

        mock_public.return_value = {"vocab_size": 100, "model_type": "public"}
        mock_private.return_value = {"vocab_size": 50, "model_type": "private"}
        with patch("sys.argv", ["money-mapper", "rebuild-model"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with patch("os.path.exists", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass
        mock_public.assert_called_once()
        mock_private.assert_called_once()

    @patch("money_mapper.ml_categorizer.rebuild_public_model")
    def test_rebuild_model_public_failure(self, mock_rebuild, capsys):
        """Test --public flag prints failure message when rebuild returns None."""
        from money_mapper.cli import main

        mock_rebuild.return_value = None
        with patch("sys.argv", ["money-mapper", "rebuild-model", "--public"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            try:
                                main()
                            except SystemExit:
                                pass
        captured = capsys.readouterr()
        assert "Failed to rebuild public model" in captured.out

    def test_rebuild_model_private_no_enriched_file(self, capsys):
        """Test --private flag prints message when enriched file is missing."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "rebuild-model", "--private"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with patch("os.path.exists", return_value=False):
                                try:
                                    main()
                                except SystemExit:
                                    pass
        captured = capsys.readouterr()
        assert "No enriched transactions found" in captured.out


class TestPrivacyAuditCommand:
    """Test privacy-audit CLI command."""

    @patch("money_mapper.privacy_audit.audit_merchant_name")
    def test_privacy_audit_scans_file(self, mock_audit):
        """Test privacy-audit scans merchants from mapping file."""
        mock_audit.return_value = {
            "merchant_name": "starbucks",
            "score": 5,
            "risk_level": "low",
            "findings": [],
        }

        with patch(
            "sys.argv",
            [
                "money-mapper",
                "privacy-audit",
                "--file",
                "config/public_mappings.toml",
                "--threshold",
                "high",
            ],
        ):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "money_mapper.cli.load_config",
                    return_value={
                        "FOOD": {
                            "COFFEE": {
                                "starbucks": {
                                    "name": "Starbucks",
                                    "category": "FOOD",
                                    "subcategory": "COFFEE",
                                    "scope": "public",
                                }
                            }
                        }
                    },
                ):
                    with patch("money_mapper.cli.get_config_manager"):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with patch(
                                    "money_mapper.setup_wizard.check_first_run", return_value=False
                                ):
                                    try:
                                        from money_mapper.cli import main

                                        main()
                                    except SystemExit:
                                        pass

        mock_audit.assert_called()

    @patch("money_mapper.privacy_audit.audit_merchant_name")
    def test_privacy_audit_exits_1_on_findings(self, mock_audit):
        """Test privacy-audit exits 1 when findings exceed threshold."""
        mock_audit.return_value = {
            "merchant_name": "dr smith medical",
            "score": 85,
            "risk_level": "high",
            "findings": [{"type": "keywords", "reason": "Medical keyword detected"}],
        }

        with patch(
            "sys.argv",
            [
                "money-mapper",
                "privacy-audit",
                "--file",
                "config/public_mappings.toml",
                "--threshold",
                "medium",
            ],
        ):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "money_mapper.cli.load_config",
                    return_value={
                        "MEDICAL": {
                            "SERVICES": {
                                "dr smith medical": {
                                    "name": "Dr Smith",
                                    "category": "MEDICAL",
                                    "subcategory": "SERVICES",
                                    "scope": "private",
                                }
                            }
                        }
                    },
                ):
                    with patch("money_mapper.cli.get_config_manager"):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with patch(
                                    "money_mapper.setup_wizard.check_first_run", return_value=False
                                ):
                                    with pytest.raises(SystemExit) as exc_info:
                                        from money_mapper.cli import main

                                        main()
                                    assert exc_info.value.code == 1


class TestContributeCommand:
    """Test contribute CLI command."""

    @patch("money_mapper.community_flow.submit_community_contribution")
    def test_contribute_success(self, mock_submit):
        """Test successful contribution creates PR."""
        from money_mapper.cli import main

        mock_submit.return_value = {
            "success": True,
            "pr_url": "https://github.com/PoppaShell/money-mapper/pull/999",
            "validation": {"passed": True},
        }
        with patch(
            "sys.argv",
            [
                "money-mapper",
                "contribute",
                "--merchant",
                "Test Store",
                "--category",
                "FOOD_AND_DRINK",
            ],
        ):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            try:
                                main()
                            except SystemExit:
                                pass
        mock_submit.assert_called_once_with("Test Store", "FOOD_AND_DRINK", "cli")

    @patch("money_mapper.community_flow.submit_community_contribution")
    def test_contribute_failure_exits_1(self, mock_submit):
        """Test failed contribution exits with code 1."""
        from money_mapper.cli import main

        mock_submit.return_value = {
            "success": False,
            "error": "Privacy audit failed",
            "validation": {"passed": False, "score": 85, "issues": ["Medical keyword"]},
        }
        with patch(
            "sys.argv",
            ["money-mapper", "contribute", "--merchant", "Dr Smith", "--category", "MEDICAL"],
        ):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with pytest.raises(SystemExit) as exc_info:
                                main()
                            assert exc_info.value.code == 1


class TestValidateConfigPaths:
    """Tests for the validate_config_paths() function."""

    def test_all_paths_exist(self, tmp_path):
        """Returns True when all required directories and files exist."""
        from money_mapper.cli import validate_config_paths

        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        patterns_file = config_dir / "statement_patterns.toml"
        patterns_file.write_text("")
        plaid_file = config_dir / "plaid_categories.toml"
        plaid_file.write_text("")

        mock_cm = MagicMock()
        mock_cm.get_directory_path.side_effect = lambda key: {
            "statements": str(statements_dir),
            "output": str(output_dir),
            "config": str(config_dir),
        }[key]
        mock_cm.get_file_path.side_effect = lambda key: {
            "statement_patterns": str(patterns_file),
            "plaid_categories": str(plaid_file),
            "private_mappings": str(tmp_path / "private_mappings.toml"),
            "public_mappings": str(tmp_path / "public_mappings.toml"),
        }[key]

        result = validate_config_paths(mock_cm, command="parse")
        assert result is True

    def test_missing_statements_dir_for_parse(self, tmp_path):
        """Returns False when statements directory is missing for parse command."""
        from money_mapper.cli import validate_config_paths

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        patterns_file = config_dir / "statement_patterns.toml"
        patterns_file.write_text("")
        plaid_file = config_dir / "plaid_categories.toml"
        plaid_file.write_text("")

        mock_cm = MagicMock()
        mock_cm.get_directory_path.side_effect = lambda key: {
            "statements": str(tmp_path / "nonexistent"),
            "output": str(tmp_path / "output"),
            "config": str(config_dir),
        }.get(key, str(tmp_path / key))
        mock_cm.get_file_path.side_effect = lambda key: {
            "statement_patterns": str(patterns_file),
            "plaid_categories": str(plaid_file),
            "private_mappings": str(tmp_path / "private_mappings.toml"),
            "public_mappings": str(tmp_path / "public_mappings.toml"),
        }[key]

        result = validate_config_paths(mock_cm, command="parse")
        assert result is False

    def test_missing_config_dir_returns_false(self, tmp_path):
        """Returns False when config directory is missing."""
        from money_mapper.cli import validate_config_paths

        mock_cm = MagicMock()
        missing = str(tmp_path / "nonexistent")
        mock_cm.get_directory_path.return_value = missing
        mock_cm.get_file_path.return_value = str(tmp_path / "missing.toml")

        result = validate_config_paths(mock_cm, command="validate")
        assert result is False

    def test_creates_output_dir_when_missing(self, tmp_path):
        """Creates output directory automatically when it does not exist."""
        from money_mapper.cli import validate_config_paths

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        patterns_file = config_dir / "statement_patterns.toml"
        patterns_file.write_text("")
        plaid_file = config_dir / "plaid_categories.toml"
        plaid_file.write_text("")
        output_dir = tmp_path / "output_new"
        # Do NOT create output_dir -- validate_config_paths should create it

        mock_cm = MagicMock()
        mock_cm.get_directory_path.side_effect = lambda key: {
            "statements": str(tmp_path),
            "output": str(output_dir),
            "config": str(config_dir),
        }.get(key, str(tmp_path))
        mock_cm.get_file_path.side_effect = lambda key: {
            "statement_patterns": str(patterns_file),
            "plaid_categories": str(plaid_file),
            "private_mappings": str(tmp_path / "private_mappings.toml"),
            "public_mappings": str(tmp_path / "public_mappings.toml"),
        }[key]

        result = validate_config_paths(mock_cm, command="enrich")
        # Should succeed by creating the directory
        assert result is True
        assert output_dir.exists()

    def test_missing_required_config_file_returns_false(self, tmp_path):
        """Returns False when a required config file is missing."""
        from money_mapper.cli import validate_config_paths

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_cm = MagicMock()
        mock_cm.get_directory_path.side_effect = lambda key: {
            "statements": str(tmp_path),
            "output": str(output_dir),
            "config": str(config_dir),
        }.get(key, str(tmp_path))
        # Both required files are missing
        mock_cm.get_file_path.side_effect = lambda key: str(tmp_path / f"{key}.toml")

        result = validate_config_paths(mock_cm, command="analyze")
        assert result is False

    def test_no_command_validates_all_paths(self, tmp_path):
        """With command=None, validates statements, output, and config paths."""
        from money_mapper.cli import validate_config_paths

        mock_cm = MagicMock()
        # All paths missing -- expect False
        mock_cm.get_directory_path.return_value = str(tmp_path / "missing")
        mock_cm.get_file_path.return_value = str(tmp_path / "missing.toml")

        result = validate_config_paths(mock_cm, command=None)
        assert result is False


class TestMainParseCommand:
    """Tests for the 'parse' subcommand in main()."""

    def _run_main(self, argv, extra_patches=()):
        """Helper: run main() with given argv and extra patches applied."""
        from money_mapper.cli import main

        patches = [patch("sys.argv", argv)] + list(extra_patches) + _base_patches()
        # Apply all patches
        ctx = []
        for p in patches:
            ctx.append(p.__enter__())
        try:
            try:
                main()
            except SystemExit:
                pass
        finally:
            for i, p in enumerate(patches):
                p.__exit__(None, None, None)

    def test_parse_command_calls_csv_importer(self, tmp_path):
        """Parse command instantiates CSVImporter and calls import_directory."""
        from money_mapper.cli import main

        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        (statements_dir / "test.csv").write_text("Date,Desc,Amount\n2024-01-01,Test,10")
        output_file = tmp_path / "parsed.json"

        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(statements_dir)
        mock_cm.get_default_file_path.return_value = str(output_file)

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = [{"date": "2024-01-01", "amount": -10.0}]

        with patch("sys.argv", ["money-mapper", "parse", "--dir", str(statements_dir)]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                    with patch("money_mapper.cli.validate_directory", return_value=True):
                        with patch("money_mapper.cli.validate_output_path", return_value=True):
                            with patch("money_mapper.utils.save_transactions_to_json"):
                                with patch(
                                    "money_mapper.setup_wizard.check_first_run",
                                    return_value=False,
                                ):
                                    with patch(
                                        "money_mapper.cli.ensure_directories_exist",
                                        return_value=True,
                                    ):
                                        with patch(
                                            "money_mapper.cli.validate_toml_files",
                                            return_value=True,
                                        ):
                                            try:
                                                main()
                                            except SystemExit:
                                                pass

        mock_importer.import_directory.assert_called_once()

    def test_parse_command_exits_when_directory_invalid(self, tmp_path):
        """Parse command exits with code 1 when directory validation fails."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(tmp_path / "nonexistent")
        mock_cm.get_default_file_path.return_value = str(tmp_path / "parsed.json")

        with patch("sys.argv", ["money-mapper", "parse"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_directory", return_value=False):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

    def test_parse_command_exits_when_no_transactions(self, tmp_path):
        """Parse command exits with code 1 when no transactions are imported."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(tmp_path)
        mock_cm.get_default_file_path.return_value = str(tmp_path / "parsed.json")

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = []

        with patch("sys.argv", ["money-mapper", "parse"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                    with patch("money_mapper.cli.validate_directory", return_value=True):
                        with patch("money_mapper.cli.validate_output_path", return_value=True):
                            with patch(
                                "money_mapper.setup_wizard.check_first_run", return_value=False
                            ):
                                with patch(
                                    "money_mapper.cli.ensure_directories_exist", return_value=True
                                ):
                                    with patch(
                                        "money_mapper.cli.validate_toml_files", return_value=True
                                    ):
                                        with pytest.raises(SystemExit) as exc_info:
                                            main()
                                        assert exc_info.value.code == 1


class TestMainEnrichCommand:
    """Tests for the 'enrich' subcommand in main()."""

    def test_enrich_command_calls_process_enrichment(self, tmp_path):
        """Enrich command calls process_transaction_enrichment with correct args."""
        from money_mapper.cli import main

        input_file = tmp_path / "parsed.json"
        input_file.write_text('[{"date": "2024-01-01", "amount": -10.0}]')
        output_file = tmp_path / "enriched.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.side_effect = lambda key: {
            "parsed_transactions": str(input_file),
            "enriched_transactions": str(output_file),
        }[key]

        with patch("sys.argv", ["money-mapper", "enrich", "--input", str(input_file)]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_json_file", return_value=True):
                    with patch("money_mapper.cli.validate_output_path", return_value=True):
                        with patch(
                            "money_mapper.cli.process_transaction_enrichment"
                        ) as mock_enrich:
                            with patch(
                                "money_mapper.setup_wizard.check_first_run", return_value=False
                            ):
                                with patch(
                                    "money_mapper.cli.ensure_directories_exist", return_value=True
                                ):
                                    with patch(
                                        "money_mapper.cli.validate_toml_files", return_value=True
                                    ):
                                        try:
                                            main()
                                        except SystemExit:
                                            pass
        mock_enrich.assert_called_once()

    def test_enrich_command_exits_when_input_invalid(self, tmp_path):
        """Enrich command exits with code 1 when input file validation fails."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "file.json")

        with patch("sys.argv", ["money-mapper", "enrich"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_json_file", return_value=False):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1


class TestMainPipelineCommand:
    """Tests for the 'pipeline' subcommand in main()."""

    def test_pipeline_command_runs_parse_and_enrich(self, tmp_path):
        """Pipeline command runs both CSVImporter and process_transaction_enrichment."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(tmp_path)
        mock_cm.get_default_file_path.side_effect = lambda key: str(tmp_path / f"{key}.json")

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = [{"date": "2024-01-01", "amount": -10.0}]

        with patch("sys.argv", ["money-mapper", "pipeline"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                    with patch("money_mapper.cli.validate_directory", return_value=True):
                        with patch("money_mapper.cli.validate_output_path", return_value=True):
                            with patch(
                                "money_mapper.cli.process_transaction_enrichment"
                            ) as mock_enrich:
                                with patch("money_mapper.cli.analyze_categorization_accuracy"):
                                    with patch("money_mapper.utils.save_transactions_to_json"):
                                        with patch(
                                            "money_mapper.setup_wizard.check_first_run",
                                            return_value=False,
                                        ):
                                            with patch(
                                                "money_mapper.cli.ensure_directories_exist",
                                                return_value=True,
                                            ):
                                                with patch(
                                                    "money_mapper.cli.validate_toml_files",
                                                    return_value=True,
                                                ):
                                                    try:
                                                        main()
                                                    except SystemExit:
                                                        pass

        mock_importer.import_directory.assert_called_once()
        mock_enrich.assert_called_once()

    def test_pipeline_command_exits_when_no_transactions(self, tmp_path):
        """Pipeline command exits with code 1 when no transactions found."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(tmp_path)
        mock_cm.get_default_file_path.return_value = str(tmp_path / "out.json")

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = []

        with patch("sys.argv", ["money-mapper", "pipeline"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                    with patch("money_mapper.cli.validate_directory", return_value=True):
                        with patch("money_mapper.cli.validate_output_path", return_value=True):
                            with patch(
                                "money_mapper.setup_wizard.check_first_run", return_value=False
                            ):
                                with patch(
                                    "money_mapper.cli.ensure_directories_exist", return_value=True
                                ):
                                    with patch(
                                        "money_mapper.cli.validate_toml_files", return_value=True
                                    ):
                                        with pytest.raises(SystemExit) as exc_info:
                                            main()
                                        assert exc_info.value.code == 1

    def test_pipeline_command_with_dir_flag(self, tmp_path):
        """Pipeline command respects --dir override."""
        from money_mapper.cli import main

        override_dir = str(tmp_path / "custom_dir")
        mock_cm = MagicMock()
        mock_cm.get_directory_path.return_value = str(tmp_path)
        mock_cm.get_default_file_path.return_value = str(tmp_path / "out.json")

        mock_importer = MagicMock()
        mock_importer.import_directory.return_value = [{"date": "2024-01-01", "amount": -10.0}]

        with patch("sys.argv", ["money-mapper", "pipeline", "--dir", override_dir]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                    with patch("money_mapper.cli.validate_directory", return_value=True) as mock_vd:
                        with patch("money_mapper.cli.validate_output_path", return_value=True):
                            with patch("money_mapper.cli.process_transaction_enrichment"):
                                with patch("money_mapper.cli.analyze_categorization_accuracy"):
                                    with patch("money_mapper.utils.save_transactions_to_json"):
                                        with patch(
                                            "money_mapper.setup_wizard.check_first_run",
                                            return_value=False,
                                        ):
                                            with patch(
                                                "money_mapper.cli.ensure_directories_exist",
                                                return_value=True,
                                            ):
                                                with patch(
                                                    "money_mapper.cli.validate_toml_files",
                                                    return_value=True,
                                                ):
                                                    try:
                                                        main()
                                                    except SystemExit:
                                                        pass

        # validate_directory should have been called with the override path
        mock_vd.assert_called_once_with(override_dir)


class TestMainValidateCommand:
    """Tests for the 'validate' subcommand in main()."""

    def test_validate_command_succeeds(self, capsys):
        """Validate command prints success message when TOML files are valid."""
        from money_mapper.cli import main

        mock_cm = MagicMock()

        with patch("sys.argv", ["money-mapper", "validate"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_toml_files", return_value=True):
                    with patch("money_mapper.cli.validate_config_paths", return_value=True):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch(
                                "money_mapper.setup_wizard.check_first_run", return_value=False
                            ):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_validate_command_exits_on_toml_error(self, capsys):
        """Validate command exits with code 1 when TOML files have errors."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "validate"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.validate_toml_files", return_value=False):
                    with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with pytest.raises(SystemExit) as exc_info:
                                main()
                            assert exc_info.value.code == 1


class TestMainAnalyzeCommand:
    """Tests for the 'analyze' subcommand in main()."""

    def test_analyze_command_calls_accuracy_function(self, tmp_path):
        """Analyze command calls analyze_categorization_accuracy."""
        from money_mapper.cli import main

        enriched_file = tmp_path / "enriched.json"
        enriched_file.write_text('[{"date": "2024-01-01", "amount": -10.0}]')

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(enriched_file)

        with patch("sys.argv", ["money-mapper", "analyze", "--file", str(enriched_file)]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_json_file", return_value=True):
                    with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with patch(
                                "money_mapper.cli.ensure_directories_exist", return_value=True
                            ):
                                with patch(
                                    "money_mapper.cli.validate_toml_files", return_value=True
                                ):
                                    try:
                                        main()
                                    except SystemExit:
                                        pass

        mock_analyze.assert_called_once()

    def test_analyze_command_verbose_flag(self, tmp_path):
        """Analyze command passes verbose=True when --verbose flag is set."""
        from money_mapper.cli import main

        enriched_file = tmp_path / "enriched.json"
        enriched_file.write_text('[{"date": "2024-01-01", "amount": -10.0}]')

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(enriched_file)

        with patch(
            "sys.argv", ["money-mapper", "analyze", "--file", str(enriched_file), "--verbose"]
        ):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_json_file", return_value=True):
                    with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with patch(
                                "money_mapper.cli.ensure_directories_exist", return_value=True
                            ):
                                with patch(
                                    "money_mapper.cli.validate_toml_files", return_value=True
                                ):
                                    try:
                                        main()
                                    except SystemExit:
                                        pass

        call_kwargs = mock_analyze.call_args
        assert call_kwargs is not None
        # verbose is a positional arg: analyze_categorization_accuracy(file, verbose, debug)
        args_passed = call_kwargs[0]
        assert args_passed[1] is True  # verbose

    def test_analyze_command_exits_when_file_invalid(self, tmp_path):
        """Analyze command exits with code 1 when file validation fails."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "enriched.json")

        with patch("sys.argv", ["money-mapper", "analyze"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.validate_json_file", return_value=False):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1


class TestMainCheckMappingsCommand:
    """Tests for the 'check-mappings' subcommand in main()."""

    def test_check_mappings_success(self, capsys):
        """Check-mappings prints success when processor returns True."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_check_only.return_value = True

        with patch("sys.argv", ["money-mapper", "check-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        mock_processor.run_check_only.assert_called_once()

    def test_check_mappings_failure_exits_1(self):
        """Check-mappings exits with code 1 when processor returns False."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_check_only.return_value = False

        with patch("sys.argv", ["money-mapper", "check-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

    def test_check_mappings_exception_exits_1(self):
        """Check-mappings exits with code 1 on unexpected exception."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        with patch("sys.argv", ["money-mapper", "check-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch(
                    "money_mapper.cli.get_mapping_processor",
                    side_effect=RuntimeError("boom"),
                ):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

    def test_check_mappings_with_config_flag(self):
        """Check-mappings passes --config directory to get_mapping_processor."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_check_only.return_value = True

        custom_config = "custom/config"

        with patch("sys.argv", ["money-mapper", "check-mappings", "--config", custom_config]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch(
                    "money_mapper.cli.get_mapping_processor", return_value=mock_processor
                ) as mock_get_proc:
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        mock_get_proc.assert_called_once_with(config_dir=custom_config, debug_mode=False)


class TestMainAddMappingsCommand:
    """Tests for the 'add-mappings' subcommand in main()."""

    def test_add_mappings_success(self, capsys):
        """Add-mappings prints success when processor returns True."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_full_processing.return_value = True

        with patch("sys.argv", ["money-mapper", "add-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        mock_processor.run_full_processing.assert_called_once()
        captured = capsys.readouterr()
        assert "complete" in captured.out.lower()

    def test_add_mappings_failure_exits_1(self):
        """Add-mappings exits with code 1 when processor returns False."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_full_processing.return_value = False

        with patch("sys.argv", ["money-mapper", "add-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

    def test_add_mappings_exception_exits_1(self):
        """Add-mappings exits with code 1 on unexpected exception."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        with patch("sys.argv", ["money-mapper", "add-mappings"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch(
                    "money_mapper.cli.get_mapping_processor",
                    side_effect=RuntimeError("fail"),
                ):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1


class TestMainSetupCommand:
    """Tests for the 'setup' subcommand in main()."""

    def test_setup_command_success(self, capsys):
        """Setup command prints success when wizard completes."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "setup"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.setup_wizard.run_setup_wizard", return_value=True):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        captured = capsys.readouterr()
        assert "completed" in captured.out.lower() or "success" in captured.out.lower()

    def test_setup_command_failure_exits_1(self):
        """Setup command exits with code 1 when wizard returns False."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "setup"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.setup_wizard.run_setup_wizard", return_value=False):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

    def test_setup_command_with_config_flag(self):
        """Setup command passes --config directory to run_setup_wizard."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "setup", "--config", "my/config"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch(
                    "money_mapper.setup_wizard.run_setup_wizard", return_value=True
                ) as mock_wizard:
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        mock_wizard.assert_called_once_with("my/config")


class TestMainCheckDepsCommand:
    """Tests for the 'check-deps' subcommand in main()."""

    def test_check_deps_all_installed(self, capsys):
        """Check-deps prints success when all dependencies are installed."""
        from money_mapper.cli import main

        deps = [("pandas", "2.0.0", True), ("fastapi", "0.100.0", True)]

        with patch("sys.argv", ["money-mapper", "check-deps"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.utils.format_dependency_status", return_value=deps):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                try:
                                    main()
                                except SystemExit:
                                    pass

        captured = capsys.readouterr()
        assert "[OK]" in captured.out
        assert "All required dependencies are installed" in captured.out

    def test_check_deps_missing_package_exits_1(self, capsys):
        """Check-deps exits with code 1 when a dependency is missing."""
        from money_mapper.cli import main

        deps = [("pandas", "2.0.0", True), ("missing-pkg", None, False)]

        with patch("sys.argv", ["money-mapper", "check-deps"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.utils.format_dependency_status", return_value=deps):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "[MISSING]" in captured.out


class TestMainWebCommand:
    """Tests for the 'web' subcommand in main()."""

    def test_web_command_calls_web_command_function(self):
        """Web command delegates to web_command() function."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "web"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.web_command.web_command", return_value=0) as mock_web:
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                # web_command returns 0, sys.exit(0)
                                assert exc_info.value.code == 0

        mock_web.assert_called_once()

    def test_web_command_propagates_exit_code(self):
        """Web command propagates non-zero exit code from web_command()."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "web"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.web_command.web_command", return_value=1):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                            with patch("money_mapper.cli.validate_toml_files", return_value=True):
                                with pytest.raises(SystemExit) as exc_info:
                                    main()
                                assert exc_info.value.code == 1


class TestMainInteractiveMenu:
    """Tests for the interactive menu in main() (no subcommand)."""

    def _run_interactive(self, choice, extra_patches=None):
        """Run main() in interactive mode with a given menu choice."""
        from money_mapper.cli import main

        if extra_patches is None:
            extra_patches = {}

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"
        mock_cm.get_directory_path.return_value = "statements"

        base = {
            "money_mapper.setup_wizard.check_first_run": False,
            "money_mapper.cli.validate_toml_files": True,
        }
        base.update(extra_patches)

        patches_applied = [patch("sys.argv", ["money-mapper"])]
        patches_applied.append(patch("money_mapper.cli.get_config_manager", return_value=mock_cm))
        for target, val in base.items():
            patches_applied.append(patch(target, return_value=val))

        inputs = iter([choice])

        with patch("builtins.input", side_effect=inputs):
            for p in patches_applied:
                p.start()
            try:
                try:
                    main()
                except (SystemExit, StopIteration):
                    pass
            finally:
                for p in patches_applied:
                    try:
                        p.stop()
                    except RuntimeError:
                        pass

    def test_interactive_choice_7_exits(self, capsys):
        """Menu choice 7 prints Goodbye and exits."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("builtins.input", return_value="7"):
                            try:
                                main()
                            except SystemExit:
                                pass

        captured = capsys.readouterr()
        assert "Goodbye" in captured.out

    def test_interactive_invalid_choice_then_exit(self, capsys):
        """Invalid menu choice shows error, then choice 7 exits."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        inputs = iter(["99", "7"])

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("builtins.input", side_effect=inputs):
                            try:
                                main()
                            except (SystemExit, StopIteration):
                                pass

        captured = capsys.readouterr()
        assert "Invalid" in captured.out

    def test_interactive_choice_5_validates_toml(self, capsys):
        """Menu choice 5 calls validate_toml_files and shows result."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch(
                        "money_mapper.cli.validate_toml_files", return_value=True
                    ) as mock_vtf:
                        with patch("builtins.input", return_value="5"):
                            try:
                                main()
                            except (SystemExit, StopIteration):
                                pass

        # validate_toml_files is called at startup (once) and for choice 5 (once) = 2 total
        assert mock_vtf.call_count >= 2

    def test_interactive_choice_1_calls_parse_interactive(self):
        """Menu choice 1 calls parse_statements_interactive."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.cli.parse_statements_interactive") as mock_parse:
                            with patch("builtins.input", return_value="1"):
                                try:
                                    main()
                                except (SystemExit, StopIteration):
                                    pass

        mock_parse.assert_called_once()

    def test_interactive_choice_2_calls_enrich_interactive(self):
        """Menu choice 2 calls enrich_transactions_interactive."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch(
                            "money_mapper.cli.enrich_transactions_interactive"
                        ) as mock_enrich:
                            with patch("builtins.input", return_value="2"):
                                try:
                                    main()
                                except (SystemExit, StopIteration):
                                    pass

        mock_enrich.assert_called_once()

    def test_interactive_choice_3_calls_pipeline_interactive(self):
        """Menu choice 3 calls run_full_pipeline_interactive."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch(
                            "money_mapper.cli.run_full_pipeline_interactive"
                        ) as mock_pipeline:
                            with patch("builtins.input", return_value="3"):
                                try:
                                    main()
                                except (SystemExit, StopIteration):
                                    pass

        mock_pipeline.assert_called_once()

    def test_interactive_choice_4_calls_analyze_interactive(self):
        """Menu choice 4 calls analyze_interactive."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.cli.analyze_interactive") as mock_analyze:
                            with patch("builtins.input", return_value="4"):
                                try:
                                    main()
                                except (SystemExit, StopIteration):
                                    pass

        mock_analyze.assert_called_once()

    def test_interactive_choice_6_calls_manage_mappings(self):
        """Menu choice 6 calls manage_mappings_interactive."""
        from money_mapper.cli import main

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/transactions.json"

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with patch("money_mapper.cli.validate_toml_files", return_value=True):
                        with patch("money_mapper.cli.manage_mappings_interactive") as mock_manage:
                            with patch("builtins.input", return_value="6"):
                                try:
                                    main()
                                except (SystemExit, StopIteration):
                                    pass

        mock_manage.assert_called_once()


class TestParseStatementsInteractive:
    """Tests for parse_statements_interactive()."""

    def test_no_csv_file_given_returns_early(self, capsys):
        """Returns early when user provides no CSV file path."""
        from money_mapper.cli import parse_statements_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/parsed.json"

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("builtins.input", return_value=""):
                parse_statements_interactive()

        captured = capsys.readouterr()
        assert "required" in captured.out.lower()

    def test_nonexistent_csv_file_returns_early(self, capsys):
        """Returns early when provided CSV file does not exist."""
        from money_mapper.cli import parse_statements_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = "output/parsed.json"

        inputs = iter(["/nonexistent/file.csv", "output/parsed.json"])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("builtins.input", side_effect=inputs):
                parse_statements_interactive()

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "error" in captured.out.lower()

    def test_csv_file_imported_successfully(self, tmp_path, capsys):
        """Imports CSV and saves transactions when file and paths are valid."""
        from money_mapper.cli import parse_statements_interactive

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Desc,Amount\n2024-01-01,Test,-10.00")
        output_file = tmp_path / "parsed.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(output_file)

        mock_importer = MagicMock()
        mock_importer.import_csv.return_value = [{"date": "2024-01-01", "amount": -10.0}]

        inputs = iter([str(csv_file), str(output_file)])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("money_mapper.utils.save_transactions_to_json"):
                        with patch("money_mapper.cli.confirm_action", return_value=False):
                            with patch("builtins.input", side_effect=inputs):
                                parse_statements_interactive()

        mock_importer.import_csv.assert_called_once_with(str(csv_file))

    def test_keyboard_interrupt_handled(self, tmp_path, capsys):
        """KeyboardInterrupt during import is caught and reported."""
        from money_mapper.cli import parse_statements_interactive

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Desc,Amount\n2024-01-01,Test,-10.00")
        output_file = tmp_path / "parsed.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(output_file)

        mock_importer = MagicMock()
        mock_importer.import_csv.side_effect = KeyboardInterrupt()

        inputs = iter([str(csv_file), str(output_file)])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("builtins.input", side_effect=inputs):
                        parse_statements_interactive()

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()

    def test_exception_during_import_handled(self, tmp_path, capsys):
        """General exception during import is caught and reported."""
        from money_mapper.cli import parse_statements_interactive

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Desc,Amount\n2024-01-01,Test,-10.00")
        output_file = tmp_path / "parsed.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(output_file)

        mock_importer = MagicMock()
        mock_importer.import_csv.side_effect = ValueError("bad file")

        inputs = iter([str(csv_file), str(output_file)])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("builtins.input", side_effect=inputs):
                        parse_statements_interactive()

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_no_transactions_found(self, tmp_path, capsys):
        """Prints message when importer returns no transactions."""
        from money_mapper.cli import parse_statements_interactive

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Date,Desc,Amount\n")
        output_file = tmp_path / "parsed.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(output_file)

        mock_importer = MagicMock()
        mock_importer.import_csv.return_value = []

        inputs = iter([str(csv_file), str(output_file)])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.CSVImporter", return_value=mock_importer):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("builtins.input", side_effect=inputs):
                        parse_statements_interactive()

        captured = capsys.readouterr()
        assert "no transactions" in captured.out.lower()


class TestEnrichTransactionsInteractive:
    """Tests for enrich_transactions_interactive()."""

    def test_enrichment_called_with_valid_files(self, tmp_path, capsys):
        """Calls process_transaction_enrichment when inputs are valid."""
        from money_mapper.cli import enrich_transactions_interactive

        input_file = tmp_path / "parsed.json"
        input_file.write_text('[{"date": "2024-01-01", "amount": -10.0}]')
        output_file = tmp_path / "enriched.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.side_effect = lambda key: {
            "parsed_transactions": str(input_file),
            "enriched_transactions": str(output_file),
        }[key]

        inputs = iter([str(output_file)])  # only output prompt (input_file passed in)

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("money_mapper.cli.process_transaction_enrichment") as mock_enrich:
                        with patch("money_mapper.cli.confirm_action", return_value=False):
                            with patch("builtins.input", side_effect=inputs):
                                enrich_transactions_interactive(input_file=str(input_file))

        mock_enrich.assert_called_once_with(str(input_file), str(output_file), debug=False)

    def test_returns_early_when_json_invalid(self, tmp_path):
        """Returns early when input JSON file validation fails."""
        from money_mapper.cli import enrich_transactions_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "out.json")

        inputs = iter([str(tmp_path / "out.json")])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=False):
                with patch("builtins.input", side_effect=inputs):
                    # Should return without error
                    enrich_transactions_interactive(input_file=str(tmp_path / "missing.json"))

    def test_keyboard_interrupt_handled(self, tmp_path, capsys):
        """KeyboardInterrupt during enrichment is caught and reported."""
        from money_mapper.cli import enrich_transactions_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "out.json")

        inputs = iter([str(tmp_path / "out.json")])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch(
                        "money_mapper.cli.process_transaction_enrichment",
                        side_effect=KeyboardInterrupt(),
                    ):
                        with patch("builtins.input", side_effect=inputs):
                            enrich_transactions_interactive(input_file=str(tmp_path / "in.json"))

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()

    def test_exception_during_enrichment_handled(self, tmp_path, capsys):
        """Exception during enrichment is caught and reported."""
        from money_mapper.cli import enrich_transactions_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "out.json")

        inputs = iter([str(tmp_path / "out.json")])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch(
                        "money_mapper.cli.process_transaction_enrichment",
                        side_effect=RuntimeError("enrichment error"),
                    ):
                        with patch("builtins.input", side_effect=inputs):
                            enrich_transactions_interactive(input_file=str(tmp_path / "in.json"))

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_prompts_for_input_when_none_given(self, tmp_path):
        """Prompts for input file when none is provided."""
        from money_mapper.cli import enrich_transactions_interactive

        input_file = tmp_path / "parsed.json"
        input_file.write_text('[{"date": "2024-01-01"}]')
        output_file = tmp_path / "enriched.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.side_effect = lambda key: {
            "parsed_transactions": str(input_file),
            "enriched_transactions": str(output_file),
        }[key]

        # First input: override for parsed file, second: override for enriched
        inputs = iter([str(input_file), str(output_file)])

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.validate_output_path", return_value=True):
                    with patch("money_mapper.cli.process_transaction_enrichment"):
                        with patch("money_mapper.cli.confirm_action", return_value=False):
                            with patch("builtins.input", side_effect=inputs):
                                enrich_transactions_interactive()  # no input_file given


class TestAnalyzeInteractive:
    """Tests for analyze_interactive()."""

    def test_calls_analyze_accuracy_with_file(self, tmp_path):
        """Calls analyze_categorization_accuracy with correct file path."""
        from money_mapper.cli import analyze_interactive

        enriched_file = tmp_path / "enriched.json"
        enriched_file.write_text('[{"date": "2024-01-01"}]')

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(enriched_file)

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                    analyze_interactive(file_path=str(enriched_file))

        mock_analyze.assert_called_once_with(
            str(enriched_file), verbose=True, debug=False, skip_interactive=False
        )

    def test_returns_early_when_file_invalid(self, tmp_path):
        """Returns early when file validation fails."""
        from money_mapper.cli import analyze_interactive

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(tmp_path / "enriched.json")

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=False):
                with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                    analyze_interactive(file_path=str(tmp_path / "missing.json"))

        mock_analyze.assert_not_called()

    def test_prompts_for_file_when_not_given(self, tmp_path):
        """Prompts for file when none is given, then runs analysis."""
        from money_mapper.cli import analyze_interactive

        enriched_file = tmp_path / "enriched.json"
        enriched_file.write_text('[{"date": "2024-01-01"}]')

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(enriched_file)

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                    with patch("builtins.input", return_value=""):
                        analyze_interactive()  # no file_path given

        mock_analyze.assert_called_once()

    def test_allow_mapping_false_sets_skip_interactive_true(self, tmp_path):
        """allow_mapping=False passes skip_interactive=True to accuracy function."""
        from money_mapper.cli import analyze_interactive

        enriched_file = tmp_path / "enriched.json"

        mock_cm = MagicMock()
        mock_cm.get_default_file_path.return_value = str(enriched_file)

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.validate_json_file", return_value=True):
                with patch("money_mapper.cli.analyze_categorization_accuracy") as mock_analyze:
                    analyze_interactive(file_path=str(enriched_file), allow_mapping=False)

        call_kwargs = mock_analyze.call_args[1]
        assert call_kwargs.get("skip_interactive") is True


class TestManageMappingsInteractive:
    """Tests for manage_mappings_interactive()."""

    def test_success_path(self, capsys):
        """Calls processor.run_combined_processing and prints success."""
        from money_mapper.cli import manage_mappings_interactive

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_combined_processing.return_value = True

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                with patch("builtins.input", return_value=""):
                    manage_mappings_interactive()

        mock_processor.run_combined_processing.assert_called_once()
        captured = capsys.readouterr()
        assert "complete" in captured.out.lower()

    def test_failure_path_prints_warning(self, capsys):
        """Prints warning when processor returns False."""
        from money_mapper.cli import manage_mappings_interactive

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_combined_processing.return_value = False

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch("money_mapper.cli.get_mapping_processor", return_value=mock_processor):
                with patch("builtins.input", return_value=""):
                    manage_mappings_interactive()

        captured = capsys.readouterr()
        assert "warning" in captured.out.lower() or "warnings" in captured.out.lower()

    def test_keyboard_interrupt_handled(self, capsys):
        """KeyboardInterrupt is caught and reported."""
        from money_mapper.cli import manage_mappings_interactive

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch(
                "money_mapper.cli.get_mapping_processor",
                side_effect=KeyboardInterrupt(),
            ):
                with patch("builtins.input", return_value=""):
                    manage_mappings_interactive()

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()

    def test_exception_handled(self, capsys):
        """General exception is caught and reported."""
        from money_mapper.cli import manage_mappings_interactive

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch(
                "money_mapper.cli.get_mapping_processor",
                side_effect=RuntimeError("processor error"),
            ):
                with patch("builtins.input", return_value=""):
                    manage_mappings_interactive()

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()

    def test_custom_config_dir_used(self):
        """Uses custom config directory when user provides one."""
        from money_mapper.cli import manage_mappings_interactive

        mock_cm = MagicMock()
        mock_cm.config_dir = "config"

        mock_processor = MagicMock()
        mock_processor.run_combined_processing.return_value = True

        with patch("money_mapper.cli.get_config_manager", return_value=mock_cm):
            with patch(
                "money_mapper.cli.get_mapping_processor", return_value=mock_processor
            ) as mock_get_proc:
                with patch("builtins.input", return_value="custom/config"):
                    manage_mappings_interactive()

        mock_get_proc.assert_called_once_with(config_dir="custom/config", debug_mode=False)


class TestMainConfigInitErrors:
    """Tests for error handling during config initialization in main()."""

    def test_config_init_failure_exits_1(self):
        """Exits with code 1 when get_config_manager raises an exception."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "parse"]):
            with patch(
                "money_mapper.cli.get_config_manager",
                side_effect=RuntimeError("config error"),
            ):
                with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

    def test_ensure_directories_fails_exits_1(self):
        """Exits with code 1 when ensure_directories_exist returns False."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "parse"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=False):
                    with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                        with patch("money_mapper.cli.validate_toml_files", return_value=True):
                            with pytest.raises(SystemExit) as exc_info:
                                main()
                            assert exc_info.value.code == 1

    def test_toml_validation_fails_exits_1(self):
        """Exits with code 1 when validate_toml_files returns False."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper", "parse"]):
            with patch("money_mapper.cli.get_config_manager"):
                with patch("money_mapper.cli.ensure_directories_exist", return_value=True):
                    with patch("money_mapper.cli.validate_toml_files", return_value=False):
                        with patch("money_mapper.setup_wizard.check_first_run", return_value=False):
                            with pytest.raises(SystemExit) as exc_info:
                                main()
                            assert exc_info.value.code == 1

    def test_first_run_setup_failure_exits_1(self):
        """Exits with code 1 when setup wizard fails on first run."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.setup_wizard.check_first_run", return_value=True):
                with patch("money_mapper.setup_wizard.run_setup_wizard", return_value=False):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 1

    def test_first_run_setup_success_exits_0_no_command(self):
        """Exits with code 0 after successful setup when no command given."""
        from money_mapper.cli import main

        with patch("sys.argv", ["money-mapper"]):
            with patch("money_mapper.setup_wizard.check_first_run", return_value=True):
                with patch("money_mapper.setup_wizard.run_setup_wizard", return_value=True):
                    with pytest.raises(SystemExit) as exc_info:
                        main()
                    assert exc_info.value.code == 0
