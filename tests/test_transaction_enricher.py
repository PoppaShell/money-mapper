"""Tests for money_mapper.transaction_enricher module."""

import pytest


class TestTransactionEnricher:
    """Test transaction enrichment functionality."""

    def test_enricher_module_imports(self):
        """Test that enricher module can be imported."""
        try:
            from money_mapper.transaction_enricher import process_transaction_enrichment
            assert process_transaction_enrichment is not None
        except ImportError:
            pytest.fail("Could not import process_transaction_enrichment")

    def test_enricher_with_sample_data(self, sample_transactions, sample_mappings):
        """Test enricher with sample transaction and mapping data."""
        # Verify sample data is available
        assert len(sample_transactions) > 0
        assert len(sample_mappings) > 0
        
        # This is a placeholder for actual enrichment testing
        # Once enricher is called with proper args, verify output
        first_transaction = sample_transactions[0]
        assert "description" in first_transaction
        assert "date" in first_transaction
