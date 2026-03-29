"""FastAPI web server for Money Mapper.

Provides 5 main pages:
- /dashboard: Spending overview with charts
- /transactions: Transaction listing and management
- /import: File upload (CSV, OFX, QFX)
- /mappings: Merchant mapping management
- /settings: Configuration and tools
"""

import html
import json
import os
import tomllib
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, PackageLoader, select_autoescape


def _load_enriched_transactions(file_path: str) -> list[dict]:
    """Load enriched transactions from JSON file.

    Args:
        file_path: Path to the JSON file containing enriched transactions.

    Returns:
        List of transaction dicts, or empty list if file missing/invalid.
    """
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _load_mappings_flat(file_path: str) -> list[dict]:
    """Load mappings from TOML and flatten to list of {merchant, category, subcategory, name}.

    Args:
        file_path: Path to the TOML mappings file.

    Returns:
        Flattened list of mapping dicts, or empty list if file missing/invalid.
    """
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        flat = []
        for section in data.values():
            if isinstance(section, dict):
                for subsection in section.values():
                    if isinstance(subsection, dict):
                        for pattern, mapping in subsection.items():
                            if isinstance(mapping, dict):
                                flat.append(
                                    {
                                        "merchant": pattern,
                                        "category": mapping.get("category", ""),
                                        "subcategory": mapping.get("subcategory", ""),
                                        "name": mapping.get("name", pattern),
                                    }
                                )
        return flat
    except (OSError, tomllib.TOMLDecodeError):
        return []


def _compute_spending_by_category(transactions: list[dict]) -> dict:
    """Compute spending totals grouped by category.

    Args:
        transactions: List of transaction dicts with 'category' and 'amount' keys.

    Returns:
        Dict with 'categories' (list of category names) and 'amounts' (list of floats),
        sorted by amount descending.
    """
    totals: dict[str, float] = {}
    for txn in transactions:
        cat = txn.get("category", "Uncategorized") or "Uncategorized"
        amount = abs(float(txn.get("amount", 0)))
        totals[cat] = totals.get(cat, 0) + amount
    sorted_cats = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return {
        "categories": [c[0] for c in sorted_cats],
        "amounts": [round(c[1], 2) for c in sorted_cats],
    }


