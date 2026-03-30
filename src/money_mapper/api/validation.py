"""Validation and sanitization helpers for the Money Mapper web API.

Provides CSV injection prevention, merchant name validation, and PFC category
validation with fuzzy suggestions. Designed for reuse across route handlers.
"""

import csv
import io


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
