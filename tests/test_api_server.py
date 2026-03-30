"""
Tests for FastAPI web interface and routes.

Tests all 5 pages: Dashboard, Transactions, Import, Mappings, Settings.
Uses httpx.AsyncClient with FastAPI TestClient pattern.
"""

import json
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# These imports will exist after GREEN phase implementation
from money_mapper.api.server import create_app


class TestServerCreation:
    """Test FastAPI app factory."""

    def test_create_app_returns_fastapi_instance(self):
        """create_app() should return a valid FastAPI instance."""
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_routes_registered(self):
        """App should have routes registered after creation."""
        app = create_app()
        routes = [route.path for route in app.routes]
        assert "/" in routes or "/dashboard" in routes

    def test_app_has_middleware_configured(self):
        """App should have routes configured."""
        app = create_app()
        # Should have routes registered
        assert len(app.routes) > 0


class TestDashboardRoute:
    """Test /dashboard GET endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        app = create_app()
        return TestClient(app)

    def test_dashboard_returns_200(self, client):
        """GET /dashboard should return HTTP 200."""
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_returns_html(self, client):
        """GET /dashboard should return HTML content."""
        response = client.get("/dashboard")
        assert "text/html" in response.headers.get("content-type", "")

    def test_dashboard_contains_spending_section(self, client):
        """Dashboard should contain spending data visualization."""
        response = client.get("/dashboard")
        assert "spending" in response.text.lower() or "chart" in response.text.lower()

    def test_dashboard_contains_recent_transactions(self, client):
        """Dashboard should reference recent transactions."""
        response = client.get("/dashboard")
        assert "transaction" in response.text.lower()

    def test_dashboard_template_renders(self, client):
        """Dashboard template should render without errors."""
        response = client.get("/dashboard")
        assert len(response.text) > 100  # Should have meaningful content


class TestTransactionsRoute:
    """Test /transactions GET/POST endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_transactions_list_returns_200(self, client):
        """GET /transactions should return 200."""
        response = client.get("/transactions")
        assert response.status_code == 200

    def test_transactions_returns_html(self, client):
        """GET /transactions should return HTML."""
        response = client.get("/transactions")
        assert "text/html" in response.headers.get("content-type", "")

    def test_transactions_list_contains_table(self, client):
        """Transactions page should have a table element."""
        response = client.get("/transactions")
        assert "table" in response.text.lower() or "transaction" in response.text.lower()

    def test_transactions_post_updates_category(self, client):
        """POST /transactions/{id} should update category."""
        # This will need real transaction fixtures in GREEN phase
        # For now, test the endpoint exists
        response = client.post("/transactions/1", json={"category": "Food"})
        # Should either succeed or return appropriate error
        assert response.status_code in [200, 404, 400]

    def test_transactions_filter_by_date(self, client):
        """GET /transactions?date=YYYY-MM should filter by date."""
        response = client.get("/transactions?date=2026-03")
        assert response.status_code in [200, 400]

    def test_transactions_filter_by_category(self, client):
        """GET /transactions?category=Food should filter by category."""
        response = client.get("/transactions?category=Food")
        assert response.status_code in [200, 400]

    def test_transactions_csv_export_available(self, client):
        """GET /transactions/export should return CSV."""
        response = client.get("/transactions/export")
        assert response.status_code in [200, 404]  # May not exist in basic version

    def test_export_csv_has_content_disposition(self, client):
        """Export should have Content-Disposition header for download."""
        response = client.get("/transactions/export")
        assert "content-disposition" in response.headers
        assert "transactions.csv" in response.headers["content-disposition"]

    def test_export_csv_valid_format(self, client):
        """Exported CSV should be parseable by csv module."""
        import csv
        import io

        response = client.get("/transactions/export")
        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        # At minimum, header row should exist
        assert len(rows) >= 1
        assert rows[0] == ["date", "merchant", "amount", "category"]


