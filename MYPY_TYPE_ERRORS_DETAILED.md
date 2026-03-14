# Mypy Type Errors - Complete Inventory

**Generated:** 2026-03-14  
**Total Errors:** 42  
**Status:** All deferred to Phase 1 (gradual typing approach)

---

## Summary by Category

| Category | Count | Severity | Phase 1 Effort |
|----------|-------|----------|----------------|
| Incompatible Defaults (Optional) | 11 | Medium | 2-3 hours |
| Missing Type Annotations | 9 | Low | 1-2 hours |
| Return Type Mismatches | 13 | High | 3-4 hours |
| Library Stubs Missing | 2 | Low | 30 min |
| Argument Type Mismatches | 7 | Medium | 2-3 hours |
| **TOTAL** | **42** | **Medium** | **9-13 hours** |

---

## Category 1: Incompatible Defaults (11 errors)

**Problem:** Functions have type hints that don't allow `None`, but default parameter values are `None`.

**Fix:** Change parameter type to `Optional[Type]` or `Type | None`

### cli.py (1 error)

```python
# Line 132
def handle_interactive_mapping(command: str = None):
    # Should be:
def handle_interactive_mapping(command: str | None = None):
```

### config_manager.py (2 errors)

```python
# Line 16
def __init__(self, config_dir: str = None):
    # Should be:
def __init__(self, config_dir: str | None = None):

# Line 338
def load_config(config_dir: str = None) -> dict:
    # Should be:
def load_config(config_dir: str | None = None) -> dict:
```

### utils.py (2 errors)

```python
# Line 133
def sanitize_description(desc, sanitization_patterns: list[Any] = None):
    # Should be:
def sanitize_description(desc, sanitization_patterns: list[Any] | None = None):

# Line 134
def sanitize_description(desc, privacy_config: dict[Any, Any] = None):
    # Should be:
def sanitize_description(desc, privacy_config: dict[Any, Any] | None = None):

# Line 836
def get_dict_key(dict_obj, key, default: str = None):
    # Should be:
def get_dict_key(dict_obj, key, default: str | None = None):
```

### transaction_enricher.py (2 errors)

```python
# Line 741
def save_enrichment_results(results, output_file: str = None, verbose: bool = False):
    # Should be:
def save_enrichment_results(results, output_file: str | None = None, verbose: bool = False):
```

### setup_wizard.py (1 error)

```python
# Line 399
def display_summary(stats: dict[Any, Any] = None):
    # Should be:
def display_summary(stats: dict[Any, Any] | None = None):
```

### mapping_processor.py (2 errors)

```python
# Line 1986
def add_mapping(pattern: str, category: str, source_file: str = None):
    # Should be:
def add_mapping(pattern: str, category: str, source_file: str | None = None):
```

**Total Time to Fix:** ~2-3 hours

---

## Category 2: Missing Type Annotations (9 errors)

**Problem:** Variables assigned without type hints. Mypy's `var-annotated` rule requires explicit types for complex assignments.

**Fix:** Add explicit type annotations to all dict/list initializations.

### utils.py (1 error)

```python
# Line 603
method_counts = {}
# Should be:
method_counts: dict[str, int] = {}
```

### transaction_enricher.py (3 errors)

```python
# Line 593
methods = {}
# Should be:
methods: dict[str, Any] = {}

# Line 605
categories = {}
# Should be:
categories: dict[str, Any] = {}

# Line 766
methods = {}
# Should be:
methods: dict[str, Any] = {}

# Line 780
categories = {}
# Should be:
categories: dict[str, Any] = {}

# Line 781
amounts = {}
# Should be:
amounts: dict[str, float] = {}
```

### mapping_processor.py (5 errors)

```python
# Line 264
backups_by_file = {}
# Should be:
backups_by_file: dict[str, str] = {}

# Line 476
all_patterns = {}
# Should be:
all_patterns: dict[str, Any] = {}

# Line 477
wildcard_patterns = {}
# Should be:
wildcard_patterns: dict[str, list[str]] = {}

# Line 762
private_additions = {}
# Should be:
private_additions: dict[str, Any] = {}

# Line 763
public_additions = {}
# Should be:
public_additions: dict[str, Any] = {}

# Line 857
existing_patterns = {}
# Should be:
existing_patterns: dict[str, str] = {}

# Line 1235
fix_types = {}
# Should be:
fix_types: dict[str, int] = {}

# Line 1968
word_counts = {}
# Should be:
word_counts: dict[str, int] = {}
```

### interactive_mapper.py (1 error)

```python
# Line 139
taxonomy = {}
# Should be:
taxonomy: dict[str, list[str]] = {}
```

**Total Time to Fix:** ~1-2 hours

---

## Category 3: Return Type Mismatches (13 errors)

**Problem:** Functions return `Any` (from TOML/JSON parsing) but type hints specify concrete types. Mypy complains of `[no-any-return]`.

**Fix:** Either (a) change return type to `Any`, (b) add type assertions, or (c) improve type hints on config loading.

### config_manager.py (6 errors)

