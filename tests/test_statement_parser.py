"""Tests for money_mapper.statement_parser module."""

import pytest

from money_mapper.statement_parser import normalize_whitespace


class TestNormalizeWhitespace:
    """Test whitespace normalization."""

    def test_multiple_spaces(self):
        """Test normalizing multiple spaces."""
        result = normalize_whitespace("STARBUCKS    COFFEE")
        assert result == "STARBUCKS COFFEE"

    def test_leading_trailing_spaces(self):
        """Test removing leading/trailing spaces."""
        result = normalize_whitespace("  AMAZON  ")
        assert result == "AMAZON"

    def test_mixed_whitespace(self):
        """Test handling mixed whitespace."""
        result = normalize_whitespace("  WHOLE   FOODS  MKT  ")
        assert result == "WHOLE FOODS MKT"

    def test_no_whitespace_changes(self):
        """Test string with normal spacing."""
        result = normalize_whitespace("NORMAL SPACING")
        assert result == "NORMAL SPACING"
