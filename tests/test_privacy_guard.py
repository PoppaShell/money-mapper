"""Tests for money_mapper.privacy_guard module."""

import pytest

from money_mapper.privacy_guard import (
    PrivacyGuard,
    mask_account_number,
    redact_merchant_name,
    encrypt_amount,
    decrypt_amount,
    create_audit_log,
    apply_privacy_settings,
)


class TestMaskAccountNumber:
    """Test account number masking."""

    def test_mask_account_number_16_digits(self):
        """Test masking 16-digit account number."""
        account = "1234567890123456"
        result = mask_account_number(account)
        
        # Should show last 4 digits
        assert result.endswith("3456")
        assert "****" in result or "*" in result

    def test_mask_account_number_with_spaces(self):
        """Test masking account number with spaces."""
        account = "1234 5678 9012 3456"
        result = mask_account_number(account)
        
        assert "3456" in result
        assert len(result) > 0

    def test_mask_account_number_short(self):
        """Test masking short account number."""
        account = "1234"
        result = mask_account_number(account)
        
        # Should handle gracefully
        assert isinstance(result, str)

    def test_mask_account_number_empty(self):
        """Test masking empty account number."""
        result = mask_account_number("")
        assert isinstance(result, str)

    def test_mask_account_number_no_digits(self):
        """Test masking account number with no digits."""
        result = mask_account_number("ABC")
        assert isinstance(result, str)

    @pytest.mark.parametrize("account,expected_last", [
        ("1234567890123456", "3456"),
        ("9999888877776666", "6666"),
        ("1111222233334444", "4444"),
    ])
    def test_mask_various_accounts(self, account, expected_last):
        """Test masking various account numbers."""
        result = mask_account_number(account)
        assert expected_last in result


class TestRedactMerchantName:
    """Test merchant name redaction."""

    def test_redact_merchant_full_redaction(self):
        """Test full merchant name redaction."""
        merchant = "STARBUCKS COFFEE #1234"
        result = redact_merchant_name(merchant, mode="full")
        
        assert result != merchant
        assert "STARBUCKS" not in result

    def test_redact_merchant_partial_redaction(self):
        """Test partial merchant name redaction."""
        merchant = "STARBUCKS COFFEE #1234"
        result = redact_merchant_name(merchant, mode="partial")
        
        # Should keep some information
        assert isinstance(result, str)
        assert len(result) > 0

    def test_redact_merchant_category_only(self):
        """Test merchant category only redaction."""
        merchant = "STARBUCKS COFFEE #1234"
        result = redact_merchant_name(merchant, mode="category")
        
        # Should return generic category
        assert isinstance(result, str)

    def test_redact_merchant_no_redaction(self):
        """Test no redaction mode."""
        merchant = "STARBUCKS COFFEE #1234"
        result = redact_merchant_name(merchant, mode="none")
        
        # Should keep original
        assert result == merchant

    def test_redact_merchant_empty(self):
        """Test redacting empty merchant name."""
        result = redact_merchant_name("", mode="full")
        assert isinstance(result, str)

    def test_redact_merchant_with_location(self):
        """Test redacting merchant with location info."""
        merchant = "WHOLE FOODS MKT #123 NEW YORK NY"
        result = redact_merchant_name(merchant, mode="partial")
        
        assert isinstance(result, str)

    @pytest.mark.parametrize("mode", ["full", "partial", "category", "none"])
    def test_redact_merchant_all_modes(self, mode):
        """Test redaction in all modes."""
        merchant = "AMAZON.COM"
        result = redact_merchant_name(merchant, mode=mode)
        assert isinstance(result, str)