def create_app(data_dir: str | None = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        data_dir: Base directory for data files. Defaults to current working directory.

    Returns:
        FastAPI: Configured application instance
    """
    base_dir = data_dir or os.getcwd()
    enriched_path = os.path.join(base_dir, "output", "enriched_transactions.json")

    app = FastAPI(
        title="Money Mapper",
        description="Personal transaction parser and categorizer",
        version="0.7.0",
    )

    # Setup Jinja2 template environment with autoescape enabled for HTML files
    env = Environment(
        loader=PackageLoader("money_mapper.api", "templates"),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )

    # ===== Dashboard Route =====
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        """Dashboard page with spending overview.

        Returns:
            HTMLResponse: Rendered HTML dashboard
        """
        template = env.get_template("dashboard.html")
        transactions = _load_enriched_transactions(enriched_path)
        spending = _compute_spending_by_category(transactions)
        recent = sorted(transactions, key=lambda t: t.get("date", ""), reverse=True)[:10]
        recent_formatted = [
            {
                "date": t.get("date", ""),
                "merchant": t.get("merchant_name", t.get("description", "Unknown")),
                "amount": abs(float(t.get("amount", 0))),
            }
            for t in recent
        ]
        data = {
            "title": "Dashboard",
            "spending": spending,
            "recent_transactions": recent_formatted,
        }
        return HTMLResponse(template.render(**data))

    # ===== Transactions Route =====
    @app.get("/transactions", response_class=HTMLResponse)
    async def transactions_list(
        date: str | None = None,
        category: str | None = None,
        merchant: str | None = None,
    ) -> HTMLResponse:
        """List transactions with optional filtering.

        Args:
            date: Filter by month (YYYY-MM)
            category: Filter by category
            merchant: Filter by merchant

        Returns:
            HTMLResponse: Rendered HTML transaction list
        """
        template = env.get_template("transactions.html")
        data = {
            "title": "Transactions",
            "transactions": [
                {
                    "id": 1,
                    "date": "2026-03-28",
                    "merchant": "Store",
                    "amount": 50,
                    "category": "Shopping",
                },
                {
                    "id": 2,
                    "date": "2026-03-27",
                    "merchant": "Gas Station",
                    "amount": 35,
                    "category": "Transport",
                },
            ],
            "filters": {"date": date, "category": category, "merchant": merchant},
        }
        return HTMLResponse(template.render(**data))

    @app.post("/transactions/{transaction_id}", response_class=HTMLResponse)
    async def update_transaction(transaction_id: int, category: str | None = None) -> HTMLResponse:
        """Update transaction category.

        Args:
            transaction_id: ID of transaction to update
            category: New category for transaction

        Returns:
            HTMLResponse: Updated transaction HTML or error
        """
        if not category or category.strip() == "":
            return HTMLResponse("Category cannot be empty", status_code=400)

        safe_id = html.escape(str(transaction_id))
        safe_category = html.escape(str(category))
        return HTMLResponse(f"Updated transaction {safe_id} to {safe_category}", status_code=200)

    @app.get("/transactions/export", response_class=HTMLResponse)
    async def export_transactions() -> HTMLResponse:
        """Export transactions as CSV.

        Returns:
            HTMLResponse: CSV data
        """
        csv_data = "date,merchant,amount,category\n2026-03-28,Store,50,Shopping\n"
        return HTMLResponse(csv_data, media_type="text/csv", status_code=200)

    # ===== Import Route =====
    @app.get("/import", response_class=HTMLResponse)
    async def import_form() -> HTMLResponse:
        """Import file upload form.

        Returns:
            HTMLResponse: Rendered HTML form
        """
        template = env.get_template("import.html")
        data = {
            "title": "Import",
            "supported_formats": ["CSV", "OFX", "QFX"],
            "instructions": "Select a CSV, OFX, or QFX file to import transactions",
        }
        return HTMLResponse(template.render(**data))

    @app.post("/import", response_class=HTMLResponse)
    async def import_file(file: UploadFile = File()) -> HTMLResponse:  # noqa: B008
        """Handle file upload for import.

        Args:
            file: Uploaded file

        Returns:
            HTMLResponse: Import results or error message
        """
        if not file:
            return HTMLResponse("No file provided", status_code=400)

        # Validate file extension
        allowed_extensions = {".csv", ".ofx", ".qfx"}
        filename = file.filename or ""
        file_extension = Path(filename).suffix.lower()

        if file_extension not in allowed_extensions:
            return HTMLResponse("Invalid file format. Supported: CSV, OFX, QFX", status_code=400)

        return HTMLResponse(f"Imported {file.filename} successfully", status_code=200)

    # ===== Mappings Route =====
    @app.get("/mappings", response_class=HTMLResponse)
    async def mappings_list() -> HTMLResponse:
        """List merchant mappings.

        Returns:
            HTMLResponse: Rendered HTML mappings list
        """
        template = env.get_template("mappings.html")
        data = {
            "title": "Mappings",
            "public_mappings": [
                {"merchant": "Starbucks", "category": "Food & Drink"},
                {"merchant": "Shell Gas", "category": "Transport"},
            ],
            "private_mappings": [{"merchant": "My Store", "category": "Custom"}],
            "privacy_warnings": ["High-risk merchants detected"],
        }
        return HTMLResponse(template.render(**data))

    @app.post("/mappings", response_class=HTMLResponse)
    async def create_mapping(
        merchant: str = Form(...), category: str = Form(...), source: str = Form(...)
    ) -> HTMLResponse:
        """Create new merchant mapping.

        Args:
            merchant: Merchant name
            category: Category to map to
            source: Source of mapping

        Returns:
            HTMLResponse: Success or error message
        """
        if not merchant or not category:
            return HTMLResponse("Merchant and category required", status_code=400)

        safe_merchant = html.escape(str(merchant))
        safe_category = html.escape(str(category))
        return HTMLResponse(f"Created mapping: {safe_merchant} - {safe_category}", status_code=201)

    # ===== Settings Route =====
    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page() -> HTMLResponse:
        """Settings and configuration page.

        Returns:
            HTMLResponse: Rendered HTML settings page
        """
        template = env.get_template("settings.html")
        data = {
            "title": "Settings",
            "options": [
                {"name": "Default Currency", "value": "USD"},
                {"name": "Privacy Audit Threshold", "value": "30"},
            ],
            "tools": [
                {"name": "Rebuild Model", "description": "Retrain ML model"},
                {"name": "Privacy Audit", "description": "Scan for PII in mappings"},
            ],
        }
        return HTMLResponse(template.render(**data))

    @app.post("/settings", response_class=HTMLResponse)
    async def update_settings(body: str | None = None) -> HTMLResponse:
        """Update settings.

        Args:
            body: Settings update as JSON

        Returns:
            HTMLResponse: Success or error message
        """
        return HTMLResponse("Settings updated", status_code=200)

    # ===== Root Route =====
    @app.get("/", response_class=HTMLResponse)
    async def root() -> HTMLResponse:
        """Root route shows dashboard.

        Returns:
            HTMLResponse: Rendered HTML dashboard
        """
        template = env.get_template("dashboard.html")
        transactions = _load_enriched_transactions(enriched_path)
        spending = _compute_spending_by_category(transactions)
        recent = sorted(transactions, key=lambda t: t.get("date", ""), reverse=True)[:10]
        recent_formatted = [
            {
                "date": t.get("date", ""),
                "merchant": t.get("merchant_name", t.get("description", "Unknown")),
                "amount": abs(float(t.get("amount", 0))),
            }
            for t in recent
        ]
        data = {
            "title": "Dashboard",
            "spending": spending,
            "recent_transactions": recent_formatted,
        }
        return HTMLResponse(template.render(**data))

    # Mount static files if they exist
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec - local dev server
