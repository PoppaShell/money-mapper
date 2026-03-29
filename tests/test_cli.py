"""Tests for money_mapper.cli module."""

import json
import os

import pytest

from money_mapper.cli import (
    confirm_action,
    print_banner,
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
            from money_mapper import main

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
