# SYNC CONTRACT: This file and .github/workflows/ci.yml must stay in sync.
# When you change one, change the other in the same commit.
# Commands must be identical: same tool, same flags, same order.
#
# Purpose: Run the EXACT same checks locally that CI runs, using a clean virtual env.
# This ensures: "If it passes locally, it will pass in CI."
#
# Usage:
#   .\.local\scripts\check_all.ps1              # Run all checks with cached venv
#   .\.local\scripts\check_all.ps1 -Fresh       # Rebuild venv from scratch
#
# Exit codes:
#   0 = All checks passed (safe to push)
#   1 = One or more checks failed (fix issues before pushing)

param(
    [switch]$Fresh = $false
)

$ErrorActionPreference = "Stop"
$venvPath = ".local\.venv"
$passed = 0
$failed = 0

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       LOCAL CI CHECK SUITE (Clean Virtual Env)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Setup/refresh virtual environment
Write-Host "[SETUP] Setting up virtual environment..." -ForegroundColor Yellow
if ($Fresh -or !(Test-Path "$venvPath\Scripts\python.exe")) {
    Write-Host "  Removing old venv..." -ForegroundColor Gray
    if (Test-Path $venvPath) {
        Remove-Item -Recurse -Force $venvPath
    }
    Write-Host "  Creating fresh venv..." -ForegroundColor Gray
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [FAIL] Failed to create venv" -ForegroundColor Red
        exit 1
    }
}

# Activate venv
$activateScript = "$venvPath\Scripts\Activate.ps1"
& $activateScript

# Install dev dependencies from pyproject.toml
Write-Host "  Installing dependencies from pyproject.toml..." -ForegroundColor Gray
python -m pip install --upgrade pip -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Failed to upgrade pip" -ForegroundColor Red
    deactivate
    exit 1
}

python -m pip install -e ".[dev]" -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] Failed to install dev dependencies" -ForegroundColor Red
    deactivate
    exit 1
}
Write-Host "  [OK] Virtual environment ready" -ForegroundColor Green
Write-Host ""

# Step 2-8: Run the EXACT checks from ci.yml in the same order

# 2. Lint with ruff
Write-Host "[1/7] Lint with: ruff check src/" -ForegroundColor Yellow
python -m ruff check src/
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - run: ruff check src/ --fix" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 3. Format check with ruff
Write-Host "[2/7] Format check with: ruff format src/ --check" -ForegroundColor Yellow
python -m ruff format src/ --check
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - run: ruff format src/" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 4. Type check with mypy
Write-Host "[3/7] Type check with: mypy src/" -ForegroundColor Yellow
python -m mypy src/
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - fix type errors in src/" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 5. Security check with bandit
Write-Host "[4/7] Security check with: bandit -r src/ -ll" -ForegroundColor Yellow
python -m bandit -r src/ -ll
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - fix security issues (or add #nosec if intentional)" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 6. Audit dependencies with pip-audit
Write-Host "[5/7] Audit dependencies with: pip-audit --ignore-vuln CVE-2026-4539" -ForegroundColor Yellow
python -m pip_audit --ignore-vuln CVE-2026-4539
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - dependency vulnerability found" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 7. Run tests with pytest
Write-Host "[6/7] Run tests with: pytest tests/ -v --tb=short" -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [PASS]" -ForegroundColor Green
    $passed++
} else {
    Write-Host "  [FAIL] - fix failing tests" -ForegroundColor Red
    $failed++
}
Write-Host ""

# 8. Coverage check
Write-Host "[7/7] Coverage check with: pytest --cov and coverage report" -ForegroundColor Yellow
python -m pytest tests/ --cov=src/money_mapper --cov-report=term-missing
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [FAIL] - tests did not complete" -ForegroundColor Red
    $failed++
} else {
    python -m coverage report --fail-under=36
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] - coverage >= 36%" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "  [FAIL] - coverage below 36% threshold" -ForegroundColor Red
        $failed++
    }
}
Write-Host ""

# Summary
Write-Host "==========================================================" -ForegroundColor Gray
Write-Host "                   CHECK SUMMARY" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Gray
Write-Host ""
Write-Host "  [PASS] $passed checks" -ForegroundColor Green
Write-Host "  [FAIL] $failed checks" -ForegroundColor Red
Write-Host ""

# Deactivate venv
deactivate

# Exit with appropriate code
if ($failed -eq 0) {
    Write-Host "[SUCCESS] All checks passed! Safe to push." -ForegroundColor Green
    Write-Host ""
    exit 0
} else {
    Write-Host "[ERROR] Some checks failed. Fix issues before pushing." -ForegroundColor Red
    Write-Host ""
    exit 1
}
