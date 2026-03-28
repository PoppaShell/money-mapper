.PHONY: help install setup lint format type-check security test coverage check-all clean pre-commit

# Default target
help:
	@echo "Money Mapper - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Install pre-commit hooks"
	@echo ""
	@echo "Checks (run locally before pushing):"
	@echo "  make lint         - Lint code with ruff"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Type check with mypy"
	@echo "  make security     - Security scan with bandit"
	@echo "  make test         - Run tests with pytest"
	@echo "  make coverage     - Run tests with coverage"
	@echo "  make check-all    - Run all checks (equivalent to CI)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean        - Remove cache files"
	@echo "  make pre-commit   - Run pre-commit on all files"
	@echo ""

# Installation
install:
	python -m pip install --upgrade pip
	pip install -e .[dev]
	pip install pre-commit

setup: install
	pre-commit install
	@echo "✅ Pre-commit hooks installed!"

# Individual checks (match CI workflow)
lint:
	@echo "🔍 Linting with ruff..."
	python -m ruff check src/

format:
	@echo "🎨 Checking code format with ruff..."
	python -m ruff format src/ --check

format-fix:
	@echo "🎨 Fixing code format with ruff..."
	python -m ruff format src/

type-check:
	@echo "📝 Type checking with mypy..."
	python -m mypy src/

security:
	@echo "🔒 Security check with bandit..."
	python -m bandit -r src/ -ll
	@echo ""
	@echo "🔒 Auditing dependencies..."
	python -m pip-audit

test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v --tb=short

coverage:
	@echo "📊 Running tests with coverage..."
	python -m pytest tests/ --cov=src/money_mapper --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "📊 Coverage report generated at: htmlcov/index.html"

# Comprehensive check (matches all CI checks)
check-all: lint format type-check security test coverage
	@echo ""
	@echo "✅ All checks passed!"

# Utilities
clean:
	@echo "🧹 Cleaning cache files..."
	rm -rf .mypy_cache .pytest_cache .ruff_cache htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete"

pre-commit:
	@echo "🔧 Running pre-commit on all files..."
	pre-commit run --all-files

# Quick development workflow
quick-check: lint type-check
	@echo "✅ Quick checks passed (lint + type-check only)"

# Development setup reminder
.DEFAULT_GOAL := help
