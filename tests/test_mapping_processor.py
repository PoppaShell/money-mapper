"""Tests for money_mapper.mapping_processor module."""

import os

import pytest

from money_mapper.mapping_processor import MappingProcessor


class TestMappingProcessorInitialization:
    """Test MappingProcessor initialization."""

    def test_init_with_temp_config(self, temp_output_dir):
        """Test initialization with temporary config directory."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir), debug_mode=False)
        assert mp.config_dir == str(config_dir)
        assert mp.debug_mode is False

    def test_init_with_debug_mode(self, temp_output_dir):
        """Test initialization with debug mode enabled."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir), debug_mode=True)
        assert mp.debug_mode is True

    def test_init_creates_backup_directory(self, temp_output_dir):
        """Test that initialization creates backup directory."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        # Backup directory should be created or accessible
        assert mp.backup_dir is not None

    def test_init_loads_config(self, temp_output_dir):
        """Test that initialization loads config."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        assert mp.config is not None


class TestMappingProcessorFileOperations:
    """Test file operations in MappingProcessor."""

    def test_load_toml_file_nonexistent(self, temp_output_dir):
        """Test loading nonexistent TOML file returns empty dict."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)
        mp = MappingProcessor(config_dir=str(config_dir))

        result = mp._load_toml_file("/nonexistent/path/file.toml")
        assert result == {}

    def test_load_toml_file_valid(self, temp_output_dir):
        """Test loading valid TOML file."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Create test TOML file
        toml_file = temp_output_dir / "test.toml"
        toml_file.write_text("[section]\nkey = 'value'\n")

        mp = MappingProcessor(config_dir=str(config_dir))
        result = mp._load_toml_file(str(toml_file))

        assert "section" in result
        assert result["section"]["key"] == "value"

    def test_backup_file_nonexistent(self, temp_output_dir):
        """Test backing up nonexistent file returns empty string."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)
        mp = MappingProcessor(config_dir=str(config_dir))

        result = mp._backup_file("/nonexistent/file.toml")
        assert result == ""

    def test_backup_file_creates_backup(self, temp_output_dir):
        """Test backup file creation."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Create file to backup
        test_file = temp_output_dir / "mappings.toml"
        test_file.write_text("[test]\ndata = 'value'\n")

        mp = MappingProcessor(config_dir=str(config_dir))
        backup_path = mp._backup_file(str(test_file))

        # Backup should be created and path returned
        assert backup_path != ""
        assert os.path.exists(backup_path)
        assert "backup_" in backup_path

    def test_backup_without_actually_backing_up(self, temp_output_dir):
        """Test backup planning without actually creating file."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        test_file = temp_output_dir / "mappings.toml"
        test_file.write_text("[test]\ndata = 'value'\n")

        mp = MappingProcessor(config_dir=str(config_dir))
        backup_path = mp._backup_file(str(test_file), actually_backup=False)

        # Backup should be reported but not actually created
        assert backup_path != ""


class TestMappingProcessorDebugMode:
    """Test debug mode functionality."""

    def test_debug_print_no_output_when_disabled(self, temp_output_dir, capsys):
        """Test debug print doesn't output when debug disabled."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir), debug_mode=False)
        mp._debug_print("test message")

        # When debug mode is off, nothing should be printed
        captured = capsys.readouterr()
        assert "test message" not in captured.out

    def test_debug_print_outputs_when_enabled(self, temp_output_dir, capsys):
        """Test debug print outputs when debug enabled."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir), debug_mode=True)
        mp._debug_print("test message")

        # When debug mode is on, message should be printed
        captured = capsys.readouterr()
        assert "test message" in captured.out or "DEBUG:" in captured.out


class TestMappingProcessorIntegration:
    """Integration tests for MappingProcessor."""

    def test_processor_initialization_complete(self, temp_output_dir):
        """Test complete initialization of MappingProcessor."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))

        # All key attributes should be initialized
        assert mp.config_dir == str(config_dir)
        assert mp.private_mappings is not None
        assert mp.public_mappings is not None
        assert mp.backup_dir is not None

    def test_processor_settings_loading(self, temp_output_dir):
        """Test loading settings from config manager."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        settings = mp._load_settings()

        assert "processing" in settings
        assert "fuzzy_matching" in settings

    def test_get_category_description_valid_category(self, temp_output_dir):
        """Test getting description for valid category."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        # Using a common PFC category
        description = mp._get_category_description("FOOD_AND_DINING")

        assert description is not None
        assert isinstance(description, str)

    def test_get_category_description_invalid_category(self, temp_output_dir):
        """Test getting description for invalid category."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        description = mp._get_category_description("NONEXISTENT_CATEGORY")

        # Should return default description
        assert description == "Financial transaction category"

    def test_load_settings_returns_dict(self, temp_output_dir):
        """Test that settings are returned as dictionary."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        settings = mp._load_settings()

        assert isinstance(settings, dict)
        assert len(settings) > 0

    @pytest.mark.parametrize("debug_mode", [True, False])
    def test_processor_with_various_debug_modes(self, temp_output_dir, debug_mode):
        """Test processor initialization with various debug modes."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir), debug_mode=debug_mode)
        assert mp.debug_mode == debug_mode


class TestMappingProcessorBackupCleanup:
    """Test backup cleanup functionality."""

    def test_cleanup_old_backups_no_backups(self, temp_output_dir):
        """Test cleanup when no backups exist."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        # Should not raise error
        mp._cleanup_old_backups()

    def test_cleanup_old_backups_empty_directory(self, temp_output_dir):
        """Test cleanup with empty backup directory."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        backup_dir = temp_output_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        mp = MappingProcessor(config_dir=str(config_dir))
        mp.backup_dir = str(backup_dir)
        # Should not raise error
        mp._cleanup_old_backups()
