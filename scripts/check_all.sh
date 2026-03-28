#!/bin/bash
# Comprehensive local CI check script
# Run before pushing to catch all issues locally

set -e  # Exit on first error

echo "🔍 Running comprehensive local checks..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

failed=0

# 1. Ruff linting
echo "${YELLOW}1️⃣  Linting with ruff...${NC}"
if python -m ruff check src/; then
    echo "${GREEN}✓ Ruff linting passed${NC}"
else
    echo "${RED}✗ Ruff linting failed${NC}"
    failed=1
fi
echo ""

# 2. Ruff formatting
echo "${YELLOW}2️⃣  Checking code format with ruff...${NC}"
if python -m ruff format src/ --check; then
    echo "${GREEN}✓ Code formatting check passed${NC}"
else
    echo "${RED}✗ Code formatting check failed${NC}"
    echo "${YELLOW}Run: ruff format src/ to fix${NC}"
    failed=1
fi
echo ""

# 3. mypy type checking
echo "${YELLOW}3️⃣  Type checking with mypy...${NC}"
if python -m mypy src/; then
    echo "${GREEN}✓ Type checking passed${NC}"
else
    echo "${RED}✗ Type checking failed${NC}"
    failed=1
fi
echo ""

# 4. Bandit security check
echo "${YELLOW}4️⃣  Security check with bandit...${NC}"
if python -m bandit -r src/ -ll; then
    echo "${GREEN}✓ Bandit security check passed${NC}"
else
    echo "${RED}✗ Bandit security check failed${NC}"
    failed=1
fi
echo ""

# 5. pip-audit dependencies
echo "${YELLOW}5️⃣  Auditing dependencies with pip-audit...${NC}"
if python -m pip_audit; then
    echo "${GREEN}✓ Dependency audit passed${NC}"
else
    echo "${RED}✗ Dependency audit failed${NC}"
    failed=1
fi
echo ""

# 6. pytest tests
echo "${YELLOW}6️⃣  Running tests with pytest...${NC}"
if python -m pytest tests/ -v --tb=short; then
    echo "${GREEN}✓ Tests passed${NC}"
else
    echo "${RED}✗ Tests failed${NC}"
    failed=1
fi
echo ""

# 7. Coverage check
echo "${YELLOW}7️⃣  Checking test coverage...${NC}"
if python -m pytest tests/ --cov=src/money_mapper --cov-report=term-missing; then
    echo "${GREEN}✓ Coverage report generated${NC}"
else
    echo "${RED}✗ Coverage check failed${NC}"
    failed=1
fi
echo ""

# Summary
echo "═════════════════════════════════════════════════════"
if [ $failed -eq 0 ]; then
    echo "${GREEN}✅ All checks passed! Safe to push.${NC}"
    exit 0
else
    echo "${RED}❌ Some checks failed. Fix issues before pushing.${NC}"
    exit 1
fi
