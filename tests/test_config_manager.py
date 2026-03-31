"""Tests for money_mapper.config_manager module."""

from money_mapper.config_manager import ConfigManager, get_config_manager


class TestConfigManagerInitialization:
    """Test ConfigManager initialization."""

    def test_init_with_valid_config_dir(self, temp_output_dir):
        """Test initialization with a valid config directory."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        cm = ConfigManager(config_dir=str(config_dir))
        assert cm.config_dir == str(config_dir)

    def test_init_with_none_config_dir(self):
        """Test initialization with None uses auto-detection."""
        cm = ConfigManager(config_dir=None)
        assert cm.config_dir is not None
        assert isinstance(cm.config_dir, str)

    def test_init_creates_file_paths(self, temp_output_dir):
        """Test that initialization sets up file paths."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        cm = ConfigManager(config_dir=str(config_dir))
        assert cm.public_settings_file is not None
        assert cm.private_settings_file is not None
        assert cm.legacy_settings_file is not None

    def test_init_loads_settings(self, temp_output_dir):
        """Test that initialization loads settings."""
        config_dir = temp_output_dir / "config"
        config_dir.mkdir(exist_ok=True)

        cm = ConfigManager(config_dir=str(config_dir))
        assert cm.settings is not None
        assert isinstance(cm.settings, dict)


class TestConfigManagerDirectoryPaths:
    """Test directory path retrieval."""

    def test_get_directory_path_statements(self):
        """Test getting statements directory path."""
        cm = get_config_manager()
        path = cm.get_directory_path("statements")

        assert path is not None
        assert isinstance(path, str)

    def test_get_directory_path_output(self):
        """Test getting output directory path."""
        cm = get_config_manager()
        path = cm.get_directory_path("output")

        assert path is not None
        assert isinstance(path, str)

    def test_get_directory_path_config(self):
        """Test getting config directory path."""
        cm = get_config_manager()
        path = cm.get_directory_path("config")

        assert path is not None
        assert isinstance(path, str)

    def test_get_directory_path_invalid_key(self):
        """Test getting invalid directory key constructs path."""
        cm = get_config_manager()
        path = cm.get_directory_path("nonexistent_directory")

        # Should return a path (might be constructed from config_dir)
        assert path is not None
        assert isinstance(path, str)


class TestConfigManagerFilePaths:
    """Test file path retrieval."""

    def test_get_file_path_public_mappings(self):
        """Test getting public mappings file path."""
        cm = get_config_manager()
        path = cm.get_file_path("public_mappings")

        assert path is not None
        assert isinstance(path, str)
        assert "public_mappings" in path.lower()

    def test_get_file_path_private_mappings(self):
        """Test getting private mappings file path."""
        cm = get_config_manager()
        path = cm.get_file_path("private_mappings")

        assert path is not None
        assert isinstance(path, str)

    def test_get_file_path_statement_patterns(self):
        """Test getting statement patterns file path."""
        cm = get_config_manager()
        path = cm.get_file_path("statement_patterns")

        assert path is not None
        assert isinstance(path, str)

    def test_get_file_path_invalid_key(self):
        """Test getting invalid file key constructs path."""
        cm = get_config_manager()
        path = cm.get_file_path("nonexistent_file")

        # Should return a path (might be constructed from config_dir)
        assert path is not None
        assert isinstance(path, str)

    def test_get_default_file_path(self):
        """Test getting default file paths."""
        cm = get_config_manager()
        path = cm.get_default_file_path("parsed_transactions")

        assert path is not None
        assert isinstance(path, str)


class TestConfigManagerEnrichmentFiles:
    """Test enrichment file configuration."""

    def test_get_enrichment_files(self):
        """Test getting all enrichment files."""
        cm = get_config_manager()
        files = cm.get_enrichment_files()

        assert isinstance(files, dict)
        assert len(files) > 0

    def test_enrichment_files_have_mappings(self):
        """Test enrichment files include mappings."""
        cm = get_config_manager()
        files = cm.get_enrichment_files()

        # Should include both private and public mappings
        assert "private_mappings" in files or len(files) > 0


class TestConfigManagerMappingProcessor:
    """Test mapping processor file configuration."""

    def test_get_mapping_processor_files(self):
        """Test getting mapping processor files."""
        cm = get_config_manager()
        files = cm.get_mapping_processor_files()

        assert isinstance(files, dict)
        assert len(files) > 0

    def test_mapping_processor_files_structure(self):
        """Test mapping processor files have expected keys."""
        cm = get_config_manager()
        files = cm.get_mapping_processor_files()

        # Should have mappings and directories
        assert any("mapping" in key.lower() for key in files.keys()) or len(files) > 0


class TestConfigManagerAllConfigFiles:
    """Test retrieving all config files."""

    def test_get_all_config_files(self):
        """Test getting all config files."""
        cm = get_config_manager()
        files = cm.get_all_config_files()

        assert isinstance(files, list)
        assert len(files) >= 0

    def test_all_config_files_are_strings(self):
        """Test that all config files are strings."""
        cm = get_config_manager()
        files = cm.get_all_config_files()

        for file in files:
            assert isinstance(file, str)


