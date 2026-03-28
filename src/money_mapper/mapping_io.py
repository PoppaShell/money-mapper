"""Mapping I/O operations - Load, save, and backup mapping files.

Handles all file I/O operations for mapping files including:
- Loading public mappings from TOML
- Loading private mappings from JSON
- Saving mappings to files
- Creating backups of mapping files
"""

import json
import shutil
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

import toml


def load_public_mappings(mapping_file: str | None = None) -> dict[str, Any] | None:
    """
    Load public mappings from TOML file.

    Args:
        mapping_file: Path to public_mappings.toml (default: config/public_settings.toml)

    Returns:
        Dict with mappings, or None if file not found/invalid
    """
    if mapping_file is None:
        mapping_file = "config/public_settings.toml"

    try:
        file_path = Path(mapping_file)
        if not file_path.exists():
            return None

        with open(file_path, "rb") as f:
            mappings = tomllib.load(f)

        if not mappings:
            return None

        return mappings

    except Exception:
        return None


def load_private_mappings(mapping_file: str | None = None) -> list[Any] | dict[str, Any] | None:
    """
    Load private mappings from JSON file.

    Args:
        mapping_file: Path to mappings JSON file (default: data/enriched_transactions.json)

    Returns:
        List/dict with mappings, or None if file not found/invalid
    """
    if mapping_file is None:
        mapping_file = "data/enriched_transactions.json"

    try:
        file_path = Path(mapping_file)
        if not file_path.exists():
            return None

        with open(file_path) as f:
            content = f.read()
            if not content.strip():
                return None

            mappings = json.loads(content)

        if not mappings:
            return None

        return mappings

    except (json.JSONDecodeError, ValueError):
        return None
    except Exception:
        return None


def save_mappings(
    mappings: dict[str, Any] | list[Any], output_file: str
) -> str | None:
    """
    Save mappings to file (TOML or JSON based on extension).

    Args:
        mappings: Mapping data to save
        output_file: Path to output file

    Returns:
        Path to saved file, or None if save failed
    """
    try:
        output_path = Path(output_file)

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save based on file extension
        if output_file.endswith(".toml"):
            with open(output_path, "w") as f:
                toml.dump(mappings, f)
        elif output_file.endswith(".json"):
            with open(output_path, "w") as f:
                json.dump(mappings, f, indent=2)
        else:
            # Default to JSON if no extension match
            with open(output_path, "w") as f:
                json.dump(mappings, f, indent=2)

        return str(output_path)

    except Exception:
        return None


def backup_mappings(mapping_file: str) -> str | None:
    """
    Create timestamped backup of mapping file.

    Args:
        mapping_file: Path to file to backup

    Returns:
        Path to backup file, or None if backup failed
    """
    try:
        file_path = Path(mapping_file)
        if not file_path.exists():
            return None

        # Create backups directory if needed
        backup_dir = file_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_filename

        # Copy file
        shutil.copy2(file_path, backup_path)

        return str(backup_path)

    except Exception:
        return None
