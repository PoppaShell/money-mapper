#!/usr/bin/env python3
"""
Setup Wizard - First-run configuration setup for Money Mapper.

This module provides an interactive setup wizard that runs on first use to help
users configure their private settings and create initial configurations.
"""

import os
import sys
import shutil
import tomllib
import json

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import get_config_manager
from utils import prompt_yes_no


def check_first_run() -> bool:
    """
    Check if this is the first run (private config files missing).

    Returns:
        True if private configs are missing, False otherwise
    """
    config = get_config_manager()
    return config.check_first_run()


def run_setup_wizard(config_dir: str = "config") -> bool:
    """
    Run the interactive setup wizard for first-time configuration.

    Args:
        config_dir: Configuration directory path

    Returns:
        True if setup completed successfully, False otherwise
    """
    print("\n" + "=" * 60)
    print("  Welcome to Money Mapper!")
    print("=" * 60)
    print()
    print("This appears to be your first time running Money Mapper.")
    print("Let's set up your private configuration files.")
    print()

    # Step 1: Create private config files from templates
    if not create_private_configs_from_templates(config_dir):
        print("Error: Failed to create private configuration files.")
        return False

    print("\n✓ Private configuration files created successfully!")

    # Step 2: Configure privacy settings
    print("\n" + "-" * 60)
    print("Privacy Settings Configuration")
    print("-" * 60)
    print()

    if configure_privacy_settings(config_dir):
        print("\n✓ Privacy settings configured successfully!")
    else:
        print("\nPrivacy settings configuration skipped.")

    # Step 3: Check for existing statements
    print("\n" + "-" * 60)
    print("Statement Processing")
    print("-" * 60)
    print()

    stats = check_and_offer_statement_processing(config_dir)

    # Step 4: Setup complete message
    display_setup_complete(config_dir, stats)

    return True


def create_private_configs_from_templates(config_dir: str = "config") -> bool:
    """
    Create private configuration files from templates.

    Args:
        config_dir: Configuration directory path

    Returns:
        True if successful, False otherwise
    """
    templates_dir = os.path.join(config_dir, "templates")

    # Check if templates directory exists
    if not os.path.exists(templates_dir):
        print(f"Error: Templates directory not found: {templates_dir}")
        return False

    # Copy private_settings.toml template
    private_settings_template = os.path.join(templates_dir, "private_settings.toml")
    private_settings_dest = os.path.join(config_dir, "private_settings.toml")

    if not os.path.exists(private_settings_template):
        print(f"Error: Template file not found: {private_settings_template}")
        return False

    if os.path.exists(private_settings_dest):
        print(f"Note: {private_settings_dest} already exists, skipping.")
    else:
        shutil.copy2(private_settings_template, private_settings_dest)
        print(f"Created: {private_settings_dest}")

    # Copy private_mappings.toml template
    private_mappings_template = os.path.join(templates_dir, "private_mappings.toml")
    private_mappings_dest = os.path.join(config_dir, "private_mappings.toml")

    if not os.path.exists(private_mappings_template):
        print(f"Error: Template file not found: {private_mappings_template}")
        return False

    if os.path.exists(private_mappings_dest):
        print(f"Note: {private_mappings_dest} already exists, skipping.")
    else:
        shutil.copy2(private_mappings_template, private_mappings_dest)
        print(f"Created: {private_mappings_dest}")

    return True