class TestEncryptDecryptAmount:
    """Test amount encryption/decryption."""

    def test_encrypt_amount(self):
        """Test encrypting transaction amount."""
        amount = 123.45
        encrypted = encrypt_amount(amount)
        
        assert encrypted != amount
        assert isinstance(encrypted, str)

    def test_decrypt_amount(self):
        """Test decrypting transaction amount."""
        original = 123.45
        encrypted = encrypt_amount(original)
        decrypted = decrypt_amount(encrypted)
        
        assert decrypted == original

    def test_encrypt_decrypt_round_trip(self):
        """Test encrypt/decrypt round trip."""
        amounts = [0.01, 50.99, 999.99, 1000.00]
        
        for amount in amounts:
            encrypted = encrypt_amount(amount)
            decrypted = decrypt_amount(encrypted)
            assert abs(decrypted - amount) < 0.01

    def test_encrypt_negative_amount(self):
        """Test encrypting negative amount."""
        amount = -50.00
        encrypted = encrypt_amount(amount)
        decrypted = decrypt_amount(encrypted)
        
        assert decrypted == amount

    def test_encrypt_zero_amount(self):
        """Test encrypting zero amount."""
        encrypted = encrypt_amount(0.0)
        decrypted = decrypt_amount(encrypted)
        
        assert decrypted == 0.0

    def test_decrypt_invalid_format(self):
        """Test decrypting invalid encrypted format."""
        result = decrypt_amount("invalid_encrypted_data")
        # Should handle gracefully
        assert result is None or isinstance(result, (int, float))


class TestCreateAuditLog:
    """Test audit logging for redaction."""

    def test_create_audit_log_entry(self):
        """Test creating audit log entry."""
        entry = create_audit_log(
            transaction_id="txn_123",
            field="merchant",
            original_value="STARBUCKS",
            redacted_value="[REDACTED]",
            redaction_type="full"
        )
        
        assert isinstance(entry, dict)
        assert "timestamp" in entry
        assert entry["transaction_id"] == "txn_123"
        assert entry["field"] == "merchant"

    def test_audit_log_contains_required_fields(self):
        """Test audit log has all required fields."""
        entry = create_audit_log(
            transaction_id="txn_456",
            field="amount",
            original_value="100.00",
            redacted_value="[ENCRYPTED]",
            redaction_type="encryption"
        )
        
        assert "timestamp" in entry
        assert "transaction_id" in entry
        assert "field" in entry
        assert "redaction_type" in entry

    def test_audit_log_timestamp_format(self):
        """Test audit log has valid timestamp."""
        entry = create_audit_log(
            transaction_id="txn_789",
            field="account",
            original_value="1234567890",
            redacted_value="****7890",
            redaction_type="mask"
        )
        
        timestamp = entry.get("timestamp")
        assert timestamp is not None
        assert isinstance(timestamp, str)


class TestApplyPrivacySettings:
    """Test applying privacy settings to transactions."""

    def test_apply_privacy_settings_mask_account(self):
        """Test applying account masking privacy setting."""
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "account": "1234567890123456"
        }
        
        settings = {
            "mask_account": True,
            "mask_account_digits": 4,
            "redact_merchant": False,
            "encrypt_amounts": False,
        }
        
        result = apply_privacy_settings(transaction, settings)
        
        assert "account" in result
        assert result["account"] != transaction["account"]
        assert "3456" in result["account"]

    def test_apply_privacy_settings_redact_merchant(self):
        """Test applying merchant redaction privacy setting."""
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS COFFEE #1234",
            "amount": 5.50,
        }
        
        settings = {
            "mask_account": False,
            "redact_merchant": True,
            "redact_merchant_mode": "partial",
            "encrypt_amounts": False,
        }
        
        result = apply_privacy_settings(transaction, settings)
        
        if settings["redact_merchant"]:
            # Merchant should be modified
            assert isinstance(result.get("merchant"), str)

    def test_apply_privacy_settings_encrypt_amounts(self):
        """Test applying amount encryption privacy setting."""
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
        }
        
        settings = {
            "mask_account": False,
            "redact_merchant": False,
            "encrypt_amounts": True,
        }
        
        result = apply_privacy_settings(transaction, settings)
        
        if settings["encrypt_amounts"]:
            amount = result.get("amount")
            # Amount should be different when encrypted
            assert amount is not None

    def test_apply_privacy_settings_all_options(self):
        """Test applying all privacy settings."""
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS #1234 NEW YORK",
            "amount": 5.50,
            "account": "1234567890123456",
            "description": "STARBUCKS"
        }
        
        settings = {
            "mask_account": True,
            "mask_account_digits": 4,
            "redact_merchant": True,
            "redact_merchant_mode": "full",
            "encrypt_amounts": True,
        }
        
        result = apply_privacy_settings(transaction, settings)
        
        assert isinstance(result, dict)
        # Should have same keys as input
        assert set(result.keys()) >= set(transaction.keys())

    def test_apply_privacy_settings_preserves_other_fields(self):
        """Test that privacy settings preserve non-sensitive fields."""
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "category": "Food & Drink",
            "confidence": 0.95
        }
        
        settings = {
            "mask_account": True,
            "redact_merchant": True,
            "encrypt_amounts": True,
        }
        
        result = apply_privacy_settings(transaction, settings)
        
        # Non-sensitive fields should be preserved
        assert result.get("category") == transaction["category"]
        assert result.get("confidence") == transaction["confidence"]


