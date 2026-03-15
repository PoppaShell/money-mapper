#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for money-mapper tests.
"""
import os
import sys
import json
import tempfile
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        'date': '2024-01-15',
        'amount': -50.25,
        'description': 'STARBUCKS #1234 COFFEE SHOP',
        'merchant_name': 'Starbucks',
        'category': 'FOOD_AND_DRINK',
        'subcategory': 'FOOD_AND_DRINK_COFFEE',
        'confidence': 0.95,
        'categorization_method': 'private_mapping'
    }


@pytest.fixture
def sample_transactions():
    """Sample list of transactions for testing."""
    return [
        {
            'date': '2024-01-15',
            'amount': -50.25,
            'description': 'STARBUCKS #1234 COFFEE SHOP'
        },
        {
            'date': '2024-01-16',
            'amount': -120.00,
            'description': 'WHOLE FOODS MARKET'
        },
        {
            'date': '2024-01-17',
            'amount': -45.00,
            'description': 'SHELL GAS STATION'
        }
    ]


@pytest.fixture
def sample_config():
    """Sample configuration dictionary."""
    return {
        'plaid_categories': {
            'FOOD_AND_DRINK': {
                'FOOD_AND_DRINK_COFFEE': {
                    'name': 'Coffee Shops',
                    'description': 'Coffee and tea shops'
                }
            },
            'SHOPPING': {
                'SHOPPING_GROCERIES': {
                    'name': 'Groceries',
                    'description': 'Grocery stores'
                }
            },
            'TRANSPORTATION': {
                'TRANSPORTATION_GAS_STATIONS': {
                    'name': 'Gas Stations',
                    'description': 'Gas stations'
                }
            }
        },
        'private_mappings': {
            'FOOD_AND_DRINK': {
                'FOOD_AND_DRINK_COFFEE': {
                    'starbucks*': {'name': 'Starbucks', 'scope': 'private'}
                }
            }
        },
        'public_mappings': {
            'SHOPPING': {
                'SHOPPING_GROCERIES': {
                    'whole foods*': {'name': 'Whole Foods', 'scope': 'public'}
                }
            },
            'TRANSPORTATION': {
                'TRANSPORTATION_GAS_STATIONS': {
                    'shell*': {'name': 'Shell', 'scope': 'public'}
                }
            }
        }
    }


@pytest.fixture
def privacy_config():
    """Sample privacy configuration."""
    return {
        'enabled': True,
        'redact_account_numbers': True,
        'redact_phone_numbers': True,
        'redact_personal_keywords': True,
        'personal_keywords': ['john', 'jane', 'personal', 'home']
    }


@pytest.fixture
def sample_mapping_data():
    """Sample mapping TOML data."""
    return {
        'FOOD_AND_DRINK': {
            'FOOD_AND_DRINK_COFFEE': {
                'starbucks*': {
                    'name': 'Starbucks',
                    'category': 'FOOD_AND_DRINK',
                    'subcategory': 'FOOD_AND_DRINK_COFFEE',
                    'scope': 'public'
                }
            }
        }
    }
