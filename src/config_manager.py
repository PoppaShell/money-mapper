#!/usr/bin/env python3
"""
Configuration Manager - Centralized configuration management for Money Mapper.

This module provides a single source of truth for all file paths, directories,
and settings used throughout the Money Mapper application.
"""

import os
import sys
import tomllib
from typing import Dict, List, Optional, Tuple

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ConfigManager:
    """Centralized configuration manager for Money Mapper."""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager.

        Args:
            config_dir: Configuration directory path. Auto-detected if None.
        """
        self.config_dir = self._find_config_directory(config_dir)
        self.public_settings_file = os.path.join(self.config_dir, "public_settings.toml")
        self.private_settings_file = os.path.join(self.config_dir, "private_settings.toml")
        # Keep legacy settings file for migration purposes
        self.legacy_settings_file = os.path.join(self.config_dir, "settings.toml")
        self.settings = self._load_settings()
    
    def _find_config_directory(self, config_dir: Optional[str]) -> str:
        """Find the configuration directory automatically."""
        if config_dir and os.path.exists(config_dir):
            return os.path.abspath(config_dir)
        
        # Auto-detect config directory
        current_dir = os.getcwd()
        
        # If we're in src/, look for ../config
        if os.path.basename(current_dir) == 'src':
            parent_config = os.path.join(os.path.dirname(current_dir), 'config')
            if os.path.exists(parent_config):
                return os.path.abspath(parent_config)
        
        # Look for config/ in current directory
        local_config = os.path.join(current_dir, 'config')
        if os.path.exists(local_config):
            return os.path.abspath(local_config)
        
        # Default to config/ (will be created if needed)
        return os.path.abspath('config')
    
    def _load_settings(self) -> Dict:
        """
        Load and merge settings from public_settings.toml and private_settings.toml.

        Returns:
            Merged settings dictionary with private settings taking precedence.
        """
        # Try loading public settings
        public_settings = self._load_public_settings()

        # Try loading private settings
        private_settings = self._load_private_settings()

        # Merge settings (private takes precedence)
        merged_settings = self._merge_settings(public_settings, private_settings)

        return merged_settings

    def _load_public_settings(self) -> Dict:
        """Load public settings from public_settings.toml or legacy settings.toml."""
        # Try new public_settings.toml first
        if os.path.exists(self.public_settings_file):
            try:
                with open(self.public_settings_file, 'rb') as f:
                    return tomllib.load(f)
            except Exception as e:
                print(f"Warning: Could not load public_settings.toml: {e}")

        # Fall back to legacy settings.toml for migration
        if os.path.exists(self.legacy_settings_file):
            try:
                with open(self.legacy_settings_file, 'rb') as f:
                    legacy_settings = tomllib.load(f)
                    # Remove privacy section if it exists (will be in private_settings.toml)
                    legacy_settings.pop('privacy', None)
                    return legacy_settings
            except Exception as e:
                print(f"Warning: Could not load settings.toml: {e}")

        # Return defaults if nothing found
        print("Warning: No settings file found. Using defaults.")
        return self._get_default_settings()

    def _load_private_settings(self) -> Dict:
        """Load private settings from private_settings.toml."""
        if not os.path.exists(self.private_settings_file):
            # Private settings don't exist yet (first run or not configured)
            return {}

        try:
            with open(self.private_settings_file, 'rb') as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"Warning: Could not load private_settings.toml: {e}")
            return {}

    def _merge_settings(self, public: Dict, private: Dict) -> Dict:
        """
        Merge public and private settings, with private taking precedence.

        Args:
            public: Public settings dictionary
            private: Private settings dictionary

        Returns:
            Merged settings dictionary
        """
        import copy
        merged = copy.deepcopy(public)

        # Recursively merge dictionaries
        def deep_merge(base, override):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value

        deep_merge(merged, private)
        return merged
    
    def _get_default_settings(self) -> Dict:
        """Return default settings structure."""
        return {
            'directories': {
                'statements': 'statements',
                'output': 'output',
                'config': 'config'
            },
            'file_paths': {
                'private_mappings': 'private_mappings.toml',
                'public_mappings': 'public_mappings.toml',
                'private_settings': 'private_settings.toml',
                'public_settings': 'public_settings.toml',
                'plaid_categories': 'plaid_categories.toml',
                'statement_patterns': 'statement_patterns.toml',
                'new_mappings_template': 'new_mappings.toml'
            },
            'default_files': {
                'parsed_transactions': 'financial_transactions.json',
                'enriched_transactions': 'enriched_transactions.json'
            },
            'fuzzy_matching': {
                'enrichment_threshold': 0.7,
                'mapping_processor_threshold': 0.8
            },
            'file_management': {
                'backup_directory': 'backups'
            },
            'processing': {
                'auto_alphabetize': True
            },
            'confidence_thresholds': {
                'high_confidence': 0.8,
                'medium_confidence': 0.5
            },
            'display': {
                'max_examples_shown': 10
            }
        }
    
    def get_directory_path(self, directory_key: str) -> str:
        """
        Get absolute path for a directory.
        
        Args:
            directory_key: Key from [directories] section
            
        Returns:
            Absolute directory path
        """
        directories = self.settings.get('directories', {})
        relative_path = directories.get(directory_key, directory_key)
        
        # If we're in src/, make paths relative to parent directory
        if os.path.basename(os.getcwd()) == 'src':
            base_dir = os.path.dirname(os.getcwd())
        else:
            base_dir = os.getcwd()
        
        return os.path.join(base_dir, relative_path)
    
    def get_file_path(self, file_key: str) -> str:
        """
        Get absolute path for a configuration file.
        
        Args:
            file_key: Key from [file_paths] section
            
        Returns:
            Absolute file path
        """
        file_paths = self.settings.get('file_paths', {})
        filename = file_paths.get(file_key, f"{file_key}.toml")
        return os.path.join(self.config_dir, filename)
    
    def get_default_file_path(self, file_key: str) -> str:
        """
        Get absolute path for a default output file.
        
        Args:
            file_key: Key from [default_files] section
            
        Returns:
            Absolute file path in output directory
        """
        default_files = self.settings.get('default_files', {})
        filename = default_files.get(file_key, f"{file_key}.json")
        output_dir = self.get_directory_path('output')
        return os.path.join(output_dir, filename)
    
    def get_enrichment_files(self) -> Dict[str, str]:
        """Get all file paths needed for transaction enrichment."""
        return {
            'private_mappings': self.get_file_path('private_mappings'),
            'public_mappings': self.get_file_path('public_mappings'),
            'plaid_categories': self.get_file_path('plaid_categories')
        }
    
    def get_mapping_processor_files(self) -> Dict[str, str]:
        """Get all file paths needed for mapping processor."""
        file_management = self.settings.get('file_management', {})
        backup_dir = file_management.get('backup_directory', 'backups')
        
        # Make backup directory absolute
        if os.path.basename(os.getcwd()) == 'src':
            base_dir = os.path.dirname(os.getcwd())
        else:
            base_dir = os.getcwd()
        
        return {
            'private_mappings': self.get_file_path('private_mappings'),
            'public_mappings': self.get_file_path('public_mappings'),
            'new_mappings_template': self.get_file_path('new_mappings_template'),
            'backup_directory': os.path.join(base_dir, backup_dir)
        }
    
    def get_all_config_files(self) -> List[str]:
        """Get list of all configuration file paths."""
        file_paths = self.settings.get('file_paths', {})
        config_files = []
        
        for file_key in file_paths.keys():
            if file_key != 'new_mappings_template':  # Skip template file
                config_files.append(self.get_file_path(file_key))
        
        return config_files
    
    def get_fuzzy_threshold(self, threshold_type: str) -> float:
        """
        Get fuzzy matching threshold.
        
        Args:
            threshold_type: Type of threshold ('enrichment' or 'mapping_processor')
            
        Returns:
            Threshold value
        """
        fuzzy_matching = self.settings.get('fuzzy_matching', {})
        key = f"{threshold_type}_threshold"
        return fuzzy_matching.get(key, 0.7)
    
    def get_confidence_threshold(self, confidence_level: str) -> float:
        """
        Get confidence threshold value.
        
        Args:
            confidence_level: Level ('high_confidence' or 'medium_confidence')
            
        Returns:
            Threshold value
        """
        thresholds = self.settings.get('confidence_thresholds', {})
        return thresholds.get(confidence_level, 0.5)
    
    def get_display_setting(self, setting_key: str) -> int:
        """
        Get display setting value.
        
        Args:
            setting_key: Setting key from [display] section
            
        Returns:
            Setting value
        """
        display = self.settings.get('display', {})
        return display.get(setting_key, 10)
    
    def is_auto_alphabetize_enabled(self) -> bool:
        """Check if auto-alphabetization is enabled."""
        processing = self.settings.get('processing', {})
        return processing.get('auto_alphabetize', True)

    def get_processing_setting(self, setting_key: str) -> bool:
        """
        Get processing setting value.

        Args:
            setting_key: Setting key from [processing] section

        Returns:
            Setting value (defaults to appropriate value if not found)
        """
        processing = self.settings.get('processing', {})

        # Default values for known settings
        defaults = {
            'auto_alphabetize': True,
            'interactive_conflicts': True,
            'validate_categories': True
        }

        return processing.get(setting_key, defaults.get(setting_key, False))

    def check_first_run(self) -> bool:
        """
        Check if this is the first run (private config files missing).

        Returns:
            True if private configs are missing, False otherwise
        """
        private_settings_exists = os.path.exists(self.private_settings_file)
        private_mappings_path = os.path.join(self.config_dir, 'private_mappings.toml')
        private_mappings_exists = os.path.exists(private_mappings_path)

        return not (private_settings_exists and private_mappings_exists)

    def get_privacy_settings(self) -> Dict:
        """
        Get privacy settings from merged configuration.

        Returns:
            Privacy settings dictionary
        """
        return self.settings.get('privacy', {})


# Global instance for easy access
_config_manager = None


def get_config_manager(config_dir: str = None) -> ConfigManager:
    """
    Get global configuration manager instance.
    
    Args:
        config_dir: Configuration directory path
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None or config_dir is not None:
        _config_manager = ConfigManager(config_dir)
    
    return _config_manager


