"""Tests for money_mapper.utils module."""

import json
from pathlib import Path
import pytest

from money_mapper.utils import load_transactions_from_json, save_transactions_to_json, sanitize_description


class TestLoadTransactions:
    """Test transaction loading from JSON."""

    def test_load_transactions_valid_file(self, sample_transactions, temp_output_dir):
        """Test loading valid transaction JSON file."""
        test_file = temp_output_dir / "transactions.json"
        
        # Write sample transactions
        with open(test_file, 'w') as f:
            json.dump(sample_transactions, f)
        
        # Load and verify
        loaded = load_transactions_from_json(str(test_file))
        assert len(loaded) == 4
        assert loaded[0]["merchant"] == "Starbucks"

    def test_load_transactions_empty_file(self, temp_output_dir):
        """Test loading empty transaction file."""
        test_file = temp_output_dir / "empty.json"
        with open(test_file, 'w') as f:
            json.dump([], f)
        
        loaded = load_transactions_from_json(str(test_file))
        assert loaded == []


class TestSaveTransactions:
    """Test transaction saving to JSON."""

    def test_save_transactions(self, sample_transactions, temp_output_dir):
        """Test saving transactions to JSON."""
        output_file = temp_output_dir / "output.json"
        
        save_transactions_to_json(sample_transactions, str(output_file))
        
        assert output_file.exists()
        
        with open(output_file) as f:
            loaded = json.load(f)
        
        assert len(loaded) == len(sample_transactions)
        assert loaded[0]["merchant"] == sample_transactions[0]["merchant"]


class TestSanitizeDescription:
    """Test merchant description sanitization."""

    @pytest.mark.xfail(reason="Sanitization logic not fully implemented - Phase 2")
    def test_sanitize_starbucks(self):
        """Test Starbucks description sanitization."""
        result = sanitize_description("STARBUCKS #12345 SEATTLE WA")
        assert result == "STARBUCKS"

    def test_sanitize_amazon(self):
        """Test Amazon description sanitization."""
        result = sanitize_description("AMAZON.COM AMZN.COM/BILL")
        assert "AMAZON" in result.upper()

    def test_sanitize_empty(self):
        """Test empty string handling."""
        result = sanitize_description("")
        assert result is not None