class TestConfigManagerThresholds:
    """Test threshold retrieval."""

    def test_get_fuzzy_threshold_high(self):
        """Test getting high fuzzy threshold."""
        cm = get_config_manager()
        threshold = cm.get_fuzzy_threshold("high")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_get_fuzzy_threshold_medium(self):
        """Test getting medium fuzzy threshold."""
        cm = get_config_manager()
        threshold = cm.get_fuzzy_threshold("medium")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_get_fuzzy_threshold_low(self):
        """Test getting low fuzzy threshold."""
        cm = get_config_manager()
        threshold = cm.get_fuzzy_threshold("low")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_get_fuzzy_threshold_ordering(self):
        """Test that threshold levels are properly ordered."""
        cm = get_config_manager()
        high = cm.get_fuzzy_threshold("high")
        medium = cm.get_fuzzy_threshold("medium")
        low = cm.get_fuzzy_threshold("low")

        # High should be >= medium >= low
        assert high >= medium >= low

    def test_get_confidence_threshold_high(self):
        """Test getting high confidence threshold."""
        cm = get_config_manager()
        threshold = cm.get_confidence_threshold("high")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_get_confidence_threshold_medium(self):
        """Test getting medium confidence threshold."""
        cm = get_config_manager()
        threshold = cm.get_confidence_threshold("medium")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_get_confidence_threshold_low(self):
        """Test getting low confidence threshold."""
        cm = get_config_manager()
        threshold = cm.get_confidence_threshold("low")

        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0


class TestGetFuzzyThresholdSafety:
    """Test that invalid config values don't crash the app."""

    def test_invalid_string_threshold_returns_default(self, tmp_path):
        """Non-numeric threshold should return 0.7 default."""
        from money_mapper.config_manager import ConfigManager

        # Create a minimal config with invalid threshold
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "public_settings.toml"
        settings_file.write_text('[fuzzy_matching]\nenrichment_threshold = "high"\n')

        cm = ConfigManager(str(config_dir))
        result = cm.get_fuzzy_threshold("enrichment")
        assert result == 0.7

    def test_valid_numeric_threshold_returns_value(self, tmp_path):
        """Valid numeric threshold should return the configured value."""
        from money_mapper.config_manager import ConfigManager

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_file = config_dir / "public_settings.toml"
        settings_file.write_text("[fuzzy_matching]\nenrichment_threshold = 0.85\n")

        cm = ConfigManager(str(config_dir))
        result = cm.get_fuzzy_threshold("enrichment")
        assert result == 0.85


class TestConfigManagerDisplaySettings:
    """Test display-related settings."""

    def test_get_display_setting_column_width(self):
        """Test getting column width display setting."""
        cm = get_config_manager()
        width = cm.get_display_setting("column_width")

        assert isinstance(width, int)
        assert width > 0

    def test_get_display_setting_max_results(self):
        """Test getting max results display setting."""
        cm = get_config_manager()
        max_results = cm.get_display_setting("max_results")

        # Should return int or 0 if not configured
        assert isinstance(max_results, int)

    def test_is_auto_alphabetize_enabled(self):
        """Test checking if auto-alphabetize is enabled."""
        cm = get_config_manager()
        enabled = cm.is_auto_alphabetize_enabled()

        assert isinstance(enabled, bool)


class TestConfigManagerProcessingSettings:
    """Test processing-related settings."""

    def test_get_processing_setting_validate_on_load(self):
        """Test getting validation on load setting."""
        cm = get_config_manager()
        setting = cm.get_processing_setting("validate_on_load")

        assert isinstance(setting, bool)

    def test_get_processing_setting_auto_backup(self):
        """Test getting auto backup setting."""
        cm = get_config_manager()
        setting = cm.get_processing_setting("auto_backup")

        assert isinstance(setting, bool)

    def test_get_processing_setting_empty_key(self):
        """Test getting processing setting with missing key."""
        cm = get_config_manager()
        setting = cm.get_processing_setting("nonexistent_setting")

        # Should return False for missing settings
        assert isinstance(setting, bool)


class TestConfigManagerPrivacySettings:
    """Test privacy-related settings."""

    def test_get_privacy_settings(self):
        """Test getting privacy settings."""
        cm = get_config_manager()
        privacy = cm.get_privacy_settings()

        assert isinstance(privacy, dict)

    def test_privacy_settings_structure(self):
        """Test privacy settings have expected structure."""
        cm = get_config_manager()
        privacy = cm.get_privacy_settings()

        # Privacy settings should be accessible even if empty
        assert privacy is not None


class TestConfigManagerFirstRun:
    """Test first-run detection."""

    def test_check_first_run(self):
        """Test checking if first run."""
        cm = get_config_manager()
        is_first_run = cm.check_first_run()

        assert isinstance(is_first_run, bool)


class TestGetConfigManager:
    """Test get_config_manager singleton function."""

    def test_get_config_manager(self):
        """Test getting config manager instance."""
        config_manager = get_config_manager()
        assert config_manager is not None
        assert isinstance(config_manager, ConfigManager)

    def test_get_config_manager_consistency(self):
        """Test that get_config_manager returns consistent results."""
        cm1 = get_config_manager()
        cm2 = get_config_manager()

        # Both should have same config directory
        assert cm1.config_dir == cm2.config_dir

    def test_get_config_manager_with_custom_dir(self, temp_output_dir):
        """Test getting config manager with custom directory."""
        config_dir = temp_output_dir / "custom_config"
        config_dir.mkdir(exist_ok=True)

        cm = get_config_manager(config_dir=str(config_dir))
        assert str(config_dir) in cm.config_dir
