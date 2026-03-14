# MoneyMapper: Complete Implementation Plan

**Status:** Planning phase — GitHub issues created, Phases 0–2 in progress, Mission launch scheduled after Phase 2

**Last updated:** 2026-03-14

---

## Execution Strategy

### Phase 0–2: Manual (this establishes Mission prerequisites)
Execute manually in short focused sessions. These phases create the test suite, CI pipeline, and `AGENTS.md` that Mission validation workers depend on.

### Phase 3–9: Mission
Once Phases 0–2 are complete, launch a Mission with Phases 3–9 as milestones. At that point:
- `pytest` exists for validation workers to run
- `AGENTS.md` gives workers project conventions
- `IMPLEMENTATION_PLAN.md` gives workers clear phase definitions
- CI/CD catches any regression before it merges

---

## Phases

### Phase 0: Developer Experience Foundation
`pyproject.toml` replaces `requirements.txt` (pypdf removed). Adds entry point `money-mapper = "money_mapper.cli:main"`. Configures ruff, mypy, pytest, bandit in one file. `.pre-commit-config.yaml` runs ruff + mypy + bandit + `money-mapper privacy-audit --staged` before every commit. `.github/workflows/ci.yml` runs full suite on every push/PR (ruff → mypy → bandit → pip-audit → privacy-audit → pytest, fail below 60% coverage). `DEVELOPMENT.md` updated with code style, testing, and contribution guidelines. `.gitignore` extended to exclude Droid/agent artifacts. `src/` restructured to `src/money_mapper/` proper package.

### Phase 1: Test Infrastructure
Write tests for all existing modules before any refactoring or deletion. `tests/` directory with `conftest.py`, fixtures (sample CSVs, JSON, TOML), and test files for `utils`, `config_manager`, `statement_parser` (before deletion), `transaction_enricher`, `mapping_processor`.

### Phase 2: Bug Fix — Issue #32
Regression test first (red), then fix: credit card transactions incorrectly dated 2025 instead of 2024.

### Phase 3: Replace PDF Parsing with CSV Import
`statement_parser.py` and `pypdf` deleted (remain in git history). New `csv_parser.py` with auto-detection of bank column patterns, configurable per-bank format mapping in `statement_patterns.toml`, and OFX/QFX secondary support. Outputs identical transaction JSON — no downstream changes needed.

### Phase 4: Privacy Guard System
New `privacy_scanner.py` scores merchants against: medical/health/religious/personal service keywords, full name patterns, low transaction frequency, category inference, and semantic distance from national chains. `money-mapper privacy-audit` CLI command with `--staged` flag for pre-commit use. Blocks commits adding flagged entries to public files. Offers `gh issue create` with pre-filled template for each finding. Retrospective scan runs on first use of existing `public_mappings.toml`.

### Phase 5: Smart Categorization — Hybrid ML Pipeline
```
Stage 1: Exact mapping lookup (public + private TOML)      ~65%, 100% accurate
Stage 2: Fuzzy/wildcard matching (existing)                ~20%, high accuracy
Stage 3a: sklearn classifier (≥20 labeled examples/cat)   true incremental learning
Stage 3b: Sentence transformer similarity fallback         85–95% accuracy
Stage 4: Manual review queue (existing)                    user decides
```
New `smart_categorizer.py`. Public model (`models/public_classifier.pkl`, `models/public_vectors.npy`) committed to repo — trained on public mapping keywords only, zero personal data. Private model (`models/private_*.pkl`, `models/private_*.npy`) gitignored, learns from user decisions over time. `money-mapper rebuild-model --public` regenerates public artifacts.

### Phase 6: Refactor `mapping_processor.py`
Split 2,118-line file into: `mapping_io.py` (file I/O), `mapping_validator.py` (PFC validation), `mapping_merger.py` (conflict resolution), `wildcard_engine.py` (pattern matching). `mapping_processor.py` kept as thin orchestrator. Phase 1 tests are the safety net.

### Phase 7: Performance Improvements
Issues #29, #30, #31, #27 addressed in order of impact. Issue #28 (PDF multiprocessing) closed as obsolete.

### Phase 8: UX + Community Contributions
Issues #18 and #19. Community contribution flow: after a new public merchant passes the privacy guard, offer `gh pr create` to share with community. Opt-in, one command.

### Phase 9: Web Interface — FastAPI + HTMX
`money-mapper web` starts `uvicorn` on `localhost:8000`, auto-opens browser, runs until Ctrl+C. Data stays in local files. New `api/` directory with `server.py`, `routes/` (import, transactions, mappings, analytics, privacy), and `templates/` (Jinja2+HTMX, no JS build step). Five pages: Dashboard (spending charts), Transactions (filterable table, inline edit), Import (CSV/OFX upload), Mappings (visual builder with privacy warnings), Settings. REST API is also the programmatic automation interface.

---

## GitHub Issues Backlog

