#!/usr/bin/env python3
"""
Interactive Mapping Builder - Guide users through creating merchant mappings.

This module provides an interactive workflow to help users create mappings
for uncategorized transactions. It analyzes transaction frequency, suggests
keywords and names, and provides guided category selection through numbered menus.

Uses the official Plaid Personal Finance Category (PFC) taxonomy with 16 PRIMARY
categories and 104 DETAILED subcategories.
"""

import re
import os
import sys
import csv
from typing import Dict, List, Tuple, Optional
from collections import Counter

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import get_config_manager
from utils import load_config, prompt_yes_no, prompt_with_validation
from mapping_processor import MappingProcessor


def get_transaction_frequency(transactions: List[Dict]) -> Dict[str, int]:
    """
    Count occurrences of each unique transaction description.

    Args:
        transactions: List of transaction dictionaries

    Returns:
        Dictionary mapping description to occurrence count, sorted by frequency
    """
    descriptions = [t.get('description', '') for t in transactions if t.get('description')]
    frequency = Counter(descriptions)

    # Return as sorted dict (most common first)
    return dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))


def suggest_keyword(description: str) -> str:
    """
    Generate a suggested keyword from transaction description.

    Removes numbers, special characters, common suffixes, and converts to lowercase.

    Args:
        description: Original transaction description

    Returns:
        Suggested keyword (lowercase, cleaned)

    Examples:
        "LOCAL COFFEE SHOP DOWNTOWN #123" -> "local coffee shop downtown"
        "WALMART SUPERCENTER #4567" -> "walmart supercenter"
        "STARBUCKS STORE 12345" -> "starbucks store"
    """
    # Convert to lowercase
    keyword = description.lower()

    # Remove common suffixes and patterns
    patterns_to_remove = [
        r'\s*#\d+',          # Store numbers like #123
        r'\s*store\s+\d+',   # "store 1234"
        r'\s*\d{3,}',        # Any 3+ digit numbers
        r'\s*-\s*\d+',       # Dash numbers like -123
    ]

    for pattern in patterns_to_remove:
        keyword = re.sub(pattern, '', keyword, flags=re.IGNORECASE)

    # Remove special characters (keep letters, spaces, apostrophes, hyphens)
    keyword = re.sub(r'[^a-z\s\'\-]', '', keyword)

    # Clean up multiple spaces
    keyword = re.sub(r'\s+', ' ', keyword).strip()

    return keyword


def suggest_name(description: str) -> str:
    """
    Generate a suggested clean name from transaction description.

    Converts to title case and removes extraneous details.

    Args:
        description: Original transaction description

    Returns:
        Suggested clean name (title case)

    Examples:
        "LOCAL COFFEE SHOP" -> "Local Coffee Shop"
        "WALMART SUPERCENTER #4567" -> "Walmart Supercenter"
        "TARGET STORE #1234" -> "Target"
    """
    # Start with the keyword (already cleaned)
    name = suggest_keyword(description)

    # Remove common redundant words
    redundant = ['store', 'location', 'branch']
    words = name.split()
    words = [w for w in words if w.lower() not in redundant]
    name = ' '.join(words)

    # Convert to title case
    name = name.title()

    return name