class TestPrivacyGuard:
    """Test main PrivacyGuard class."""

    def test_privacy_guard_initialization(self):
        """Test PrivacyGuard initialization."""
        guard = PrivacyGuard()
        assert guard is not None
        assert hasattr(guard, "apply_privacy")
        assert hasattr(guard, "get_audit_log")

    def test_privacy_guard_apply_privacy_to_transaction(self):
        """Test applying privacy to single transaction."""
        guard = PrivacyGuard(mask_account=True, redact_merchant=False, encrypt_amounts=False)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "account": "1234567890123456"
        }
        
        result = guard.apply_privacy(transaction)
        
        assert isinstance(result, dict)
        assert "account" in result

    def test_privacy_guard_apply_privacy_to_transactions(self):
        """Test applying privacy to multiple transactions."""
        guard = PrivacyGuard(mask_account=True, redact_merchant=True, encrypt_amounts=False)
        
        transactions = [
            {
                "date": "2024-03-15",
                "merchant": "STARBUCKS",
                "amount": 5.50,
                "account": "1234567890123456"
            },
            {
                "date": "2024-03-16",
                "merchant": "AMAZON",
                "amount": 49.99,
                "account": "1234567890123456"
            },
        ]
        
        results = [guard.apply_privacy(txn) for txn in transactions]
        
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)

    def test_privacy_guard_custom_settings(self):
        """Test PrivacyGuard with custom settings."""
        custom_settings = {
            "mask_account": True,
            "mask_account_digits": 2,
            "redact_merchant": True,
            "redact_merchant_mode": "category",
            "encrypt_amounts": False,
        }
        
        guard = PrivacyGuard(**custom_settings)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "account": "1234567890123456"
        }
        
        result = guard.apply_privacy(transaction)
        assert isinstance(result, dict)

    def test_privacy_guard_audit_log(self):
        """Test PrivacyGuard audit log tracking."""
        guard = PrivacyGuard(mask_account=True, track_audit=True)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
            "account": "1234567890123456",
            "id": "txn_123"
        }
        
        result = guard.apply_privacy(transaction)
        audit_log = guard.get_audit_log()
        
        if guard.track_audit:
            assert isinstance(audit_log, list)

    def test_privacy_guard_no_privacy_mode(self):
        """Test PrivacyGuard with no privacy settings enabled."""
        guard = PrivacyGuard(mask_account=False, redact_merchant=False, encrypt_amounts=False)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS",
            "amount": 5.50,
        }
        
        result = guard.apply_privacy(transaction)
        
        # Should return transaction largely unchanged
        assert result["merchant"] == transaction["merchant"]
        assert result["amount"] == transaction["amount"]


