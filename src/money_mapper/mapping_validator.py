#!/usr/bin/env python3
"""
Mapping Validator - Validate financial transaction mappings.

This module provides functionality to validate mapping structure, fields, and categories
to ensure data integrity and consistency across the mapping files.
"""

import os
from typing import Any

# PFC Taxonomy categories (extracted from mapping_processor.py)
VALID_CATEGORIES = {
    "BANK_FEES",
    "ENTERTAINMENT",
    "FOOD_AND_DRINK",
    "GENERAL_MERCHANDISE",
    "GENERAL_SERVICES",
    "GOVERNMENT_AND_NON_PROFIT",
    "HOME_IMPROVEMENT",
    "INCOME",
    "MEDICAL",
    "PERSONAL_SERVICES",
    "PERSONAL_TAX",
    "RENT_AND_UTILITIES",
    "SHOPPING",
    "TRANSFER",
    "TRANSPORTATION",
    "UNCATEGORIZED",
    "UNKNOWN",
}

VALID_SUBCATEGORIES = {
    "BANK_FEES_ATM_FEES",
    "BANK_FEES_FOREIGN_TRANSACTION_FEES",
    "BANK_FEES_INSUFFICIENT_FUNDS",
    "BANK_FEES_INTEREST_CHARGE",
    "BANK_FEES_OVERDRAFT_FEES",
    "BANK_FEES_OTHER_BANK_FEES",
    "ENTERTAINMENT_CASINOS_AND_GAMBLING",
    "ENTERTAINMENT_MUSIC_AND_AUDIO",
    "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS",
    "ENTERTAINMENT_TV_AND_MOVIES",
    "ENTERTAINMENT_VIDEO_GAMES",
    "ENTERTAINMENT_OTHER_ENTERTAINMENT",
    "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR",
    "FOOD_AND_DRINK_COFFEE",
    "FOOD_AND_DRINK_FAST_FOOD",
    "FOOD_AND_DRINK_GROCERIES",
    "FOOD_AND_DRINK_RESTAURANT",
    "FOOD_AND_DRINK_VENDING_MACHINES",
    "FOOD_AND_DRINK_OTHER_FOOD_AND_DRINK",
    "INCOME_DIVIDENDS",
    "INCOME_INTEREST_EARNED",
    "INCOME_RETIREMENT_PENSION",
    "INCOME_TAX_REFUND",
    "INCOME_UNEMPLOYMENT",
    "INCOME_WAGES",
    "INCOME_OTHER_INCOME",
    "TRANSPORTATION_GAS",
    "TRANSPORTATION_PARKING",
    "TRANSPORTATION_PUBLIC_TRANSIT",
    "TRANSPORTATION_TAXI",
    "TRANSPORTATION_TOLLS",
    "TRANSPORTATION_OTHER_TRANSPORTATION",
    "SHOPPING_GENERAL",
    "SHOPPING_ONLINE",
    "SHOPPING_DRUGSTORE",
    "SHOPPING_ELECTRONICS",
    "GENERAL_MERCHANDISE_BOOKSTORES_AND_NEWSSTANDS",
    "GENERAL_MERCHANDISE_CLOTHING_AND_ACCESSORIES",
    "GENERAL_MERCHANDISE_CONVENIENCE_STORES",
    "GENERAL_MERCHANDISE_DEPARTMENT_STORES",
    "GENERAL_MERCHANDISE_DISCOUNT_STORES",
    "GENERAL_MERCHANDISE_ELECTRONICS",
    "GENERAL_MERCHANDISE_GIFTS_AND_NOVELTIES",
    "GENERAL_MERCHANDISE_OFFICE_SUPPLIES",
    "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES",
    "GENERAL_MERCHANDISE_PET_SUPPLIES",
    "GENERAL_MERCHANDISE_SPORTING_GOODS",
    "GENERAL_MERCHANDISE_SUPERSTORES",
    "GENERAL_MERCHANDISE_TOBACCO_AND_VAPE",
    "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE",
}