def load_category_taxonomy() -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, str]]:
    """
    Load category taxonomy and descriptions from official Plaid PFC CSV file.

    Returns:
        Tuple of:
        - Dictionary mapping PRIMARY categories to list of DETAILED subcategories
        - Dictionary mapping DETAILED categories to their descriptions
        - Dictionary mapping PRIMARY categories to their descriptions

    Example:
        taxonomy = {
            'FOOD_AND_DRINK': [
                'FOOD_AND_DRINK_COFFEE',
                'FOOD_AND_DRINK_RESTAURANT',
                ...
            ],
            ...
        }
        detailed_descriptions = {
            'FOOD_AND_DRINK_COFFEE': 'Purchases at coffee shops or cafes',
            ...
        }
        primary_descriptions = {
            'FOOD_AND_DRINK': 'Food and beverage purchases',
            ...
        }
    """
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'claude',
                            'transactions-personal-finance-category-taxonomy.csv')

    taxonomy = {}
    detailed_descriptions = {}
    primary_descriptions = {}

    # Manual PRIMARY category descriptions (Plaid CSV only has DETAILED descriptions)
    primary_desc_map = {
        'BANK_FEES': 'Banking fees and charges',
        'ENTERTAINMENT': 'Recreation and entertainment',
        'FOOD_AND_DRINK': 'Food and beverage purchases',
        'GENERAL_MERCHANDISE': 'Retail and merchandise',
        'GENERAL_SERVICES': 'Professional and personal services',
        'GOVERNMENT_AND_NON_PROFIT': 'Government, taxes, and donations',
        'HOME_IMPROVEMENT': 'Home and garden',
        'INCOME': 'Income and earnings',
        'LOAN_PAYMENTS': 'Debt payments and loans',
        'MEDICAL': 'Healthcare and medical',
        'PERSONAL_CARE': 'Personal care and wellness',
        'RENT_AND_UTILITIES': 'Housing and utilities',
        'TRANSFER_IN': 'Incoming transfers and deposits',
        'TRANSFER_OUT': 'Outgoing transfers and withdrawals',
        'TRANSPORTATION': 'Transportation and automotive',
        'TRAVEL': 'Travel and lodging'
    }

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                primary = row['PRIMARY']
                detailed = row['DETAILED']
                description = row.get('DESCRIPTION', '')

                if primary not in taxonomy:
                    taxonomy[primary] = []
                    primary_descriptions[primary] = primary_desc_map.get(primary, '')

                taxonomy[primary].append(detailed)
                detailed_descriptions[detailed] = description

    except FileNotFoundError:
        # Fallback to loading from plaid_categories.toml if CSV not found
        print("Warning: Plaid CSV not found, falling back to plaid_categories.toml")
        plaid = load_config('config/plaid_categories.toml')

        for full_category in plaid.keys():
            if '.' in full_category:
                primary, detailed = full_category.split('.', 1)
                if primary not in taxonomy:
                    taxonomy[primary] = []
                    primary_descriptions[primary] = primary_desc_map.get(primary, '')
                taxonomy[primary].append(full_category)  # Use full name
                detailed_descriptions[full_category] = ''  # No description available

    return taxonomy, detailed_descriptions, primary_descriptions


