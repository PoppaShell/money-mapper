"""Shared pytest configuration and fixtures for Money Mapper tests."""

import json
import os
from pathlib import Path
import pytest
import tempfile
import toml


@pytest.fixture
def test_data_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_transactions(test_data_dir):
    """Load sample transactions from fixture."""
    fixture_file = test_data_dir / "sample_transactions.json"
    if fixture_file.exists():
        with open(fixture_file) as f:
            return json.load(f)
    return []


@pytest.fixture
def sample_mappings(test_data_dir):
    """Load sample mappings from fixture."""
    fixture_file = test_data_dir / "sample_mappings.toml"
    if fixture_file.exists():
        return toml.load(open(fixture_file))
    return {}


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_checking(test_data_dir):
    """Path to sample checking account CSV."""
    return test_data_dir / "sample_statements" / "checking_2024_01.csv"


@pytest.fixture
def sample_csv_credit(test_data_dir):
    """Path to sample credit card CSV."""
    return test_data_dir / "sample_statements" / "credit_2024_01.csv"
