"""Validation and sanitization helpers for the Money Mapper web API.

Provides CSV injection prevention, merchant name validation, and PFC category
validation with fuzzy suggestions. Designed for reuse across route handlers.
"""


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
