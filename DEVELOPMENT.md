# Development Workflow Guide

This guide explains how to avoid CI failures by running checks locally before pushing.

## Quick Start

### 1. Initial Setup (One-time)

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Verify installation
pre-commit run --all-files
```

### 2. Before Every Commit

The pre-commit hooks will **automatically** run on `git commit`. They will:
- ✅ Lint code with ruff
- ✅ Format code with ruff
- ✅ Type-check with mypy
- ✅ Security scan with bandit

If any check fails, your commit will be blocked. Fix the issues and try again.

```bash
# This will trigger pre-commit hooks automatically
git commit -m "Your message"
```

### 3. Before Every Push (Optional but Recommended)

Run the comprehensive check script to catch issues **before** pushing:

#### On Windows (PowerShell):
```powershell
./scripts/check_all.ps1
```

#### On macOS/Linux (Bash):
```bash
bash scripts/check_all.sh
```

This runs all CI checks locally:
1. **Ruff linting** - Find code quality issues
2. **Ruff formatting** - Verify code style
3. **mypy** - Type checking
4. **bandit** - Security vulnerabilities
5. **pip-audit** - Dependency vulnerabilities
6. **pytest** - Unit tests
7. **coverage** - Test coverage report

---

## Understanding Each Check

### 🔍 **Ruff (Linting & Formatting)**
Enforces code quality and style.

**Common fixes:**
```bash
# Auto-fix most issues
ruff check src/ --fix

# Auto-format code
ruff format src/
```

### 📝 **mypy (Type Checking)**
Ensures type annotations are correct.

**Common fixes:**
- Add type hints to function signatures
- Fix return type mismatches
- Cast `Any` types properly

### 🔒 **bandit (Security)**
Scans for common security vulnerabilities.

**Common issues:**
- Hardcoded passwords/secrets
- SQL injection risks
- Use of unsafe functions

### 📦 **pip-audit (Dependency Audit)**
Checks for known vulnerabilities in dependencies.

---

## Manual Checks

If you want to run specific checks without the hooks:

```bash
# Just linting
python -m ruff check src/

# Just type-checking
python -m mypy src/

# Just security
python -m bandit -r src/ -ll

# Just tests
python -m pytest tests/ -v

# Just coverage
python -m pytest tests/ --cov=src/money_mapper --cov-report=term-missing
```

---

## Troubleshooting

### Pre-commit hooks not running?

```bash
# Reinstall hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Hook failed but you want to skip it?

```bash
# Skip hooks (NOT RECOMMENDED)
git commit --no-verify -m "Message"

# But fix it immediately after!
python -m ruff check src/ --fix
```

### mypy errors are too strict?

Edit `pyproject.toml` under `[tool.mypy]` to adjust settings, but try to fix real issues first.

### Ruff wants to reformat my code?

```bash
# Auto-format everything
ruff format src/

# Then commit
git add -A
git commit -m "style: Auto-format with ruff"
```

---

## CI vs Local Checks

| Check | Local (pre-commit) | CI | Purpose |
|-------|-------------------|----|---------| 
| Ruff check | ✅ YES | ✅ YES | Code quality |
| Ruff format | ✅ YES | ✅ YES | Code style |
| mypy | ✅ YES | ✅ YES | Type safety |
| bandit | ✅ YES | ✅ YES | Security |
| pip-audit | ✅ YES | ✅ YES | Dependencies |
| pytest | ❌ NO | ✅ YES | Unit tests |
| coverage | ❌ NO | ✅ YES | Code coverage |
| actionlint | ✅ YES | ✅ YES | GitHub Actions |

**Key point:** Running `./scripts/check_all.ps1` locally replicates **all** CI checks!

---

## Recommended Workflow

```bash
# 1. Make changes to code
# ... edit files ...

# 2. Stage and commit (auto-runs pre-commit hooks)
git add .
git commit -m "feat: Add new feature"

# 3. Before pushing, run full check locally
./scripts/check_all.ps1

# 4. If all pass, push!
git push origin feature/my-feature

# 5. Create PR
gh pr create --base main --head feature/my-feature
```

---

## Tips for Faster Development

### Parallel checking
Run tests in parallel:
```bash
python -m pytest tests/ -n auto  # Requires pytest-xdist
```

### Cache management
Clear caches to force fresh checks:
```bash
rm -rf .mypy_cache .ruff_cache .pytest_cache
```

### Skip expensive checks
For quick iterations, you can skip slower checks:
```bash
# Just lint + type check (skip tests)
python -m ruff check src/ --fix
python -m mypy src/
```

---

## Adding New Dependencies

Always check for vulnerabilities:
```bash
pip install new-package
pip-audit  # Check for vulnerabilities
git add pyproject.toml
git commit -m "deps: Add new-package"
```

---

## Questions?

Refer to tool documentation:
- **Ruff**: https://docs.astral.sh/ruff/
- **mypy**: https://mypy.readthedocs.io/
- **bandit**: https://bandit.readthedocs.io/
- **pytest**: https://docs.pytest.org/