Create all of these before beginning Phase 0. Existing issues (#18, #19, #27–32) are noted — do not duplicate.

### Phase 0 — Developer Experience (6 new issues)
- Set up pyproject.toml with modern packaging and entry point
- Configure ruff linting and mypy type checking
- Set up pre-commit hooks (ruff, mypy, bandit, privacy-audit)
- Set up GitHub Actions CI/CD pipeline
- Update .gitignore to exclude Droid/development artifacts, enhance DEVELOPMENT.md
- Restructure src/ to src/money_mapper/ Python package

### Phase 1 — Test Infrastructure (6 new issues)
- Create test infrastructure: conftest.py, fixtures, directory structure
- Write unit tests for utils.py
- Write unit tests for config_manager.py
- Write unit tests for statement_parser.py (before deletion in Phase 3)
- Write unit tests for transaction_enricher.py
- Write unit tests for mapping_processor.py

### Phase 2 — Bug Fix
- #32 (existing): Fix credit card transaction date bug

### Phase 3 — CSV Import (5 new issues)
- Implement csv_parser.py with bank format auto-detection
- Add per-bank CSV format config section to statement_patterns.toml
- Add OFX/QFX file import support via ofxtools
- Remove statement_parser.py and pypdf dependency
- Update CLI and README: CSV-only import, remove --format flag

### Phase 4 — Privacy Guard (6 new issues)
- Implement privacy_scanner.py with merchant privacy scoring
- Add money-mapper privacy-audit CLI command
- Integrate privacy guard into pre-commit hooks and CI
- Add gh issue create integration for privacy findings
- Retrospective audit of existing public_mappings.toml on first run
- Write tests for privacy_scanner.py

### Phase 5 — Smart Categorization (6 new issues)
- Implement smart_categorizer.py: sentence transformer similarity
- Add sklearn classifier layer with incremental learning
- Build and commit public_classifier.pkl training pipeline
- Pre-compute and commit public_vectors.npy
- Integrate smart_categorizer into transaction enrichment pipeline
- Add money-mapper rebuild-model CLI command

### Phase 6 — Mapping Processor Refactor (5 new issues)
- Extract mapping_io.py from mapping_processor.py
- Extract mapping_validator.py from mapping_processor.py
- Extract mapping_merger.py from mapping_processor.py
- Extract wildcard_engine.py from mapping_processor.py
- Slim mapping_processor.py to thin orchestrator

### Phase 7 — Performance
- #29 (existing): Pre-compile pattern index
- #30 (existing): Cache config and reduce redundant loads
- #31 (existing): Optimize wildcard consolidation
- #27 (existing): Multiprocessing for transaction enrichment
- #28 (existing): Close as obsolete — PDF removed

### Phase 8 — UX + Community
- #19 (existing): Numbered menu for category validation
- #18 (existing): Mapping file selection for wildcard consolidation
- Community contribution flow: PR creation for new public merchants

### Phase 9 — Web Interface (13 new issues)
- Set up FastAPI server structure and routing (api/server.py)
- Create Jinja2 base templates with HTMX integration
- Implement /api/import endpoint (CSV/OFX upload and parse)
- Implement /api/transactions endpoints (list, filter, update category)
- Implement /api/mappings endpoints (CRUD)
- Implement /api/analytics endpoints (spending by category, trends)
- Build Dashboard page (spending charts, month-over-month, top merchants)
- Build Transactions page (filterable table, inline category editing)
- Build Import page (drag-and-drop upload, bank format detection)
- Build Mappings page (visual builder, privacy warnings inline)
- Build Settings page (bank config, privacy settings, model rebuild)
- Add money-mapper web CLI command with auto-browser-open
- Write API integration tests using httpx

### Future Roadmap (create as issues, no phase assignment yet)
- Subscription/recurring transaction auto-detection
- Budget tracking per PFC category with alerts
- Anomaly detection for unusual transactions
- Tax tagging and deductible transaction export
- Net worth snapshot from imported account balances
- Spending goals with progress tracking

**Total: ~47 new issues + 8 existing = ~55 issues**

---

## Final File Structure

```
money-mapper/
├── src/money_mapper/
│   ├── __init__.py
│   ├── cli.py
│   ├── csv_parser.py            # Phase 3
│   ├── transaction_enricher.py
│   ├── smart_categorizer.py     # Phase 5
│   ├── privacy_scanner.py       # Phase 4
│   ├── mapping_processor.py     # Phase 6 (thin orchestrator)
│   ├── mapping_io.py            # Phase 6
│   ├── mapping_validator.py     # Phase 6
│   ├── mapping_merger.py        # Phase 6
│   ├── wildcard_engine.py       # Phase 6
│   ├── interactive_mapper.py
│   ├── config_manager.py
│   ├── setup_wizard.py
│   ├── utils.py
│   └── api/                     # Phase 9
│       ├── __init__.py
│       ├── server.py
│       ├── routes/
│       │   ├── import_.py
│       │   ├── transactions.py
│       │   ├── mappings.py
│       │   ├── analytics.py
│       │   └── privacy.py
│       └── templates/
│           ├── base.html
│           ├── dashboard.html
│           ├── transactions.html
│           ├── import.html
│           ├── mappings.html
│           └── settings.html
├── models/
│   ├── public_classifier.pkl    # committed — zero personal data
│   └── public_vectors.npy       # committed — zero personal data
├── tests/                       # Phase 1
├── .github/workflows/ci.yml     # Phase 0
├── pyproject.toml               # Phase 0
├── .pre-commit-config.yaml      # Phase 0
├── AGENTS.md                    # Phase 0
├── IMPLEMENTATION_PLAN.md       # this document
└── .gitignore

Gitignored (never committed):
  models/private_*.pkl
  models/private_*.npy
  config/private_*.toml
  statements/
  output/
```

---

## Open Issues Disposition

| Issue | Action |
|---|---|
| #32 Bug: wrong dates | Phase 2 |
| #29 #30 #31 Performance | Phase 7 |
| #28 PDF multiprocessing | Close as obsolete (Phase 7) |
| #27 Enrichment multiprocessing | Phase 7 |
| #19 #18 UX improvements | Phase 8 |
