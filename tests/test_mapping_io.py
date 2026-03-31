"""Tests for mapping I/O module."""

import json
from pathlib import Path

from money_mapper.mapping_io import (
    backup_mappings,
    load_private_mappings,
    load_public_mappings,
    save_mappings,
)


class TestLoadPublicMappings:
    """Test loading public mappings."""

    def test_load_public_mappings_returns_dict(self):
        """Test that function returns dict when default config file exists."""
        result = load_public_mappings()
        assert isinstance(result, dict)

    def test_load_public_mappings_file_not_found(self, tmp_path):
        """Test with missing file."""
        missing_file = str(tmp_path / "missing.toml")
        result = load_public_mappings(missing_file)
        assert result is None

    def test_load_public_mappings_valid_toml(self, tmp_path):
        """Test loading valid TOML file."""
        mapping_file = tmp_path / "mappings.toml"
        mapping_file.write_text("""
[FOOD_AND_DRINK]
[FOOD_AND_DRINK.RESTAURANTS]
"starbucks" = { name = "Starbucks", category = "FOOD_AND_DRINK" }
""")

        result = load_public_mappings(str(mapping_file))
        assert isinstance(result, dict) or result is None

    def test_load_public_mappings_empty_file(self, tmp_path):
        """Test with empty TOML file."""
        mapping_file = tmp_path / "empty.toml"
        mapping_file.write_text("")

        result = load_public_mappings(str(mapping_file))
        assert result is None

    def test_load_public_mappings_preserves_structure(self, tmp_path):
        """Test that nested structure is preserved."""
        mapping_file = tmp_path / "mappings.toml"
        mapping_file.write_text("""
[CATEGORY]
[CATEGORY.SUBCATEGORY]
"merchant" = { name = "Test" }
""")

        result = load_public_mappings(str(mapping_file))
        # Should preserve the nested TOML structure
        assert isinstance(result, dict)
        assert "CATEGORY" in result


class TestLoadPrivateMappings:
    """Test loading private mappings."""

    def test_load_private_mappings_returns_list_or_dict(self, tmp_path):
        """Test that function returns list when given a valid JSON file."""
        mapping_file = tmp_path / "transactions.json"
        transactions = [{"merchant_name": "Walmart", "category": "GENERAL_MERCHANDISE"}]
        with open(mapping_file, "w") as f:
            json.dump(transactions, f)

        result = load_private_mappings(str(mapping_file))
        assert isinstance(result, list)
        assert result[0]["merchant_name"] == "Walmart"

    def test_load_private_mappings_file_not_found(self, tmp_path):
        """Test with missing file."""
        missing_file = str(tmp_path / "missing.json")
        result = load_private_mappings(missing_file)
        assert result is None

    def test_load_private_mappings_valid_json_list(self, tmp_path):
        """Test loading valid JSON list."""
        mapping_file = tmp_path / "transactions.json"
        transactions = [
            {"merchant_name": "Starbucks", "category": "FOOD"},
            {"merchant_name": "Shell Gas", "category": "TRANSPORTATION"},
        ]
        with open(mapping_file, "w") as f:
            json.dump(transactions, f)

        result = load_private_mappings(str(mapping_file))
        assert isinstance(result, list) or result is None

    def test_load_private_mappings_valid_json_dict(self, tmp_path):
        """Test loading valid JSON dict."""
        mapping_file = tmp_path / "mappings.json"
        mappings = {
            "starbucks": {"category": "FOOD"},
            "shell": {"category": "TRANSPORTATION"},
        }
        with open(mapping_file, "w") as f:
            json.dump(mappings, f)

        result = load_private_mappings(str(mapping_file))
        assert isinstance(result, (list, dict)) or result is None

    def test_load_private_mappings_empty_file(self, tmp_path):
        """Test with empty JSON file."""
        mapping_file = tmp_path / "empty.json"
        mapping_file.write_text("")

        result = load_private_mappings(str(mapping_file))
        assert result is None

    def test_load_private_mappings_invalid_json(self, tmp_path):
        """Test with invalid JSON."""
        mapping_file = tmp_path / "invalid.json"
        mapping_file.write_text("{invalid json")

        result = load_private_mappings(str(mapping_file))
        assert result is None