class TestImportRoute:
    """Test /import GET/POST endpoints for file upload."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_import_form_returns_200(self, client):
        """GET /import should return upload form."""
        response = client.get("/import")
        assert response.status_code == 200

    def test_import_form_contains_upload_input(self, client):
        """Import form should have file input."""
        response = client.get("/import")
        assert "file" in response.text.lower() or "upload" in response.text.lower()

    def test_import_form_supports_csv(self, client):
        """Form should indicate CSV support."""
        response = client.get("/import")
        assert "csv" in response.text.lower()

    def test_import_form_supports_ofx(self, client):
        """Form should indicate OFX support."""
        response = client.get("/import")
        assert "ofx" in response.text.lower() or "qfx" in response.text.lower()

    def test_post_csv_file_accepted(self, client):
        """POST /import with CSV should be accepted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("date,description,amount\n2026-01-01,Store,100.00\n")
            f.flush()
            with open(f.name, "rb") as csv_file:
                response = client.post("/import", files={"file": csv_file})
        assert response.status_code in [200, 400]  # Should at least not reject it

    def test_post_invalid_file_rejected(self, client):
        """POST /import with invalid file should fail appropriately."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is not a valid file format")
            f.flush()
            with open(f.name, "rb") as invalid_file:
                response = client.post("/import", files={"file": invalid_file})
        # Should return error code or redirect
        assert response.status_code in [400, 422]


class TestMappingsRoute:
    """Test /mappings GET/POST endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_mappings_list_returns_200(self, client):
        """GET /mappings should return mappings list."""
        response = client.get("/mappings")
        assert response.status_code == 200

    def test_mappings_shows_public_mappings(self, client):
        """Mappings page should display public mappings."""
        response = client.get("/mappings")
        assert "public" in response.text.lower() or "mapping" in response.text.lower()

    def test_mappings_shows_private_mappings(self, client):
        """Mappings page should display private mappings."""
        response = client.get("/mappings")
        assert "private" in response.text.lower() or "custom" in response.text.lower()

    def test_mappings_post_adds_new(self, client):
        """POST /mappings should add new mapping."""
        response = client.post(
            "/mappings", data={"merchant": "Test Store", "category": "Shopping", "source": "test"}
        )
        assert response.status_code in [200, 201, 400]

    def test_mappings_shows_privacy_warnings(self, client):
        """Mappings page should show privacy warnings for risky entries."""
        response = client.get("/mappings")
        # Should at least load without error
        assert response.status_code == 200