VALID_SCOPES = {"public", "private"}


def validate_mappings(mappings: dict[str, Any]) -> list[str]:
    """
    Validate all mappings in a structure.

    Args:
        mappings: Dictionary of mappings organized by section

    Returns:
        List of validation issues found
    """
    issues = []

    if not isinstance(mappings, dict):
        issues.append("Mappings must be a dictionary")
        return issues

    for section, section_mappings in mappings.items():
        if not isinstance(section_mappings, dict):
            continue

        for pattern, mapping in section_mappings.items():
            pattern_issues = validate_single_mapping(pattern, mapping)
            issues.extend(pattern_issues)

    return issues


def validate_single_mapping(pattern: str, mapping: Any) -> list[str]:
    """
    Validate a single mapping entry.

    Args:
        pattern: The pattern key for the mapping
        mapping: The mapping entry to validate

    Returns:
        List of validation issues found
    """
    issues = []

    if not isinstance(mapping, dict):
        issues.append(f"Mapping for pattern '{pattern}' must be a dictionary")
        return issues

    # Check required fields
    required_fields = ["name", "category", "subcategory", "scope"]
    for field in required_fields:
        if field not in mapping:
            issues.append(f"Mapping '{pattern}' missing required field: {field}")

    # Check field values
    if "category" in mapping:
        category = mapping["category"]
        if category and category not in VALID_CATEGORIES:
            issues.append(f"Mapping '{pattern}' has invalid category: {category}")

    if "subcategory" in mapping:
        subcategory = mapping["subcategory"]
        if subcategory and subcategory not in VALID_SUBCATEGORIES:
            issues.append(f"Mapping '{pattern}' has invalid subcategory: {subcategory}")

    if "scope" in mapping:
        scope = mapping["scope"]
        if scope and scope not in VALID_SCOPES:
            issues.append(
                f"Mapping '{pattern}' has invalid scope: {scope} (must be 'public' or 'private')"
            )

    return issues


def validate_mapping_structure(mappings: Any) -> list[str]:
    """
    Validate the structure of mappings.

    Args:
        mappings: The mappings to validate

    Returns:
        List of structural validation issues
    """
    issues = []

    if not isinstance(mappings, dict):
        issues.append("Root mappings must be a dictionary")
        return issues

    for section, section_mappings in mappings.items():
        if not isinstance(section_mappings, dict):
            issues.append(f"Section '{section}' must contain a dictionary of mappings")
            continue

        for pattern, mapping in section_mappings.items():
            if not isinstance(mapping, dict):
                issues.append(
                    f"Mapping for pattern '{pattern}' in section '{section}' must be a dictionary"
                )

    return issues


def check_required_files(private_file: str, public_file: str) -> bool:
    """
    Check that required mapping files exist.

    Args:
        private_file: Path to private mappings file
        public_file: Path to public mappings file

    Returns:
        True if both files exist, False otherwise
    """
    private_exists = os.path.exists(private_file)
    public_exists = os.path.exists(public_file)

    return private_exists and public_exists


def validate_categories_consistency(
    mappings: dict[str, Any], category_taxonomy: dict[str, set[str]] | None = None
) -> list[str]:
    """
    Validate that categories and subcategories are consistent.

    Args:
        mappings: Dictionary of mappings
        category_taxonomy: Optional taxonomy for validation

    Returns:
        List of consistency issues
    """
    issues = []

    if not isinstance(mappings, dict):
        return issues

    for section, section_mappings in mappings.items():
        if not isinstance(section_mappings, dict):
            continue

        for pattern, mapping in section_mappings.items():
            if not isinstance(mapping, dict):
                continue

            category = mapping.get("category")
            subcategory = mapping.get("subcategory")

            # Check that subcategory starts with category
            if category and subcategory:
                if not subcategory.startswith(category + "_"):
                    issues.append(
                        f"Mapping '{pattern}': subcategory '{subcategory}' should start with '{category}_'"
                    )

    return issues
