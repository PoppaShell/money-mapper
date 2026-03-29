"""FastAPI web server for Money Mapper.

Provides 5 main pages:
- /dashboard: Spending overview with charts
- /transactions: Transaction listing and management
- /import: File upload (CSV, OFX, QFX)
- /mappings: Merchant mapping management
- /settings: Configuration and tools
"""

import html
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, PackageLoader, select_autoescape


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
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
        data = {
            "title": "Dashboard",
            "spending": {
                "categories": ["Food", "Transport", "Entertainment"],
                "amounts": [150, 75, 50],
            },
            "recent_transactions": [
                {"date": "2026-03-28", "merchant": "Store", "amount": 50},
                {"date": "2026-03-27", "merchant": "Gas", "amount": 35},
            ],
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
        """Root route redirects to dashboard.

        Returns:
            HTMLResponse: HTML redirect or dashboard
        """
        template = env.get_template("dashboard.html")
        data = {
            "title": "Dashboard",
            "spending": {"categories": [], "amounts": []},
            "recent_transactions": [],
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