def configure_privacy_settings(config_dir: str = "config") -> bool:
    """
    Interactively configure privacy settings.

    Args:
        config_dir: Configuration directory path

    Returns:
        True if settings were configured, False if skipped
    """
    print("Money Mapper can automatically redact personal information from")
    print("transaction descriptions to protect your privacy when sharing or debugging.")
    print()

    if not prompt_yes_no("Would you like to configure privacy redaction now?", default=True):
        print("Skipping privacy configuration. You can configure it later by editing")
        print(f"{config_dir}/private_settings.toml")
        return False

    print()
    print("Enter information to redact (press Enter to skip any section):")
    print()

    # Collect privacy keywords
    names = input("Names to redact (comma-separated): ").strip()
    employers = input("Employer names to redact (comma-separated): ").strip()
    locations = input("Locations to redact (comma-separated): ").strip()
    custom = input("Custom keywords to redact (comma-separated): ").strip()

    print()
    redaction_enabled = prompt_yes_no("Enable redaction?", default=True)

    redaction_mode = input("Redaction mode (exact/fuzzy, default: fuzzy): ").strip().lower()
    if redaction_mode not in ['exact', 'fuzzy']:
        redaction_mode = 'fuzzy'

    threshold_str = input("Fuzzy matching threshold (0.0-1.0, default: 0.85): ").strip()
    try:
        threshold = float(threshold_str) if threshold_str else 0.85
        threshold = max(0.0, min(1.0, threshold))  # Clamp to valid range
    except ValueError:
        threshold = 0.85

    # Save settings
    return save_privacy_settings(
        config_dir,
        names=[n.strip() for n in names.split(',') if n.strip()],
        employers=[e.strip() for e in employers.split(',') if e.strip()],
        locations=[l.strip() for l in locations.split(',') if l.strip()],
        custom=[c.strip() for c in custom.split(',') if c.strip()],
        enable_redaction=redaction_enabled,
        redaction_mode=redaction_mode,
        fuzzy_threshold=threshold
    )


def save_privacy_settings(config_dir: str, names: list, employers: list,
                          locations: list, custom: list, enable_redaction: bool,
                          redaction_mode: str, fuzzy_threshold: float) -> bool:
    """
    Save privacy settings to private_settings.toml.

    Args:
        config_dir: Configuration directory
        names: List of names to redact
        employers: List of employer names to redact
        locations: List of locations to redact
        custom: List of custom keywords to redact
        enable_redaction: Whether to enable redaction
        redaction_mode: Redaction mode ('exact' or 'fuzzy')
        fuzzy_threshold: Fuzzy matching threshold

    Returns:
        True if successful, False otherwise
    """
    import toml  # We need toml for writing (tomllib is read-only)

    private_settings_file = os.path.join(config_dir, "private_settings.toml")

    try:
        # Load existing settings
        with open(private_settings_file, 'rb') as f:
            settings = tomllib.load(f)
    except Exception as e:
        print(f"Warning: Could not load existing settings: {e}")
        settings = {}

    # Update privacy section
    if 'privacy' not in settings:
        settings['privacy'] = {}

    settings['privacy']['enable_redaction'] = enable_redaction
    settings['privacy']['redaction_mode'] = redaction_mode
    settings['privacy']['fuzzy_redaction_threshold'] = fuzzy_threshold

    if 'keywords' not in settings['privacy']:
        settings['privacy']['keywords'] = {}

    settings['privacy']['keywords']['names'] = names
    settings['privacy']['keywords']['employers'] = employers
    settings['privacy']['keywords']['locations'] = locations
    settings['privacy']['keywords']['custom'] = custom

    # Write back to file
    try:
        with open(private_settings_file, 'w') as f:
            toml.dump(settings, f)
        print(f"\n✓ Privacy settings saved to {private_settings_file}")
        return True
    except Exception as e:
        print(f"Error: Could not save privacy settings: {e}")
        return False


