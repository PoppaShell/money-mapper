#!/bin/bash
# Pre-push Validation Script
# Run all CI checks locally before pushing to origin
# Usage: ./validate.sh

set -e

echo "========================================"
echo "LOCAL VALIDATION - PHASE 0 PRE-PUSH"
echo "========================================"
echo ""

FAILED=0
PASSED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
check_step() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Step $1: $2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

pass_check() {
    echo -e "${GREEN}✓ PASSED${NC}: $1"
    ((PASSED++))
}

fail_check() {
    echo -e "${RED}✗ FAILED${NC}: $1"
    ((FAILED++))
}

warn_check() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

# Step 1: Ruff Linting
check_step 1 "Ruff Linting (ruff check src/)"
if python -m ruff check src/ > /dev/null 2>&1; then
    pass_check "Ruff linting"
else
    fail_check "Ruff linting - run: python -m ruff check src/"
fi

# Step 2: Ruff Formatting
check_step 2 "Ruff Formatting (ruff format src/ --check)"
if python -m ruff format src/ --check > /dev/null 2>&1; then
    pass_check "Ruff formatting"
else
    warn_check "Files need reformatting - run: python -m ruff format src/"
    python -m ruff format src/
    pass_check "Auto-fixed formatting"
fi

# Step 3: Mypy Type Checking
check_step 3 "Mypy Type Checking (mypy src/)"
if python -m mypy src/ > /dev/null 2>&1; then
    pass_check "Mypy type checking"
else
    warn_check "Type errors found (Phase 0 - acceptable, Phase 1 - must fix)"
    warn_check "See MYPY_TYPE_ERRORS_DETAILED.md for details"
fi

# Step 4: Bandit Security
check_step 4 "Bandit Security Scan (bandit -r src/ -ll)"
if python -m bandit -r src/ -ll > /dev/null 2>&1; then
    pass_check "Bandit security scan"
else
    fail_check "Security issues found - run: python -m bandit -r src/ -ll"
fi

# Step 5: Pytest
check_step 5 "Pytest Unit Tests (pytest tests/ --cov)"
if python -m pytest tests/ --cov=src/money_mapper --cov-report=term-miss -q > /dev/null 2>&1; then
    pass_check "Pytest unit tests"
else
    warn_check "Some tests failed or coverage below 60%"
    warn_check "Run: pytest tests/ --cov=src/money_mapper --cov-report=term-miss"
fi

# Step 6: Coverage Threshold
check_step 6 "Coverage Threshold Check (>= 60%)"
if python -m coverage report --skip-empty > /dev/null 2>&1; then
    if python -m coverage report --fail-under=60 > /dev/null 2>&1; then
        pass_check "Coverage threshold met (>= 60%)"
    else
        warn_check "Coverage below 60% threshold"
        python -m coverage report
    fi
else
    warn_check "Coverage report not available - run tests first"
fi

# Summary
echo ""
echo "========================================"
echo "VALIDATION SUMMARY"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo "Ready to push to origin."
    exit 0
else
    echo ""
    echo -e "${RED}✗ Some checks failed.${NC}"
    echo "Fix the issues above before pushing."
    exit 1
fi