def display_category_menu(taxonomy: Dict[str, List[str]], primary_descriptions: Dict[str, str]) -> Optional[str]:
    """
    Display PRIMARY category menu and get user selection.

    Args:
        taxonomy: Category taxonomy dictionary
        primary_descriptions: Dictionary mapping PRIMARY categories to descriptions

    Returns:
        Selected PRIMARY category, or None if cancelled
    """
    print("\nSelect PRIMARY category:")

    categories = sorted(taxonomy.keys())
    for i, category in enumerate(categories, 1):
        desc = primary_descriptions.get(category, '')
        if desc:
            print(f"  {i:2}. {category:<25} - {desc}")
        else:
            print(f"  {i:2}. {category}")

    while True:
        try:
            choice = input("\nEnter number (or 'q' to cancel): ").strip()
            if choice.lower() == 'q':
                return None

            num = int(choice)
            if 1 <= num <= len(categories):
                return categories[num - 1]
            else:
                print(f"Please enter a number between 1 and {len(categories)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def display_subcategory_menu(primary: str, taxonomy: Dict[str, List[str]], descriptions: Dict[str, str]) -> Optional[str]:
    """
    Display DETAILED subcategory menu for a PRIMARY category and get user selection.

    Args:
        primary: PRIMARY category name
        taxonomy: Category taxonomy dictionary
        descriptions: Dictionary mapping DETAILED categories to descriptions

    Returns:
        Selected DETAILED subcategory (full name like FOOD_AND_DRINK_COFFEE), or None if cancelled
    """
    subcategories = sorted(taxonomy.get(primary, []))

    if not subcategories:
        print(f"\nNo subcategories found for {primary}")
        return None

    print(f"\nSelect {primary} subcategory:")

    for i, subcategory in enumerate(subcategories, 1):
        # Remove PRIMARY_ prefix for cleaner display but keep format
        if subcategory.startswith(primary + '_'):
            display_name = subcategory[len(primary) + 1:]  # Remove "PRIMARY_" prefix
        else:
            display_name = subcategory

        # Get description
        desc = descriptions.get(subcategory, '')
        if desc:
            # Truncate long descriptions to fit nicely
            if len(desc) > 45:
                desc = desc[:42] + '...'
            print(f"  {i:2}. {display_name:<35} - {desc}")
        else:
            print(f"  {i:2}. {display_name}")

    while True:
        try:
            choice = input("\nEnter number (or 'q' to go back): ").strip()
            if choice.lower() == 'q':
                return None

            num = int(choice)
            if 1 <= num <= len(subcategories):
                return subcategories[num - 1]
            else:
                print(f"Please enter a number between 1 and {len(subcategories)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def display_scope_menu() -> Optional[str]:
    """
    Display scope selection menu and get user choice.

    Returns:
        'public' or 'private', or None if cancelled
    """
    print("\nSelect scope:")
    print("  1. public  - National/regional chain (shareable)")
    print("  2. private - Local business or personal (kept private)")

    while True:
        choice = input("\nEnter number (or 'q' to go back): ").strip()
        if choice.lower() == 'q':
            return None

        if choice == '1':
            return 'public'
        elif choice == '2':
            return 'private'
        else:
            print("Please enter 1 or 2")


def create_mapping_entry(
    keyword: str,
    name: str,
    primary: str,
    detailed: str,
    scope: str,
    processor: MappingProcessor,
    debug: bool = False
) -> bool:
    """
    Create and save a new mapping entry to new_mappings.toml.

    Args:
        keyword: Keyword to match transactions
        name: Clean merchant name
        primary: PRIMARY category
        detailed: DETAILED subcategory (full name like FOOD_AND_DRINK_COFFEE)
        scope: 'public' or 'private'
        processor: MappingProcessor instance
        debug: Enable debug output

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create mapping in the simple flat format used by new_mappings.toml
        mapping_value = {
            "name": name,
            "category": primary,
            "subcategory": detailed,
            "scope": scope
        }

        # Get path to new_mappings.toml
        file_path = processor.new_mappings_file

        # Load current entries (if file exists and has content)
        current_entries = {}
        if os.path.exists(file_path):
            try:
                current_entries = load_config(file_path)
            except Exception:
                # File might be empty or just comments, that's ok
                pass

        # Add new mapping
        current_entries[keyword] = mapping_value

        # Write back to file, preserving the header
        import toml

        # Read the header from the file
        header_lines = []
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.strip().startswith('[') and not line.strip().startswith('"'):
                        header_lines.append(line.rstrip())
                    else:
                        break  # Stop at first non-comment/non-blank line

        # Write header + entries
        with open(file_path, 'w') as f:
            # Write header
            if header_lines:
                f.write('\n'.join(header_lines))
                f.write('\n\n')

            # Write entries
            toml.dump(current_entries, f)

        if debug:
            print(f"\nDEBUG: Added mapping to {file_path}")
            print(f"  \"{keyword}\" = {mapping_value}")

        return True

    except Exception as e:
        print(f"\nError creating mapping: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False


def run_mapping_wizard(
    uncategorized_transactions: List[Dict],
    config_dir: str = 'config',
    debug: bool = False
) -> int:
    """
    Interactive workflow to build mappings for uncategorized transactions.

    Args:
        uncategorized_transactions: List of uncategorized transaction dicts
        config_dir: Configuration directory
        debug: Enable debug output

    Returns:
        Number of mappings created
    """
    if not uncategorized_transactions:
        print("No uncategorized transactions to process.")
        return 0

    # Initialize
    config_manager = get_config_manager(config_dir)
    processor = MappingProcessor(config_dir=config_dir, debug_mode=debug)
    taxonomy, detailed_descriptions, primary_descriptions = load_category_taxonomy()

    # Get frequency analysis - use original_description if available (before privacy redaction)
    # Build a map of descriptions to their original unredacted versions
    description_originals = {}
    for t in uncategorized_transactions:
        redacted_desc = t.get('description', '')
        original_desc = t.get('original_description', redacted_desc)  # Fallback to redacted if no original
        if redacted_desc and original_desc:
            description_originals[redacted_desc] = original_desc

    frequency = get_transaction_frequency(uncategorized_transactions)
    top_transactions = list(frequency.items())[:25]  # Top 25

    print(f"\n--- Interactive Mapping Builder ---")
    print(f"Found {len(top_transactions)} unique uncategorized merchant(s) to process\n")

    mappings_created = 0
    skipped = 0

    for idx, (description, count) in enumerate(top_transactions, 1):
        # Use original unredacted description (fallback to redacted if unavailable)
        original_desc = description_originals.get(description, description)

        print(f"\n{'='*70}")
        print(f"[{idx}/{len(top_transactions)}] Transaction: \"{original_desc}\"")
        print(f"Occurrences: {count} transaction(s)")
        print(f"{'='*70}")

        # Ask if user wants to create a mapping for this transaction
        action = prompt_with_validation(
            "\nCreate mapping for this transaction?",
            valid_options=['y', 'yes', 'n', 'no', 's', 'skip', 'q', 'quit'],
            default='y'
        )

        if action in ['n', 'no']:
            print("Skipping this transaction...")
            skipped += 1
            continue
        elif action in ['s', 'skip']:
            print("Skipping remaining transactions...")
            skipped += (len(top_transactions) - idx + 1)
            break
        elif action in ['q', 'quit']:
            print("Exiting mapping builder...")
            skipped += (len(top_transactions) - idx + 1)
            break

        # Use original description for suggestions (not the redacted one)
        suggested_keyword = suggest_keyword(original_desc)
        suggested_name = suggest_name(original_desc)

        # Mapping creation loop - allows user to go back and change selections
        while True:
            print(f"\nSuggested keyword(s): {suggested_keyword}")
            print(f"Suggested name: {suggested_name}")

            # Get keyword (allow editing)
            keyword_input = input(f"\nEdit keyword(s) [Enter to accept, 'skip' to skip]: ").strip()
            if keyword_input.lower() == 'skip':
                print("Skipping this transaction...")
                skipped += 1
                break
            keyword = keyword_input if keyword_input else suggested_keyword

            # Get name (allow editing)
            name_input = input(f"Edit name [Enter to accept, 'skip' to skip, 'back' to restart]: ").strip()
            if name_input.lower() == 'skip':
                print("Skipping this transaction...")
                skipped += 1
                break
            elif name_input.lower() == 'back':
                print("Restarting mapping for this transaction...")
                continue  # Restart the while loop
            name = name_input if name_input else suggested_name

            # Select PRIMARY category
            primary = display_category_menu(taxonomy, primary_descriptions)
            if not primary:
                print("Cancelled. Restarting...")
                continue  # Restart the while loop

            # Select DETAILED subcategory
            detailed = display_subcategory_menu(primary, taxonomy, detailed_descriptions)
            if not detailed:
                print("Cancelled. Going back to category selection...")
                continue  # Restart the while loop

            # Select scope
            scope = display_scope_menu()
            if not scope:
                print("Cancelled. Going back to category selection...")
                continue  # Restart the while loop

            # Confirm before creating
            print(f"\nReview mapping:")
            print(f"  Keyword: \"{keyword}\"")
            print(f"  Name: \"{name}\"")
            print(f"  Category: {primary}")
            print(f"  Subcategory: {detailed}")
            print(f"  Scope: {scope}")

            confirm = prompt_with_validation(
                "\nCreate this mapping?",
                valid_options=['y', 'yes', 'n', 'no', 'back'],
                default='y'
            )
            if confirm == 'back':
                print("Going back...")
                continue  # Restart the while loop
            elif confirm in ['n', 'no']:
                print("Cancelled. Skipping this transaction...")
                skipped += 1
                break

            # Create the mapping
            success = create_mapping_entry(
                keyword, name, primary, detailed, scope, processor, debug
            )

            if success:
                print(f"\n✓ Added to new_mappings.toml:")
                print(f"  \"{keyword}\" = {{ name = \"{name}\", category = \"{primary}\", subcategory = \"{detailed}\", scope = \"{scope}\" }}")
                mappings_created += 1
            else:
                print("\n✗ Failed to create mapping")
                if prompt_yes_no("Retry?", default=True):
                    continue  # Restart the while loop
                else:
                    skipped += 1

            # Exit the while loop after successful creation or user chooses not to retry
            break

    # Summary
    print(f"\n{'='*70}")
    print(f"Mapping Builder Summary:")
    print(f"  Mappings created: {mappings_created}")
    print(f"  Transactions skipped: {skipped}")
    print(f"  Total processed: {mappings_created + skipped}")
    print(f"{'='*70}")

    # If mappings were created, offer to process them
    if mappings_created > 0:
        print(f"\nNew mappings have been added to new_mappings.toml")
        print("They need to be processed to take effect.")
        print()

        if prompt_yes_no("Would you like to run the mapping processor now?", default=True):
            print("\n" + "="*70)
            print("Running Mapping Processor...")
            print("="*70)

            try:
                success = processor.run_full_processing()
                if success:
                    print("\n✓ Mapping processor completed successfully!")
                    print("Your new mappings are now active.")
                else:
                    print("\n✗ Mapping processor encountered issues.")
                    print("Please check the output above for details.")
            except Exception as e:
                print(f"\nError running mapping processor: {e}")
                if debug:
                    import traceback
                    traceback.print_exc()
        else:
            print("\nYou can process the mappings later by running:")
            print("  python src/cli.py add-mappings")

    return mappings_created


if __name__ == "__main__":
    """Test the interactive mapper with sample data."""
    # Sample uncategorized transactions for testing
    sample_transactions = [
        {"description": "LOCAL COFFEE SHOP DOWNTOWN #123", "amount": -4.50},
        {"description": "LOCAL COFFEE SHOP DOWNTOWN #123", "amount": -5.00},
        {"description": "REGIONAL GROCERY STORE #456", "amount": -45.67},
        {"description": "ABC HARDWARE", "amount": -29.99},
    ]

    print("INTERACTIVE MAPPING BUILDER TEST")
    print("="*70)
    created = run_mapping_wizard(sample_transactions, debug=True)
    print(f"\n\nTest complete. Created {created} mappings.")