def check_and_offer_statement_processing(config_dir: str = "config") -> dict:
    """
    Check for existing statements and offer to process them automatically.

    Args:
        config_dir: Configuration directory path

    Returns:
        Dictionary with processing statistics (num_transactions, categorization_rate)
    """
    config = get_config_manager(config_dir)
    statements_dir = config.get_directory_path('statements')
    stats = {'num_transactions': 0, 'categorization_rate': None}

    if not os.path.exists(statements_dir):
        print(f"No statements directory found at: {statements_dir}")
        print("Create the directory and add PDF statements to get started.")
        return stats

    # Check for PDF files
    pdf_files = [f for f in os.listdir(statements_dir) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"No PDF files found in: {statements_dir}")
        print("Add PDF statements to that directory to get started.")
        return stats

    print(f"Found {len(pdf_files)} PDF file(s) in {statements_dir}")
    print()

    if not prompt_yes_no("Would you like to parse these statements now?", default=True):
        print("\nYou can parse statements later using:")
        print("  python src/cli.py parse --dir statements")
        print("  python src/cli.py enrich")
        print("  python src/cli.py analyze")
        return stats

    # Get file paths from config manager
    parsed_file = config.get_default_file_path('parsed_transactions')
    enriched_file = config.get_default_file_path('enriched_transactions')

    try:
        # Step 1: Parse statements
        print("\n" + "-" * 60)
        print("Parsing Statements")
        print("-" * 60)
        print(f"Parsing statements from '{statements_dir}' directory...")

        from statement_parser import process_pdf_statements
        from utils import save_transactions_to_json

        transactions = process_pdf_statements(statements_dir, debug=False)

        if not transactions:
            print("\n✗ No transactions found in PDF files")
            print("You can try again later with:")
            print("  python src/cli.py parse --dir statements")
            return stats

        # Save transactions
        save_transactions_to_json(transactions, parsed_file)

        num_transactions = len(transactions)
        stats['num_transactions'] = num_transactions

        print(f"✓ Successfully parsed {num_transactions} transaction(s) from {len(pdf_files)} file(s)")
        print(f"  Output: {parsed_file}")

        # Step 2: Enrich transactions
        print("\n" + "-" * 60)
        print("Enriching Transactions")
        print("-" * 60)
        print("Enriching transactions...")

        from transaction_enricher import process_transaction_enrichment
        process_transaction_enrichment(parsed_file, enriched_file, debug=False)

        print(f"✓ Successfully enriched {num_transactions} transaction(s)")
        print(f"  Output: {enriched_file}")

        # Step 3: Show analysis with Interactive Mapping Builder integration
        print("\n" + "-" * 60)
        print("Categorization Analysis")
        print("-" * 60)

        from transaction_enricher import analyze_categorization_accuracy

        # Load enriched transactions to calculate categorization rate
        with open(enriched_file, 'r') as f:
            enriched_transactions = json.load(f)

        categorized = sum(1 for t in enriched_transactions if t.get('category') != 'UNCATEGORIZED')
        if num_transactions > 0:
            stats['categorization_rate'] = (categorized / num_transactions) * 100

        # Run analysis (this includes Interactive Mapping Builder integration)
        analyze_categorization_accuracy(enriched_file, verbose=False, debug=False)

        return stats

    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        print("\nYou can complete parsing later with:")
        print("  python src/cli.py parse --dir statements")
        return stats
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        print("\nYou can try again later with:")
        print("  python src/cli.py parse --dir statements")
        print("  python src/cli.py enrich")
        return stats


def display_setup_complete(config_dir: str = "config", stats: dict = None):
    """
    Display setup complete message with optional processing statistics.

    Args:
        config_dir: Configuration directory path
        stats: Dictionary with processing statistics (num_transactions, categorization_rate)
    """
    print("\n" + "=" * 70)
    print(" " * 24 + "Setup Complete!")
    print("=" * 70)
    print()
    print("Your Money Mapper installation is ready to use!")
    print()

    # Show summary
    print("Summary:")
    print("  ✓ Configuration files created")
    print("  ✓ Privacy settings configured")

    if stats and stats.get('num_transactions', 0) > 0:
        print(f"  ✓ Statements parsed: {stats['num_transactions']} transaction(s)")
        if stats.get('categorization_rate') is not None:
            print(f"  ✓ Categorization rate: {stats['categorization_rate']:.1f}%")

    print()
    print("Configuration files:")
    print(f"  - {config_dir}/private_settings.toml (privacy settings)")
    print(f"  - {config_dir}/private_mappings.toml (personal merchant mappings)")
    print()
    print("These files are gitignored and won't be committed to version control.")
    print()

    # Show next steps
    print("Next steps:")
    if not stats or stats.get('num_transactions', 0) == 0:
        print("  1. Add PDF statements to 'statements/' directory")
        print("  2. Run: python src/cli.py")
        print("  3. Choose option 3 for complete processing pipeline")
    else:
        print("  1. Add new statements to 'statements/' directory")
        print("  2. Run: python src/cli.py")
        print("  3. Choose option 3 to process new statements")

    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    """Test the setup wizard."""
    if check_first_run():
        print("First run detected!")
        run_setup_wizard()
    else:
        print("Private configuration files already exist.")
        print("Setup wizard is not needed.")
