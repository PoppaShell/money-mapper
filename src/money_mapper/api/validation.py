"""Validation and sanitization helpers for the Money Mapper web API.

Provides CSV injection prevention, merchant name validation, and PFC category
validation with fuzzy suggestions. Designed for reuse across route handlers.
"""

import csv
import difflib
import html
import io
import tomllib


def sanitize_csv_value(value: str) -> str:
    """Sanitize a value for safe CSV export per OWASP guidelines.

    Prefixes values starting with =, +, @, or - (non-numeric) with a tab
    character to prevent spreadsheet formula injection.

    Args:
        value: Raw string value to sanitize.

    Returns:
        Sanitized string safe for CSV inclusion.
    """
    if not value:
        return value
    first = value[0]
    if first in ("=", "+", "@"):
        return "\t" + value
    if first == "-":
        rest = value[1:]
        if not rest or not (rest[0].isdigit() or rest[0] == "."):
            return "\t" + value
    return value


def build_csv_export(transactions: list[dict]) -> str:
    """Build CSV string from transactions with injection protection.

    Uses Python's csv module for proper quoting and applies OWASP
    sanitization to merchant and category fields.

    Args:
        transactions: List of transaction dicts with date, merchant_name,
            amount, and category keys.

    Returns:
        Complete CSV string with header row.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "merchant", "amount", "category"])
    for t in transactions:
        merchant = t.get("merchant_name", t.get("description", ""))
        category = t.get("category", "")
        writer.writerow(
            [
                t.get("date", ""),
                sanitize_csv_value(str(merchant)),
                t.get("amount", 0),
                sanitize_csv_value(str(category)),
            ]
        )
    return output.getvalue()


def validate_merchant_name(merchant: str) -> tuple[bool, str]:
    """Validate and clean a merchant name.

    Strips control characters, trims whitespace, enforces length limit.

    Args:
        merchant: Raw merchant name string.

    Returns:
        (True, cleaned_name) on success, or (False, error_message) on failure.
    """
    # Strip control characters (below 0x20) except space (0x20)
    cleaned = "".join(c for c in merchant if ord(c) >= 32)
    cleaned = cleaned.strip()

    if not cleaned:
        return (False, "Merchant name cannot be empty")

    if len(cleaned) > 200:
        return (False, "Merchant name exceeds 200 character limit")

    return (True, cleaned)


def validate_pfc_category(category: str, plaid_path: str) -> tuple[bool, list[str]]:
    """Validate a category against the Plaid PFC taxonomy.

    Checks for exact match (case-insensitive) against subcategory names
    from plaid_categories.toml. On failure, suggests up to 3 close matches.

    Args:
        category: Category string to validate.
        plaid_path: Path to plaid_categories.toml file.

    Returns:
        (True, []) on valid match, or (False, suggestions) on failure.
    """
    if not category or not category.strip():
        return (False, [])

    try:
        with open(plaid_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return (False, [])

    # Collect all subcategory names (the DETAILED part of PRIMARY.DETAILED keys)
    subcategories = []
    for primary_key, primary_val in data.items():
        if isinstance(primary_val, dict):
            for detailed_key in primary_val:
                subcategories.append(detailed_key)

    # Case-insensitive exact match
    category_upper = category.strip().upper()
    if category_upper in (s.upper() for s in subcategories):
        return (True, [])

    # Fuzzy match for suggestions
    suggestions = difflib.get_close_matches(
        category_upper, [s.upper() for s in subcategories], n=3, cutoff=0.4
    )
    return (False, suggestions)


def format_warnings_html(warnings: list[str]) -> str:
    """Format a list of warning strings as an HTML warning block.

    Produces a div with class "warning" containing an unordered list of
    escaped warning messages. Returns empty string if no warnings.

    Args:
        warnings: List of warning message strings.

    Returns:
        HTML string with warning block, or empty string.
    """
    if not warnings:
        return ""
    items = "".join(f"<li>{html.escape(w)}</li>" for w in warnings)
    return f'<div class="warning"><strong>Warnings:</strong><ul>{items}</ul></div>'