```python
# Line 257
def get_timeout(self) -> float:
    return self.config["timeout"]  # Returns Any
# Fix: Change return type to 'Any' or cast properly:
def get_timeout(self) -> float:
    return float(self.config["timeout"])

# Line 270
def get_threshold(self) -> float:
    return self.config["threshold"]

# Line 283
def get_max_retries(self) -> int:
    return self.config["max_retries"]

# Line 288
def is_debug_enabled(self) -> bool:
    return self.config["debug"]

# Line 309
def is_strict_mode_enabled(self) -> bool:
    return self.config["strict_mode"]

# Line 331
def get_all_settings(self) -> dict[Any, Any]:
    return self.config
```

### utils.py (1 error)

```python
# Line 390
def load_json_file(filepath) -> list[dict[Any, Any]]:
    # Returns Any from json.load()
    return json.load(open(filepath))
# Fix:
def load_json_file(filepath) -> list[dict[Any, Any]]:
    import json
    with open(filepath) as f:
        return json.load(f)
```

### statement_parser.py (4 errors)

```python
# Line 323
def detect_date_format(sample_date) -> str | None:
    return row_data["date_format"]  # Returns Any

# Line 389
def get_posting_date(self, row) -> int:
    return row["posting_date"]  # Returns Any

# Line 391
def get_transaction_amount(self, row) -> int:
    return row["amount"]  # Returns Any
```

### transaction_enricher.py (1 error)

```python
# Line 524
confidence: int = float(confidence)
# Type mismatch: float assigned to int variable
# Fix:
confidence: float = float(confidence)
```

### setup_wizard.py (1 error)

```python
# Line 379
api_limit: int | None = float(input_value)
# Type mismatch: float assigned to int | None
# Fix:
api_limit: int | None = int(float(input_value))
```

**Total Time to Fix:** ~3-4 hours (requires careful type casting)

---

## Category 4: Library Stubs Missing (2 errors)

**Problem:** External library `toml` doesn't have type information.

**Fix:** Install type stubs or add `# type: ignore` comments

### setup_wizard.py (1 error)

```python
# Line 239
import toml  # Library stubs not installed for "toml"
# Fix: pip install types-toml
# Or:
import toml  # type: ignore
```

### interactive_mapper.py (1 error)

```python
# Line 350
import toml  # Library stubs not installed for "toml"
# Fix: Install types-toml
```

**Solution:** Run `pip install types-toml` in dev environment

**Total Time to Fix:** ~30 minutes

---

## Category 5: Argument Type Mismatches (7 errors)

**Problem:** Functions called with arguments of wrong type.

**Fix:** Either update call sites or update function signatures.

### transaction_enricher.py (2 errors)

```python
# Line 195
sanitize_description(description, None)
# Function expects: sanitization_patterns: list[Any]
# Passed: None
# Fix: Either update function signature to accept Optional, or pass proper list:
sanitize_description(description, [])

# Incompatible types in assignment (expression has type "float", variable has type "int")
# Already covered in Category 3

# statement_parser.py (1 error)
# Line 240
value = data["field_name"][index]
# data["field_name"] could be None (Any | None not indexable)
# Fix: Add None check:
if data["field_name"] is not None:
    value = data["field_name"][index]

# Line 311
best_match = max(candidates, key=matcher.match)
# matcher.match is overloaded function, can't be used as key
# Fix: Use lambda:
best_match = max(candidates, key=lambda x: matcher.match(x))
```

**Total Time to Fix:** ~2-3 hours

---

## Phase 1 Implementation Plan

### Week 1-2: Type Annotation Foundation
- Category 1: Add Optional types to all function parameters
- Category 4: Install types-toml or suppress warnings
- Category 2: Add explicit type hints to dict/list assignments

**Estimated:** 4-5 hours

### Week 2-3: Return Type Fixes
- Category 3: Fix return type mismatches (most time-consuming)
- Category 5: Fix argument passing and type mismatches

**Estimated:** 5-8 hours

### Verification
- Run `mypy src/` and verify 0 errors
- Update CI workflow to enforce mypy (currently non-blocking)
- Add type checking to pre-commit hooks

---

## Configuration for Phase 0 (Temporary)

**pyproject.toml:**
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
# Phase 0: Accept errors (will be fixed in Phase 1)
# Phase 1: Set ignore_errors = false
```

**CI Workflow (.github/workflows/ci.yml):**
```yaml
- name: Type check with mypy
  run: mypy src/ || true  # Don't fail in Phase 0
  # Phase 1: Change to: run: mypy src/  # Fail if errors
```

---

## Monitoring

Track mypy errors across phases:
- **Phase 0:** 42 errors (BASELINE - documented)
- **Phase 1:** Target 0 errors (ALL fixed)
- **Phase 2+:** Maintain 0 errors (add type checking to pre-commit)

---

## Summary

**Total Effort:** 9-13 hours for Phase 1  
**Complexity:** Medium (mostly mechanical fixes)  
**Impact:** High (improves code quality, IDE support, refactoring safety)

Recommend allocating 2-3 days of Phase 1 sprints to this work.

