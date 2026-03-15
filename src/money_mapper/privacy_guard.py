#!/usr/bin/env python3
"""
Privacy Guard - Redact and protect sensitive data in transactions.

This module provides functionality to mask account numbers, redact merchant names,
encrypt transaction amounts, and maintain audit logs of redaction operations.
"""

import base64
import hashlib
from datetime import datetime
from typing import Any


def mask_account_number(account: str, visible_digits: int = 4) -> str:
    """
    Mask account number showing only last N digits.

    Args:
        account: Account number to mask
        visible_digits: Number of digits to keep visible (default: 4)

    Returns:
        Masked account number (e.g., "****1234")
    """
    if not account:
        return ""

    # Remove spaces and non-digits
    digits_only = "".join(c for c in account if c.isdigit())

    if len(digits_only) <= visible_digits:
        return "*" * len(digits_only)

    # Show only last N digits, mask the rest
    masked_part = "*" * (len(digits_only) - visible_digits)
    visible_part = digits_only[-visible_digits:]

    return f"{masked_part}{visible_part}"


def redact_merchant_name(merchant: str, mode: str = "partial") -> str:
    """
    Redact merchant name based on privacy mode.

    Args:
        merchant: Merchant name to redact
        mode: Redaction mode ('full', 'partial', 'category', 'none')

    Returns:
        Redacted merchant name
    """
    if not merchant:
        return ""

    if mode == "none":
        return merchant

    if mode == "full":
        # Complete redaction
        return "[REDACTED]"

    elif mode == "partial":
        # Keep first word, redact rest
        words = merchant.split()
        if len(words) > 1:
            return f"{words[0]} [...]"
        return merchant

    elif mode == "category":
        # Return generic category placeholder
        return "[MERCHANT]"

    return merchant


def encrypt_amount(amount: float) -> str:
    """
    Encrypt transaction amount using simple encoding.

    Args:
        amount: Transaction amount to encrypt

    Returns:
        Encrypted amount as string
    """
    # Convert to string with 2 decimal places
    amount_str = f"{amount:.2f}"

    # Encode to bytes
    encoded = amount_str.encode("utf-8")

    # Base64 encode for reversibility
    encrypted = base64.b64encode(encoded).decode("utf-8")

    return encrypted


def decrypt_amount(encrypted: str) -> float | None:
    """
    Decrypt transaction amount.

    Args:
        encrypted: Encrypted amount string

    Returns:
        Decrypted amount or None if invalid
    """
    try:
        # Base64 decode
        decoded = base64.b64decode(encrypted.encode("utf-8")).decode("utf-8")

        # Convert back to float
        return float(decoded)
    except (ValueError, TypeError, Exception):
        return None


def create_audit_log(
    transaction_id: str,
    field: str,
    original_value: Any,
    redacted_value: Any,
    redaction_type: str
) -> dict[str, Any]:
    """
    Create audit log entry for redaction operation.

    Args:
        transaction_id: ID of transaction being redacted
        field: Field that was redacted
        original_value: Original value before redaction
        redacted_value: Redacted value
        redaction_type: Type of redaction (mask, redact, encrypt)

    Returns:
        Audit log entry dictionary
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "transaction_id": transaction_id,
        "field": field,
        "original_value_hash": hashlib.sha256(str(original_value).encode()).hexdigest()[:16],
        "redaction_type": redaction_type,
        "redacted_value_type": type(redacted_value).__name__,
    }


def apply_privacy_settings(
    transaction: dict[str, Any],
    settings: dict[str, Any]
) -> dict[str, Any]:
    """
    Apply privacy settings to a transaction.

    Args:
        transaction: Transaction dictionary
        settings: Privacy settings dictionary

    Returns:
        Transaction with privacy settings applied
    """
    # Create a copy to avoid modifying original
    protected = transaction.copy()

    # Apply account masking
    if settings.get("mask_account", False) and "account" in protected:
        visible_digits = settings.get("mask_account_digits", 4)
        protected["account"] = mask_account_number(
            str(protected["account"]),
            visible_digits=visible_digits
        )

    # Apply merchant redaction
    if settings.get("redact_merchant", False) and "merchant" in protected:
        mode = settings.get("redact_merchant_mode", "partial")
        protected["merchant"] = redact_merchant_name(str(protected["merchant"]), mode=mode)

    # Apply amount encryption
    if settings.get("encrypt_amounts", False) and "amount" in protected:
        if isinstance(protected["amount"], (int, float)):
            protected["amount"] = encrypt_amount(float(protected["amount"]))

    return protected


class PrivacyGuard:
    """Main privacy guard class for protecting sensitive transaction data."""

    def __init__(
        self,
        mask_account: bool = False,
        mask_account_digits: int = 4,
        redact_merchant: bool = False,
        redact_merchant_mode: str = "partial",
        encrypt_amounts: bool = False,
        track_audit: bool = False,
    ):
        """
        Initialize privacy guard with settings.

        Args:
            mask_account: Whether to mask account numbers
            mask_account_digits: Number of digits to keep visible
            redact_merchant: Whether to redact merchant names
            redact_merchant_mode: Mode for merchant redaction
            encrypt_amounts: Whether to encrypt transaction amounts
            track_audit: Whether to track audit logs
        """
        self.mask_account = mask_account
        self.mask_account_digits = mask_account_digits
        self.redact_merchant = redact_merchant
        self.redact_merchant_mode = redact_merchant_mode
        self.encrypt_amounts = encrypt_amounts
        self.track_audit = track_audit
        self.audit_log: list[dict[str, Any]] = []

    def apply_privacy(self, transaction: dict[str, Any]) -> dict[str, Any]:
        """
        Apply privacy settings to transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Protected transaction
        """
        settings = {
            "mask_account": self.mask_account,
            "mask_account_digits": self.mask_account_digits,
            "redact_merchant": self.redact_merchant,
            "redact_merchant_mode": self.redact_merchant_mode,
            "encrypt_amounts": self.encrypt_amounts,
        }

        protected = apply_privacy_settings(transaction, settings)

        # Track audit log if enabled
        if self.track_audit and transaction.get("id"):
            self._track_changes(transaction, protected)

        return protected

    def _track_changes(
        self, original: dict[str, Any], protected: dict[str, Any]
    ) -> None:
        """
        Track changes for audit log.

        Args:
            original: Original transaction
            protected: Protected transaction
        """
        transaction_id = original.get("id", "unknown")

        for field in ["account", "merchant", "amount"]:
            if field in original and original[field] != protected.get(field):
                entry = create_audit_log(
                    transaction_id=transaction_id,
                    field=field,
                    original_value=original[field],
                    redacted_value=protected.get(field),
                    redaction_type=self._get_redaction_type(field)
                )
                self.audit_log.append(entry)

    def _get_redaction_type(self, field: str) -> str:
        """
        Determine redaction type for field.

        Args:
            field: Field name

        Returns:
            Redaction type
        """
        if field == "account":
            return "mask"
        elif field == "merchant":
            return "redact"
        elif field == "amount":
            return "encrypt"
        return "unknown"

    def get_audit_log(self) -> list[dict[str, Any]]:
        """
        Get audit log entries.

        Returns:
            List of audit log entries
        """
        return self.audit_log.copy()

    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self.audit_log.clear()