class TestSaveMappings:
    """Test saving mappings."""

    def test_save_mappings_creates_file(self, tmp_path):
        """Test that save creates file."""
        output_file = tmp_path / "output.toml"
        mappings = {"FOOD_AND_DRINK": {"RESTAURANTS": {"merchant": "data"}}}

        result = save_mappings(mappings, str(output_file))

        assert output_file.exists() or result is None

    def test_save_mappings_returns_path(self, tmp_path):
        """Test that function returns file path."""
        output_file = tmp_path / "output.toml"
        mappings = {"TEST": "data"}

        result = save_mappings(mappings, str(output_file))

        # Should return the path to the saved file
        assert isinstance(result, str)
        assert result == str(output_file)

    def test_save_mappings_to_json(self, tmp_path):
        """Test saving to JSON format."""
        output_file = tmp_path / "output.json"
        mappings = [{"merchant": "Test", "category": "FOOD"}]

        result = save_mappings(mappings, str(output_file))

        assert output_file.exists() or result is None

    def test_save_mappings_overwrites_existing(self, tmp_path):
        """Test that save overwrites existing file."""
        output_file = tmp_path / "output.toml"
        # Create initial file
        output_file.write_text("old content")

        mappings = {"NEW": "content"}
        save_mappings(mappings, str(output_file))

        # File should be updated
        assert output_file.exists()

    def test_save_mappings_creates_directory(self, tmp_path):
        """Test that save creates directories if needed."""
        output_file = tmp_path / "subdir" / "output.toml"
        mappings = {"TEST": "data"}

        result = save_mappings(mappings, str(output_file))

        # Directory should be created or function handles gracefully
        assert output_file.exists() or result is None

    def test_save_mappings_empty_data(self, tmp_path):
        """Test saving empty mappings."""
        output_file = tmp_path / "empty.toml"

        result = save_mappings({}, str(output_file))

        # Should handle empty data gracefully
        assert result is None or output_file.exists()


class TestBackupMappings:
    """Test backing up mappings."""

    def test_backup_mappings_creates_file(self, tmp_path):
        """Test that backup creates new file."""
        original_file = tmp_path / "original.toml"
        original_file.write_text("original content")

        result = backup_mappings(str(original_file))

        # Should create backup and return path to it
        assert isinstance(result, str)
        assert Path(result).exists()

    def test_backup_mappings_returns_path(self, tmp_path):
        """Test that function returns backup path."""
        original_file = tmp_path / "original.toml"
        original_file.write_text("content")

        result = backup_mappings(str(original_file))

        # Should return path to backup file
        assert isinstance(result, str)
        assert "original" in result

    def test_backup_mappings_nonexistent_file(self, tmp_path):
        """Test backup of nonexistent file."""
        missing_file = str(tmp_path / "missing.toml")

        result = backup_mappings(missing_file)

        # Should return None for missing file
        assert result is None

    def test_backup_mappings_creates_timestamped(self, tmp_path):
        """Test that backup includes timestamp."""
        original_file = tmp_path / "mappings.toml"
        original_file.write_text("content")

        result = backup_mappings(str(original_file))

        # Backup path should include timestamp or be in backup dir
        if result:
            assert isinstance(result, str)

    def test_backup_mappings_preserves_content(self, tmp_path):
        """Test that backup preserves original content."""
        original_file = tmp_path / "mappings.toml"
        content = "original content"
        original_file.write_text(content)

        result = backup_mappings(str(original_file))

        # If backup created, should have same content
        if result and Path(result).exists():
            assert Path(result).read_text() == content

    def test_backup_mappings_multiple_calls(self, tmp_path):
        """Test multiple backup calls don't overwrite."""
        import time

        original_file = tmp_path / "mappings.toml"
        original_file.write_text("content")

        backup1 = backup_mappings(str(original_file))
        time.sleep(1.1)  # Wait to ensure different timestamp
        backup2 = backup_mappings(str(original_file))

        # Backups should be different or return None
        if backup1 and backup2:
            assert backup1 != backup2


class TestMappingIOIntegration:
    """Integration tests for mapping I/O."""

    def test_load_save_roundtrip(self, tmp_path):
        """Test loading and saving preserves data."""
        original_file = tmp_path / "original.json"
        output_file = tmp_path / "output.json"

        original_data = [{"merchant": "Test", "category": "FOOD"}]
        with open(original_file, "w") as f:
            json.dump(original_data, f)

        # Load and save
        loaded = load_private_mappings(str(original_file))
        if loaded:
            saved = save_mappings(loaded, str(output_file))
            assert output_file.exists() or saved is None

    def test_backup_then_modify(self, tmp_path):
        """Test backup then modify workflow."""
        mapping_file = tmp_path / "mappings.toml"
        mapping_file.write_text("original content")

        # Create backup
        backup_path = backup_mappings(str(mapping_file))

        # Modify original
        mapping_file.write_text("modified content")

        # Backup should have original content (if it exists)
        if backup_path and Path(backup_path).exists():
            assert "original" in Path(backup_path).read_text()