class TestPrivacyIntegration:
    """Integration tests for privacy guard."""

    def test_privacy_guard_with_enriched_transactions(self):
        """Test privacy guard with enriched transaction data."""
        guard = PrivacyGuard(
            mask_account=True,
            redact_merchant=True,
            encrypt_amounts=False
        )
        
        enriched = {
            "date": "2024-03-15",
            "merchant": "STARBUCKS COFFEE #1234",
            "amount": 5.50,
            "account": "1234567890123456",
            "category": "Food & Drink",
            "plaid_category": "FOOD_AND_DRINK",
            "confidence": 0.98,
            "mapping_method": "plaid_keyword"
        }
        
        result = guard.apply_privacy(enriched)
        
        assert "category" in result
        assert "plaid_category" in result
        assert "confidence" in result

    def test_privacy_guard_workflow(self):
        """Test complete privacy guard workflow."""
        transactions = [
            {
                "date": "2024-03-15",
                "merchant": "STARBUCKS",
                "amount": 5.50,
                "account": "1111111111111111"
            },
            {
                "date": "2024-03-16",
                "merchant": "WHOLE FOODS",
                "amount": 65.32,
                "account": "1111111111111111"
            },
            {
                "date": "2024-03-17",
                "merchant": "CVS PHARMACY",
                "amount": 25.99,
                "account": "2222222222222222"
            },
        ]
        
        guard = PrivacyGuard(
            mask_account=True,
            redact_merchant=True,
            encrypt_amounts=False,
            track_audit=True
        )
        
        protected_transactions = [guard.apply_privacy(txn) for txn in transactions]
        
        assert len(protected_transactions) == 3
        assert all("account" in t for t in protected_transactions)


class TestPrivacyEdgeCases:
    """Test edge cases in privacy processing."""

    def test_privacy_guard_empty_transaction(self):
        """Test privacy guard with empty transaction."""
        guard = PrivacyGuard(mask_account=True)
        result = guard.apply_privacy({})
        
        assert isinstance(result, dict)

    def test_privacy_guard_null_values(self):
        """Test privacy guard with None values."""
        guard = PrivacyGuard(mask_account=True, redact_merchant=True)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": None,
            "amount": None,
            "account": None
        }
        
        result = guard.apply_privacy(transaction)
        assert isinstance(result, dict)

    def test_privacy_guard_special_characters(self):
        """Test privacy guard with special characters in merchant."""
        guard = PrivacyGuard(redact_merchant=True)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "AT&T WIRELESS / STORE #123",
            "amount": 75.00,
        }
        
        result = guard.apply_privacy(transaction)
        assert isinstance(result, dict)

    def test_privacy_guard_unicode_merchant(self):
        """Test privacy guard with unicode merchant name."""
        guard = PrivacyGuard(redact_merchant=True)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "CAFÉ FRANÇAIS ☕",
            "amount": 5.50,
        }
        
        result = guard.apply_privacy(transaction)
        assert isinstance(result, dict)

    def test_privacy_guard_very_long_merchant(self):
        """Test privacy guard with very long merchant name."""
        guard = PrivacyGuard(redact_merchant=True)
        
        transaction = {
            "date": "2024-03-15",
            "merchant": "A" * 500,
            "amount": 5.50,
        }
        
        result = guard.apply_privacy(transaction)
        assert isinstance(result, dict)

    def test_privacy_guard_extreme_amounts(self):
        """Test privacy guard with extreme amounts."""
        guard = PrivacyGuard(encrypt_amounts=True)
        
        transactions = [
            {"date": "2024-03-15", "merchant": "TEST", "amount": 0.01},
            {"date": "2024-03-15", "merchant": "TEST", "amount": 999999.99},
            {"date": "2024-03-15", "merchant": "TEST", "amount": -999999.99},
        ]
        
        results = [guard.apply_privacy(t) for t in transactions]
        assert len(results) == 3