def get_enrichment_config() -> Dict[str, str]:
    """Convenience function to get enrichment file paths."""
    return get_config_manager().get_enrichment_files()


def validate_config() -> Tuple[bool, List[str], List[str]]:
    """
    Validate configuration completeness.
    
    Returns:
        Tuple of (is_valid, missing_required, missing_optional)
    """
    config = get_config_manager()
    missing_required = []
    missing_optional = []
    
    # Check required files
    required_files = ['statement_patterns', 'plaid_categories']
    for file_key in required_files:
        file_path = config.get_file_path(file_key)
        if not os.path.exists(file_path):
            missing_required.append(file_key)
    
    # Check optional files
    optional_files = ['private_mappings', 'public_mappings']
    for file_key in optional_files:
        file_path = config.get_file_path(file_key)
        if not os.path.exists(file_path):
            missing_optional.append(file_key)
    
    is_valid = len(missing_required) == 0
    return is_valid, missing_required, missing_optional


if __name__ == "__main__":
    """Test the configuration manager."""
    print("=== Configuration Manager Test ===")

    config = get_config_manager()

    print(f"Config directory: {config.config_dir}")
    print(f"Public settings file: {config.public_settings_file}")
    print(f"Private settings file: {config.private_settings_file}")
    print(f"First run: {config.check_first_run()}")
    
    print("\nDirectories:")
    for key in ['statements', 'output', 'config']:
        path = config.get_directory_path(key)
        exists = "✓" if os.path.exists(path) else "✗"
        print(f"  {key}: {path} {exists}")
    
    print("\nConfiguration files:")
    for file_path in config.get_all_config_files():
        exists = "✓" if os.path.exists(file_path) else "✗"
        filename = os.path.basename(file_path)
        print(f"  {filename}: {file_path} {exists}")
    
    print("\nDefault output files:")
    for key in ['parsed_transactions', 'enriched_transactions']:
        path = config.get_default_file_path(key)
        print(f"  {key}: {path}")
    
    print("\nThresholds:")
    print(f"  Enrichment fuzzy matching: {config.get_fuzzy_threshold('enrichment')}")
    print(f"  High confidence: {config.get_confidence_threshold('high_confidence')}")
    print(f"  Medium confidence: {config.get_confidence_threshold('medium_confidence')}")
    
    print("\nValidation:")
    is_valid, missing_required, missing_optional = validate_config()
    print(f"  Configuration valid: {is_valid}")
    if missing_required:
        print(f"  Missing required files: {missing_required}")
    if missing_optional:
        print(f"  Missing optional files: {missing_optional}")
    
    print("\n=== Test Complete ===")