"""Integration tests for money-mapper CLI pipeline.

These tests exercise the REAL pipeline with no mocks. They run actual CLI
commands against fixture data and verify real output files are created.
"""

import json
import os
import shutil
import subprocess
import sys

PYTHON = sys.executable
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "sample_statements")
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(REPO_ROOT, "config")


def setup_test_env(tmp_path):
    """Set up a complete test environment with config and output dirs."""
    # Copy entire config directory (including templates)
    dest_config = tmp_path / "config"
    if CONFIG_DIR and os.path.exists(CONFIG_DIR):
        shutil.copytree(CONFIG_DIR, dest_config)
    else:
        dest_config.mkdir()

    # Create output directory
    (tmp_path / "output").mkdir(exist_ok=True)

    # Create models directory
    (tmp_path / "models").mkdir(exist_ok=True)


def run_cli(*args: str, cwd: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a money-mapper CLI command and return the result."""
    cmd = [PYTHON, "-m", "money_mapper.cli", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd or os.path.dirname(os.path.dirname(__file__)),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestParseCommand:
    """Integration tests for the parse CLI command."""

    def test_parse_bofa_checking(self, tmp_path):
        """Parse BofA checking fixture and verify 20 transactions are produced."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        shutil.copy(
            os.path.join(FIXTURE_DIR, "bofa_checking_2024_01.csv"),
            statements_dir / "bofa_checking_2024_01.csv",
        )

        result = run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(output_dir / "financial_transactions.json"),
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        output_file = output_dir / "financial_transactions.json"
        assert output_file.exists(), "Output JSON file was not created"

        with open(output_file) as f:
            transactions = json.load(f)

        assert len(transactions) == 20, f"Expected 20 transactions, got {len(transactions)}"

    def test_parse_bofa_savings(self, tmp_path):
        """Parse BofA savings fixture and verify 6 transactions are produced."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        shutil.copy(
            os.path.join(FIXTURE_DIR, "bofa_savings_2024_01.csv"),
            statements_dir / "bofa_savings_2024_01.csv",
        )

        result = run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(output_dir / "financial_transactions.json"),
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        output_file = output_dir / "financial_transactions.json"
        assert output_file.exists(), "Output JSON file was not created"

        with open(output_file) as f:
            transactions = json.load(f)

        assert len(transactions) == 6, f"Expected 6 transactions, got {len(transactions)}"

    def test_parse_bofa_credit(self, tmp_path):
        """Parse BofA credit fixture and verify 16 transactions are produced."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        shutil.copy(
            os.path.join(FIXTURE_DIR, "bofa_credit_2024_01.csv"),
            statements_dir / "bofa_credit_2024_01.csv",
        )

        result = run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(output_dir / "financial_transactions.json"),
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        output_file = output_dir / "financial_transactions.json"
        assert output_file.exists(), "Output JSON file was not created"

        with open(output_file) as f:
            transactions = json.load(f)

        assert len(transactions) == 16, f"Expected 16 transactions, got {len(transactions)}"

    def test_parse_all_bofa_fixtures(self, tmp_path):
        """Parse all 3 BofA fixtures together and verify 42 total transactions."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        for filename in [
            "bofa_checking_2024_01.csv",
            "bofa_savings_2024_01.csv",
            "bofa_credit_2024_01.csv",
        ]:
            shutil.copy(
                os.path.join(FIXTURE_DIR, filename),
                statements_dir / filename,
            )

        result = run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(output_dir / "financial_transactions.json"),
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        output_file = output_dir / "financial_transactions.json"
        assert output_file.exists(), "Output JSON file was not created"

        with open(output_file) as f:
            transactions = json.load(f)

        assert len(transactions) == 42, f"Expected 42 transactions, got {len(transactions)}"

    def test_parse_nonexistent_directory(self, tmp_path):
        """Parse command with a nonexistent directory should fail gracefully."""
        setup_test_env(tmp_path)
        result = run_cli(
            "parse",
            "--dir",
            str(tmp_path / "does_not_exist"),
            cwd=str(tmp_path),
        )

        assert "Traceback" not in result.stderr


class TestEnrichCommand:
    """Integration tests for the enrich CLI command."""

    def test_enrich_parsed_transactions(self, tmp_path):
        """Parse then enrich transactions; verify enriched output has categories assigned."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        # Copy fixture CSV
        shutil.copy(
            os.path.join(FIXTURE_DIR, "bofa_checking_2024_01.csv"),
            statements_dir / "bofa_checking_2024_01.csv",
        )

        parsed_output = output_dir / "financial_transactions.json"

        parse_result = run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(parsed_output),
            cwd=str(tmp_path),
        )

        assert parse_result.returncode == 0, f"parse stderr: {parse_result.stderr}"
        assert parsed_output.exists(), "Parsed output file was not created"

        enriched_output = output_dir / "enriched_transactions.json"

        enrich_result = run_cli(
            "enrich",
            "--input",
            str(parsed_output),
            "--output",
            str(enriched_output),
            cwd=str(tmp_path),
        )

        assert enrich_result.returncode == 0, f"enrich stderr: {enrich_result.stderr}"
        assert "Traceback" not in enrich_result.stderr
        assert enriched_output.exists(), "Enriched output file was not created"

        with open(enriched_output) as f:
            transactions = json.load(f)

        assert len(transactions) > 0, "Enriched output has no transactions"

        # At least some transactions should have a category assigned
        categorized = [
            t for t in transactions if t.get("category") and t["category"] != "UNCATEGORIZED"
        ]
        assert len(categorized) > 0, "No transactions were categorized after enrichment"

    def test_enrich_nonexistent_file(self, tmp_path):
        """Enrich command with a nonexistent input file should fail gracefully."""
        setup_test_env(tmp_path)
        result = run_cli(
            "enrich",
            "--input",
            str(tmp_path / "does_not_exist.json"),
            cwd=str(tmp_path),
        )

        assert "Traceback" not in result.stderr