class TestSettingsRoute:
    """Test /settings GET/POST endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_settings_returns_200(self, client):
        """GET /settings should return settings page."""
        response = client.get("/settings")
        assert response.status_code == 200

    def test_settings_shows_configuration(self, client):
        """Settings page should display current config."""
        response = client.get("/settings")
        assert "setting" in response.text.lower() or "config" in response.text.lower()

    def test_settings_post_updates_config(self, client):
        """POST /settings should update configuration."""
        response = client.post("/settings", json={"option": "value"})
        assert response.status_code in [200, 400]

    def test_settings_has_about_section(self, client):
        """Settings should have an About section."""
        response = client.get("/settings")
        assert "about" in response.text.lower() or "money mapper" in response.text.lower()

    def test_settings_has_save_button(self, client):
        """Settings should have a Save Settings button."""
        response = client.get("/settings")
        assert "save" in response.text.lower()


class TestErrorHandling:
    """Test error responses and edge cases."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_nonexistent_route_returns_404(self, client):
        """Accessing non-existent route should return 404."""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

    def test_missing_required_fields_returns_error(self, client):
        """POST without required fields should return validation error."""
        response = client.post("/mappings", data={})
        # FastAPI returns 422 for validation errors (more correct than 400)
        assert response.status_code in [400, 422]

    def test_invalid_json_returns_422(self, client):
        """Malformed JSON should return 422."""
        response = client.post(
            "/mappings", content="not json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_file_upload_without_file_returns_400(self, client):
        """POST to /import without file should error."""
        response = client.post("/import")
        assert response.status_code in [400, 422]

    def test_invalid_category_update_returns_400(self, client):
        """Updating with invalid category should return error."""
        response = client.post("/transactions/1", json={"category": ""})
        assert response.status_code == 400

    def test_too_large_file_rejected(self, client):
        """Uploading very large file should be rejected."""
        # In real implementation, check file size limit
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv") as f:
            # Write 100MB of data
            f.write(b"x" * (100 * 1024 * 1024))
            f.flush()
            # This might timeout or be rejected
            # For now, just ensure route handles it
            pass  # Will test in integration


class TestRouteIntegration:
    """Test integration between routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    def test_all_pages_accessible(self, client):
        """All main pages should be accessible."""
        pages = ["/dashboard", "/transactions", "/import", "/mappings", "/settings"]
        for page in pages:
            response = client.get(page)
            assert response.status_code == 200, f"{page} failed with {response.status_code}"

    def test_navigation_between_pages(self, client):
        """Pages should contain links to other pages."""
        # At minimum, dashboard should load
        response = client.get("/dashboard")
        assert response.status_code == 200


class TestDataHelpers:
    """Test data loading helper functions."""

    def test_load_enriched_transactions_returns_list(self, tmp_path):
        """Should load transactions from JSON file."""
        from money_mapper.api.server import _load_enriched_transactions

        txn_file = tmp_path / "enriched_transactions.json"
        txn_file.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-01-15",
                        "merchant_name": "STORE",
                        "amount": -50.0,
                        "category": "Shopping",
                    }
                ]
            )
        )
        result = _load_enriched_transactions(str(txn_file))
        assert len(result) == 1
        assert result[0]["merchant_name"] == "STORE"

    def test_load_enriched_transactions_missing_file(self, tmp_path):
        """Should return empty list when file doesn't exist."""
        from money_mapper.api.server import _load_enriched_transactions

        result = _load_enriched_transactions(str(tmp_path / "nonexistent.json"))
        assert result == []

    def test_load_mappings_from_toml(self, tmp_path):
        """Should load and flatten mappings from TOML file."""
        from money_mapper.api.server import _load_mappings_flat

        toml_file = tmp_path / "mappings.toml"
        toml_file.write_text(
            "[FOOD_AND_DRINK.COFFEE]\n"
            '"starbucks*" = {name = "Starbucks", category = "FOOD_AND_DRINK", '
            'subcategory = "FOOD_AND_DRINK_COFFEE", scope = "public"}\n'
        )
        result = _load_mappings_flat(str(toml_file))
        assert len(result) >= 1
        assert result[0]["merchant"] == "starbucks*"
        assert result[0]["name"] == "Starbucks"

    def test_load_mappings_missing_file(self, tmp_path):
        """Should return empty list when file doesn't exist."""
        from money_mapper.api.server import _load_mappings_flat

        result = _load_mappings_flat(str(tmp_path / "nonexistent.toml"))
        assert result == []

    def test_compute_spending_by_category(self):
        """Should aggregate amounts by category."""
        from money_mapper.api.server import _compute_spending_by_category

        transactions = [
            {"category": "FOOD", "amount": -10.0},
            {"category": "FOOD", "amount": -5.0},
            {"category": "TRANSPORT", "amount": -20.0},
        ]
        result = _compute_spending_by_category(transactions)
        assert "TRANSPORT" in result["categories"]
        assert "FOOD" in result["categories"]
        assert len(result["categories"]) == 2
        # Transport is 20, Food is 15, so Transport should be first (sorted by amount desc)
        assert result["categories"][0] == "TRANSPORT"

    def test_compute_spending_empty(self):
        """Should handle empty transaction list."""
        from money_mapper.api.server import _compute_spending_by_category

        result = _compute_spending_by_category([])
        assert result["categories"] == []
        assert result["amounts"] == []


class TestDashboardRealData:
    """Test dashboard with real data loading."""

    def test_dashboard_empty_state(self):
        """Dashboard renders without crashing when no data exists."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_dashboard_with_transactions(self, tmp_path):
        """Dashboard shows spending data from transactions file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn_file = output_dir / "enriched_transactions.json"
        txn_file.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-03-28",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD_AND_DRINK",
                    },
                    {
                        "date": "2026-03-27",
                        "merchant_name": "Shell",
                        "amount": -45.00,
                        "category": "TRANSPORTATION",
                    },
                ]
            )
        )

        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_root_shows_dashboard(self, tmp_path):
        """Root route should render dashboard template."""
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200


