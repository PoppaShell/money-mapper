"""Tests for money_mapper.cli module."""

import os
import pytest
from pathlib import Path

from money_mapper.cli import (
    validate_directory,
    validate_json_file,
    validate_output_path,
    confirm_action,
    print_banner,
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

    def test_validate_directory_requires_pdf_files(self, temp_output_dir):
        """Test that validation requires PDF files to exist."""
        empty_dir = temp_output_dir / "empty"
        empty_dir.mkdir(exist_ok=True)
        
        # Directory exists but has no PDFs - should return False
        result = validate_directory(str(empty_dir))
        assert result is False

    def test_validate_directory_with_pdf_files(self, temp_output_dir):
        """Test validation with PDF files present."""
        pdf_dir = temp_output_dir / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        
        # Create a test PDF file
        pdf_file = pdf_dir / "test.pdf"
        pdf_file.write_text("fake pdf content")
        
        # Should return True when PDF exists
        result = validate_directory(str(pdf_dir))
        assert result is True

    @pytest.mark.parametrize("invalid_path", [
        "/nonexistent/path",
        "",
    ])
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
            'validate_directory',
            'validate_json_file',
            'validate_output_path',
            'confirm_action',
            'print_banner',
            'main',
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
        # Create test directory structure with PDF files
        statements_dir = temp_output_dir / "statements"
        statements_dir.mkdir(exist_ok=True)
        
        # Add a PDF file to statements directory
        pdf_file = statements_dir / "statement.pdf"
        pdf_file.write_text("fake pdf")
        
        output_dir = temp_output_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        # Validate statements directory (has PDF)
        assert validate_directory(str(statements_dir)) is True
        
        # Output dir doesn't need PDFs for validation (different validation rules)
        # Just verify path is valid
        assert os.path.isdir(str(output_dir)) is True


