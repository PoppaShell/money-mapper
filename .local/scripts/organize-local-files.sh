#!/bin/bash
# Script to organize local temporary files into .local/ directory
# This ensures all temporary files are in one place and never committed to git

echo "🗂️  Organizing local temporary files..."
echo ""

# Create .local directory structure
echo "Creating .local/ directory structure..."
mkdir -p .local/{reports/htmlcov,cache,sessions,notes}

echo "✓ Created .local directory structure"
echo ""

echo "Moving temporary files to .local/..."

# Coverage reports → .local/
for file in .coverage coverage.xml; do
    if [ -f "$file" ]; then
        mv "$file" .local/
        echo "✓ Moved: $file → .local/"
    fi
done

# Test results → .local/reports/
for pattern in '*_test_results.txt' 'test_output.txt' 'mypy_errors.txt'; do
    for file in $pattern; do
        if [ -f "$file" ] && [ "$file" != "$pattern" ]; then
            mv "$file" .local/reports/
            echo "✓ Moved: $file → .local/reports/"
        fi
    done
done

# HTML coverage → .local/reports/htmlcov/
if [ -d "htmlcov" ]; then
    mv htmlcov .local/reports/
    echo "✓ Moved: htmlcov/ → .local/reports/"
fi

# Cache directories → .local/cache/
for dir in .pytest_cache .mypy_cache .ruff_cache; do
    if [ -d "$dir" ]; then
        mv "$dir" .local/cache/
        echo "✓ Moved: $dir/ → .local/cache/"
    fi
done

# Python __pycache__ → .local/cache/
find . -type d -name "__pycache__" | while read dir; do
    mkdir -p ".local/cache/__pycache__"
    mv "$dir" ".local/cache/" 2>/dev/null && echo "✓ Moved: $dir → .local/cache/"
done

echo ""
echo "📊 Cleanup Summary"
echo "✓ All temporary files organized in .local/"
echo "✓ Safe to delete .local/ anytime (auto-generated)"
echo "✓ Verify with: git status --short"
echo ""
echo "Next: Run git status to verify cleanup"