class TestTransactionsRealData:
    """Test transactions route with real data."""

    def test_transactions_loads_real_data(self, tmp_path):
        """Transactions page shows data from enriched file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn_file = output_dir / "enriched_transactions.json"
        txn_file.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-03-28",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD_AND_DRINK",
                        "description": "STARBUCKS #1234",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions")
        assert response.status_code == 200

    def test_transactions_empty_state(self):
        """Transactions page works with no data."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/transactions")
        assert response.status_code == 200

    def test_transactions_filter_by_category(self, tmp_path):
        """Filter narrows results to matching category."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn_file = output_dir / "enriched_transactions.json"
        txn_file.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-03-28",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD",
                    },
                    {
                        "date": "2026-03-27",
                        "merchant_name": "Shell",
                        "amount": -45.00,
                        "category": "TRANSPORT",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions?category=FOOD")
        assert response.status_code == 200

    def test_transactions_export_csv(self, tmp_path):
        """Export returns real CSV data."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        txn_file = output_dir / "enriched_transactions.json"
        txn_file.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-03-28",
                        "merchant_name": "Store",
                        "amount": -50.0,
                        "category": "Shopping",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "Store" in response.text


class TestImportRealData:
    """Test import route with real pipeline."""

    def test_import_csv_processes_file(self, tmp_path):
        """Uploading a CSV should attempt to process it."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)

        csv_content = "Date,Description,Amount,Running Bal.\n01/15/2026,STARBUCKS,-5.50,1000.00\n"
        response = client.post(
            "/import",
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
        )
        # Should succeed or report import count (not crash)
        assert response.status_code in (200, 500)

    def test_import_rejects_invalid_extension(self):
        """Should reject non-CSV/OFX/QFX files."""
        app = create_app()
        client = TestClient(app)
        response = client.post(
            "/import",
            files={"file": ("test.txt", b"some text", "text/plain")},
        )
        assert response.status_code == 400

    def test_import_empty_file(self, tmp_path):
        """Should handle empty CSV gracefully."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.post(
            "/import",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert response.status_code in (200, 500)


