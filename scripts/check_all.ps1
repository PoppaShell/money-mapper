# Comprehensive local CI check script for PowerShell (Windows)
# Run before pushing to catch all issues locally

$ErrorActionPreference = "Continue"  # Don't exit on first error, collect all

$failed = 0
$checks = @()

Write-Host "🔍 Running comprehensive local checks..." -ForegroundColor Cyan
Write-Host ""

# 1. Ruff linting
Write-Host "1️⃣  Linting with ruff..." -ForegroundColor Yellow
if (python -m ruff check src/ 2>&1) {
    Write-Host "✓ Ruff linting passed" -ForegroundColor Green
    $checks += "ruff-check: PASS"
} else {
    Write-Host "✗ Ruff linting failed" -ForegroundColor Red
    $checks += "ruff-check: FAIL"
    $failed = 1
}
Write-Host ""

# 2. Ruff formatting
Write-Host "2️⃣  Checking code format with ruff..." -ForegroundColor Yellow
if (python -m ruff format src/ --check 2>&1) {
    Write-Host "✓ Code formatting check passed" -ForegroundColor Green
    $checks += "ruff-format: PASS"
} else {
    Write-Host "✗ Code formatting check failed" -ForegroundColor Red
    Write-Host "Run: ruff format src/ to auto-fix" -ForegroundColor Yellow
    $checks += "ruff-format: FAIL"
    $failed = 1
}
Write-Host ""

# 3. mypy type checking
Write-Host "3️⃣  Type checking with mypy..." -ForegroundColor Yellow
if (python -m mypy src/ 2>&1) {
    Write-Host "✓ Type checking passed" -ForegroundColor Green
    $checks += "mypy: PASS"
} else {
    Write-Host "✗ Type checking failed" -ForegroundColor Red
    $checks += "mypy: FAIL"
    $failed = 1
}
Write-Host ""

# 4. Bandit security check
Write-Host "4️⃣  Security check with bandit..." -ForegroundColor Yellow
if (python -m bandit -r src/ -ll 2>&1) {
    Write-Host "✓ Bandit security check passed" -ForegroundColor Green
    $checks += "bandit: PASS"
} else {
    Write-Host "✗ Bandit security check failed" -ForegroundColor Red
    $checks += "bandit: FAIL"
    $failed = 1
}
Write-Host ""

# 5. pip-audit dependencies
Write-Host "5️⃣  Auditing dependencies with pip-audit..." -ForegroundColor Yellow
if (python -m pip_audit 2>&1) {
    Write-Host "✓ Dependency audit passed" -ForegroundColor Green
    $checks += "pip-audit: PASS"
} else {
    Write-Host "✗ Dependency audit failed (warnings present)" -ForegroundColor Yellow
    $checks += "pip-audit: WARN"
    # Don't fail on pip-audit warnings, just inform
}
Write-Host ""

# 6. pytest tests
Write-Host "6️⃣  Running tests with pytest..." -ForegroundColor Yellow
if (python -m pytest tests/ -v --tb=short 2>&1) {
    Write-Host "✓ Tests passed" -ForegroundColor Green
    $checks += "pytest: PASS"
} else {
    Write-Host "✗ Tests failed" -ForegroundColor Red
    $checks += "pytest: FAIL"
    $failed = 1
}
Write-Host ""

# 7. Coverage check
Write-Host "7️⃣  Checking test coverage..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path ".local/reports/htmlcov" | Out-Null
if (python -m pytest tests/ --cov=src/money_mapper --cov-report=term-missing --cov-report=html:.local/reports/htmlcov --cov-report=xml:.local/reports/coverage.xml 2>&1) {
    Write-Host "✓ Coverage report generated at: .local/reports/htmlcov/index.html" -ForegroundColor Green
    $checks += "coverage: PASS"
} else {
    Write-Host "✗ Coverage check failed" -ForegroundColor Red
    $checks += "coverage: FAIL"
    $failed = 1
}
Write-Host ""

# Summary
Write-Host "═════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host "Check Results:" -ForegroundColor Cyan
foreach ($check in $checks) {
    if ($check -like "*PASS*") {
        Write-Host "  ✓ $check" -ForegroundColor Green
    } elseif ($check -like "*FAIL*") {
        Write-Host "  ✗ $check" -ForegroundColor Red
    } else {
        Write-Host "  ⚠ $check" -ForegroundColor Yellow
    }
}
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✅ All checks passed! Safe to push." -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Some checks failed. Fix issues before pushing." -ForegroundColor Red
    exit 1
}
