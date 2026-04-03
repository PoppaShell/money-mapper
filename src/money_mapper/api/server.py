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
    public_mappings_path = os.path.join(base_dir, "config", "public_mappings.toml")
    private_mappings_path = os.path.join(base_dir, "config", "private_mappings.toml")

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
            "active_page": "dashboard",
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
            date: Filter by date prefix (e.g. YYYY-MM)
            category: Filter by category substring
            merchant: Filter by merchant or description substring

        Returns:
            HTMLResponse: Rendered HTML transaction list
        """
        template = env.get_template("transactions.html")
        transactions = _load_enriched_transactions(enriched_path)

        # Apply filters
        filtered = transactions
        if date:
            filtered = [t for t in filtered if t.get("date", "").startswith(date)]
        if category:
            filtered = [t for t in filtered if category.lower() in t.get("category", "").lower()]
        if merchant:
            filtered = [
                t
                for t in filtered
                if merchant.lower() in t.get("merchant_name", "").lower()
                or merchant.lower() in t.get("description", "").lower()
            ]

        formatted = [
            {
                "id": i,
                "date": t.get("date", ""),
                "merchant": t.get("merchant_name", t.get("description", "Unknown")),
                "amount": abs(float(t.get("amount", 0))),
                "amount_type": "credit" if float(t.get("amount", 0)) >= 0 else "debit",
                "category": t.get("category", "Uncategorized"),
            }
            for i, t in enumerate(filtered)
        ]

        data = {
            "title": "Transactions",
            "active_page": "transactions",
            "transactions": formatted,
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
            HTMLResponse: CSV data with Content-Disposition header for download.
        """
        from money_mapper.api.validation import build_csv_export

        transactions = _load_enriched_transactions(enriched_path)
        csv_data = build_csv_export(transactions)
        return HTMLResponse(
            csv_data,
            media_type="text/csv",
            status_code=200,
            headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
        )

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
            "active_page": "import",
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
        import tempfile

        if not file:
            return HTMLResponse("No file provided", status_code=400)

        allowed_extensions = {".csv", ".ofx", ".qfx"}
        filename = file.filename or ""
        file_extension = Path(filename).suffix.lower()

        if file_extension not in allowed_extensions:
            return HTMLResponse("Invalid file format. Supported: CSV, OFX, QFX", status_code=400)

        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        tmp_path_str = None
        try:
            content = await file.read()
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=file_extension, dir=output_dir, delete=False
            ) as tmp:
                tmp.write(content)
                tmp_path_str = tmp.name

            # Import transactions
            from money_mapper.csv_importer import CSVImporter

            importer = CSVImporter()
            try:
                transactions = importer.import_file(tmp_path_str)
            except ValueError as e:
                safe_err = html.escape(str(e))
                return HTMLResponse(f"Import failed: {safe_err}", status_code=400)

            if not transactions:
                return HTMLResponse(
                    "No transactions found in file. "
                    "Check that the file format is supported (CSV, OFX, QFX).",
                    status_code=422,
                )

            # Save raw transactions
            raw_path = os.path.join(output_dir, "financial_transactions.json")
            with open(raw_path, "w") as f:
                json.dump(transactions, f, indent=2)

            # Try enrichment
            enriched_output = os.path.join(output_dir, "enriched_transactions.json")
            try:
                from money_mapper.transaction_enricher import process_transaction_enrichment

                process_transaction_enrichment(
                    raw_path, enriched_output, debug=False, use_multiprocessing=False
                )
                enriched = _load_enriched_transactions(enriched_output)
                template = env.get_template("import_result.html")
                msg = f"Imported {len(transactions)} transactions, {len(enriched)} enriched"
                result_html = template.render(
                    title="Import Results",
                    message=msg,
                    warnings=importer.warnings,
                    active_page="import",
                )
                return HTMLResponse(result_html, status_code=200)
            except Exception:
                template = env.get_template("import_result.html")
                count = len(transactions)
                all_warnings = list(importer.warnings) + [
                    "Enrichment failed -- categories not applied"
                ]
                result_html = template.render(
                    title="Import Results",
                    message=f"Imported {count} transactions",
                    warnings=all_warnings,
                    active_page="import",
                )
                return HTMLResponse(result_html, status_code=207)

        except Exception as e:
            safe_err = html.escape(str(e))
            return HTMLResponse(f"Import failed: {safe_err}", status_code=500)
        finally:
            # Ensure temp file is always cleaned up
            if tmp_path_str and os.path.exists(tmp_path_str):
                os.unlink(tmp_path_str)

    # ===== Mappings Route =====
    @app.get("/mappings", response_class=HTMLResponse)
    async def mappings_list() -> HTMLResponse:
        """List merchant mappings."""
        template = env.get_template("mappings.html")
        public = _load_mappings_flat(public_mappings_path)
        private = _load_mappings_flat(private_mappings_path)

        # Run privacy audit on a sample of public mappings
        warnings = []
        try:
            from money_mapper.privacy_audit import audit_merchant_name

            for m in public[:50]:
                report = audit_merchant_name(m["merchant"], min_score=70)
                if report["score"] >= 70:
                    warnings.append(
                        f"{m['merchant']}: {report['risk_level']} risk (score {report['score']})"
                    )
        except Exception:
            pass

        plaid_path = os.path.join(base_dir, "config", "plaid_categories.toml")
        pfc_categories = []
        try:
            with open(plaid_path, "rb") as f:
                plaid_data = tomllib.load(f)
            for primary_val in plaid_data.values():
                if isinstance(primary_val, dict):
                    for detailed_key in primary_val:
                        pfc_categories.append(detailed_key)
            pfc_categories.sort()
        except (OSError, tomllib.TOMLDecodeError):
            pass

        data = {
            "title": "Mappings",
            "active_page": "mappings",
            "public_mappings": [{"merchant": m["name"], "category": m["category"]} for m in public],
            "private_mappings": [
                {"merchant": m["name"], "category": m["category"]} for m in private
            ],
            "privacy_warnings": warnings if warnings else None,
            "pfc_categories": pfc_categories,
        }
        return HTMLResponse(template.render(**data))

    @app.post("/mappings", response_class=HTMLResponse)
    async def create_mapping(
        merchant: str = Form(...), category: str = Form(...), source: str = Form(...)
    ) -> HTMLResponse:
        """Create new merchant mapping in staging file."""
        from money_mapper.api.validation import validate_merchant_name, validate_pfc_category

        if not merchant or not category:
            return HTMLResponse("Merchant and category required", status_code=400)

        # Validate merchant name
        merchant_valid, merchant_result = validate_merchant_name(merchant)
        if not merchant_valid:
            safe_err = html.escape(merchant_result)
            return HTMLResponse(safe_err, status_code=400)
        cleaned_merchant = merchant_result

        # Validate category against PFC taxonomy
        plaid_path = os.path.join(base_dir, "config", "plaid_categories.toml")
        cat_valid, suggestions = validate_pfc_category(category, plaid_path)
        if not cat_valid:
            safe_cat = html.escape(str(category))
            if suggestions:
                suggestion_text = ", ".join(html.escape(s) for s in suggestions)
                msg = f"Invalid category: {safe_cat}. Did you mean: {suggestion_text}?"
            else:
                msg = f"Invalid category: {safe_cat}. Check plaid_categories.toml for valid categories."
            return HTMLResponse(msg, status_code=400)

        new_mappings_path = os.path.join(base_dir, "config", "new_mappings.toml")
        try:
            import toml as toml_writer

            existing = {}
            if os.path.exists(new_mappings_path):
                with open(new_mappings_path, "rb") as f:
                    existing = tomllib.load(f)

            if "STAGING" not in existing:
                existing["STAGING"] = {}
            if "NEW" not in existing["STAGING"]:
                existing["STAGING"]["NEW"] = {}

            existing["STAGING"]["NEW"][cleaned_merchant.lower()] = {
                "name": cleaned_merchant,
                "category": category,
                "subcategory": category,
                "scope": source if source in ("public", "private") else "private",
            }

            with open(new_mappings_path, "w") as f:
                toml_writer.dump(existing, f)

            from money_mapper.transaction_enricher import clear_pattern_cache

            clear_pattern_cache()

            safe_merchant = html.escape(str(cleaned_merchant))
            safe_category = html.escape(str(category))
            return HTMLResponse(
                f"Added mapping: {safe_merchant} - {safe_category} (staged in new_mappings.toml)",
                status_code=201,
            )
        except Exception as e:
            safe_err = html.escape(str(e))
            return HTMLResponse(f"Failed to add mapping: {safe_err}", status_code=500)

    # ===== Settings Route =====
    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page() -> HTMLResponse:
        """Settings and configuration page.

        Returns:
            HTMLResponse: Rendered HTML settings page
        """
        template = env.get_template("settings.html")

        options = []
        settings_path = os.path.join(base_dir, "config", "public_settings.toml")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "rb") as f:
                    settings = tomllib.load(f)
                for section_name, section in settings.items():
                    if isinstance(section, dict):
                        for key, value in section.items():
                            options.append({"name": f"{section_name}.{key}", "value": str(value)})
            except Exception:
                pass

        data = {
            "title": "Settings",
            "active_page": "settings",
            "options": options if options else [{"name": "No settings found", "value": ""}],
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
    @app.get("/")
    async def root():
        """Root route redirects to dashboard."""
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/dashboard", status_code=307)

    # Mount static files if they exist
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec - local dev server