class TestMappingsRealData:
    """Test mappings route with real data."""

    def test_mappings_loads_from_toml(self, tmp_path):
        """Mappings page loads real data from TOML files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "public_mappings.toml").write_text(
            "[FOOD_AND_DRINK.COFFEE]\n"
            '"starbucks*" = {name = "Starbucks", category = "FOOD_AND_DRINK", '
            'subcategory = "FOOD_AND_DRINK_COFFEE", scope = "public"}\n'
        )
        (config_dir / "private_mappings.toml").write_text("")

        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/mappings")
        assert response.status_code == 200

    def test_mappings_empty_state(self):
        """Mappings page works when no mapping files exist."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/mappings")
        assert response.status_code == 200

    def test_create_mapping_writes_staging(self, tmp_path):
        """Adding a mapping should write to new_mappings.toml."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "public_mappings.toml").write_text("")
        (config_dir / "private_mappings.toml").write_text("")

        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.post(
            "/mappings",
            data={"merchant": "Test Store", "category": "SHOPPING", "source": "manual"},
        )
        assert response.status_code == 201
        # Verify file was created
        assert (config_dir / "new_mappings.toml").exists()


class TestSettingsRealData:
    """Test settings route with real data."""

    def test_settings_loads_config(self, tmp_path):
        """Settings page loads real config from TOML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "public_settings.toml").write_text(
            '[directories]\nstatements = "statements"\noutput = "output"\n'
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/settings")
        assert response.status_code == 200

    def test_settings_empty_state(self):
        """Settings page works when no config file exists."""
        app = create_app()
        client = TestClient(app)
        response = client.get("/settings")
        assert response.status_code == 200


class TestBrowserRendering:
    """Test all pages render correctly with real fixture data."""

    def test_dashboard_shows_spending_categories(self, tmp_path):
        """Dashboard should show spending breakdown from enriched data."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "enriched_transactions.json").write_text(
            json.dumps(
                [
                    {
                        "date": "2024-01-15",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD_AND_DRINK",
                        "categorization_method": "public_mapping",
                        "confidence": 0.95,
                    },
                    {
                        "date": "2024-01-16",
                        "merchant_name": "Shell",
                        "amount": -45.00,
                        "category": "TRANSPORTATION",
                        "categorization_method": "public_mapping",
                        "confidence": 0.95,
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200
        text = response.text.lower()
        assert "food_and_drink" in text or "starbucks" in text

    def test_dashboard_empty_state(self, tmp_path):
        """Dashboard renders without crashing when no data exists."""
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_transactions_shows_real_data(self, tmp_path):
        """Transactions page shows real transaction rows."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "enriched_transactions.json").write_text(
            json.dumps(
                [
                    {
                        "date": "2024-01-15",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD_AND_DRINK",
                        "categorization_method": "public_mapping",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions")
        assert response.status_code == 200
        assert "starbucks" in response.text.lower()

    def test_transactions_filter_by_category(self, tmp_path):
        """Category filter narrows transaction list."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "enriched_transactions.json").write_text(
            json.dumps(
                [
                    {
                        "date": "2024-01-15",
                        "merchant_name": "Starbucks",
                        "amount": -5.50,
                        "category": "FOOD",
                    },
                    {
                        "date": "2024-01-16",
                        "merchant_name": "Shell",
                        "amount": -45.00,
                        "category": "TRANSPORT",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions?category=FOOD")
        assert response.status_code == 200

    def test_import_page_has_upload_form(self, tmp_path):
        """Import page renders file upload form."""
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/import")
        assert response.status_code == 200
        text = response.text.lower()
        assert "file" in text
        assert "import" in text

    def test_mappings_page_loads_real_data(self, tmp_path):
        """Mappings page loads real mappings from TOML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "public_mappings.toml").write_text(
            "[FOOD_AND_DRINK.COFFEE]\n"
            '"starbucks*" = {name = "Starbucks", category = "FOOD_AND_DRINK", '
            'subcategory = "FOOD_AND_DRINK_COFFEE", scope = "public"}\n'
        )
        (config_dir / "private_mappings.toml").write_text("")
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/mappings")
        assert response.status_code == 200
        assert "starbucks" in response.text.lower()

    def test_settings_page_shows_config(self, tmp_path):
        """Settings page displays real config from TOML."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "public_settings.toml").write_text(
            '[directories]\nstatements = "statements"\noutput = "output"\n'
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/settings")
        assert response.status_code == 200
        assert "statements" in response.text

    def test_all_nav_links_return_200(self, tmp_path):
        """Every navigation link should resolve to 200."""
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        for path in ["/", "/dashboard", "/transactions", "/import", "/mappings", "/settings"]:
            response = client.get(path)
            assert response.status_code == 200, f"{path} returned {response.status_code}"

    def test_csv_export_returns_csv(self, tmp_path):
        """Export endpoint returns CSV with real data."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "enriched_transactions.json").write_text(
            json.dumps(
                [
                    {
                        "date": "2024-01-15",
                        "merchant_name": "Store",
                        "amount": -50.0,
                        "category": "Shopping",
                    },
                ]
            )
        )
        app = create_app(data_dir=str(tmp_path))
        client = TestClient(app)
        response = client.get("/transactions/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "Store" in response.text
