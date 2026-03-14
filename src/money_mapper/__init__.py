"""Money Mapper - Financial transaction parser and categorizer.

Extract and categorize transactions from bank statements using the
Plaid Personal Finance Category (PFC) taxonomy.
"""

__version__ = "0.6.0"
__author__ = "PoppaShell"

from money_mapper.cli import main

__all__ = ["main"]
