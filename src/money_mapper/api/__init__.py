"""Web API module for Money Mapper.

Provides FastAPI web interface with 5 pages:
- Dashboard: Overview of spending
- Transactions: Transaction listing and categorization
- Import: File upload and parsing
- Mappings: Merchant mapping management
- Settings: Configuration and tools
"""

from money_mapper.api.server import create_app

__all__ = ["create_app"]