class TestAnalyzeCommand:
    """Integration tests for the analyze CLI command."""

    def _setup_enriched_file(self, tmp_path) -> str:
        """Parse and enrich a fixture CSV, returning the path to the enriched file."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        shutil.copy(
            os.path.join(FIXTURE_DIR, "bofa_checking_2024_01.csv"),
            statements_dir / "bofa_checking_2024_01.csv",
        )

        parsed_output = output_dir / "financial_transactions.json"
        run_cli(
            "parse",
            "--dir",
            str(statements_dir),
            "--output",
            str(parsed_output),
            cwd=str(tmp_path),
        )

        enriched_output = output_dir / "enriched_transactions.json"
        run_cli(
            "enrich",
            "--input",
            str(parsed_output),
            "--output",
            str(enriched_output),
            cwd=str(tmp_path),
        )

        return str(enriched_output)

    def test_analyze_enriched_transactions(self, tmp_path):
        """Analyze enriched transactions; verify output contains categorization text."""
        enriched_file = self._setup_enriched_file(tmp_path)

        result = run_cli(
            "analyze",
            "--file",
            enriched_file,
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        combined_output = result.stdout + result.stderr
        assert "categoriz" in combined_output.lower(), (
            f"Expected 'categoriz' in output, got: {combined_output[:500]}"
        )

    def test_analyze_verbose(self, tmp_path):
        """Analyze enriched transactions with --verbose flag; verify no crash."""
        enriched_file = self._setup_enriched_file(tmp_path)

        result = run_cli(
            "analyze",
            "--file",
            enriched_file,
            "--verbose",
            cwd=str(tmp_path),
        )

        assert "Traceback" not in result.stderr


class TestOtherCommands:
    """Integration tests for miscellaneous CLI commands."""

    def test_check_deps(self, tmp_path):
        """check-deps command should return exit code 0."""
        setup_test_env(tmp_path)
        result = run_cli("check-deps", cwd=str(tmp_path))

        assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
        assert "Traceback" not in result.stderr

    def test_validate_config(self, tmp_path):
        """validate command should complete without a Traceback."""
        result = run_cli("validate", cwd=str(tmp_path))

        assert "Traceback" not in result.stderr

    def test_privacy_audit(self, tmp_path):
        """privacy-audit command with --threshold high should complete without a Traceback."""
        result = run_cli(
            "privacy-audit",
            "--threshold",
            "high",
            cwd=str(tmp_path),
        )

        assert "Traceback" not in result.stderr

    def test_rebuild_model_public(self, tmp_path):
        """rebuild-model --public in a temp directory should complete without a Traceback."""
        setup_test_env(tmp_path)

        result = run_cli(
            "rebuild-model",
            "--public",
            cwd=str(tmp_path),
        )

        assert "Traceback" not in result.stderr

    def test_rebuild_model_creates_file(self, tmp_path):
        """rebuild-model --public should find merchants and create model."""
        setup_test_env(tmp_path)
        result = run_cli("rebuild-model", "--public", "--debug", cwd=str(tmp_path))
        assert "No merchants found" not in result.stdout, f"Bug: {result.stdout}"
        assert result.returncode == 0, f"rebuild failed: {result.stdout}\n{result.stderr}"

    def test_no_runtime_warning_on_cli(self):
        """CLI commands should not emit RuntimeWarning about sys.modules."""
        result = run_cli("check-deps")
        assert "RuntimeWarning" not in result.stderr, f"Warning found: {result.stderr}"


class TestFullPipeline:
    """Integration tests for the full pipeline command."""

    def test_pipeline_command(self, tmp_path):
        """Run full pipeline against all 3 BofA fixtures; verify 42 enriched transactions
        and a categorization rate above 50%."""
        setup_test_env(tmp_path)
        statements_dir = tmp_path / "statements"
        statements_dir.mkdir()
        output_dir = tmp_path / "output"

        for filename in [
            "bofa_checking_2024_01.csv",
            "bofa_savings_2024_01.csv",
            "bofa_credit_2024_01.csv",
        ]:
            shutil.copy(
                os.path.join(FIXTURE_DIR, filename),
                statements_dir / filename,
            )

        result = run_cli(
            "pipeline",
            "--dir",
            str(statements_dir),
            cwd=str(tmp_path),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Traceback" not in result.stderr

        # The pipeline command should produce an enriched output file
        enriched_candidates = list(output_dir.glob("*.json"))
        assert len(enriched_candidates) > 0, (
            f"No JSON output files found in {output_dir}. stdout: {result.stdout[:500]}"
        )

        # Load the most recently modified JSON file as the enriched output
        enriched_file = max(enriched_candidates, key=lambda p: p.stat().st_mtime)

        with open(enriched_file) as f:
            transactions = json.load(f)

        assert len(transactions) == 42, f"Expected 42 transactions, got {len(transactions)}"

        categorized = [
            t for t in transactions if t.get("category") and t["category"] != "UNCATEGORIZED"
        ]
        categorization_rate = len(categorized) / len(transactions)
        assert categorization_rate > 0.5, (
            f"Expected >50% categorization rate, got {categorization_rate:.1%} "
            f"({len(categorized)}/{len(transactions)})"
        )
