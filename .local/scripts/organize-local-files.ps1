# Script to organize local temporary files into .local/ directory
# This ensures all temporary files are in one place and never committed to git

Write-Host "🗂️  Organizing local temporary files..." -ForegroundColor Cyan
Write-Host ""

# Create .local directory structure
Write-Host "Creating .local/ directory structure..." -ForegroundColor Yellow
$directories = @(
    ".local",
    ".local/reports",
    ".local/reports/htmlcov",
    ".local/cache",
    ".local/sessions",
    ".local/notes"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "✓ Created: $dir"
    } else {
        Write-Host "✓ Exists: $dir"
    }
}

Write-Host ""
Write-Host "Moving temporary files to .local/..." -ForegroundColor Yellow

# Coverage reports → .local/
@(".coverage", "coverage.xml") | ForEach-Object {
    if (Test-Path $_) {
        Move-Item -Path $_ -Destination ".local/" -Force
        Write-Host "✓ Moved: $_ → .local/"
    }
}

# Test results → .local/reports/
@("*_test_results.txt", "test_output.txt", "mypy_errors.txt") | ForEach-Object {
    Get-ChildItem -Path $_ -ErrorAction SilentlyContinue | ForEach-Object {
        Move-Item -Path $_.FullName -Destination ".local/reports/" -Force
        Write-Host "✓ Moved: $($_.Name) → .local/reports/"
    }
}

# HTML coverage → .local/reports/htmlcov/
if (Test-Path "htmlcov") {
    Move-Item -Path "htmlcov" -Destination ".local/reports/" -Force
    Write-Host "✓ Moved: htmlcov/ → .local/reports/"
}

# Cache directories → .local/cache/
$cacheDirs = @(".pytest_cache", ".mypy_cache", ".ruff_cache")
foreach ($dir in $cacheDirs) {
    if (Test-Path $dir) {
        Move-Item -Path $dir -Destination ".local/cache/$dir" -Force
        Write-Host "✓ Moved: $dir/ → .local/cache/"
    }
}

# Python __pycache__ → .local/cache/
Get-ChildItem -Path "." -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    $destPath = ".local/cache/$($_.Name)"
    if (-not (Test-Path $destPath)) {
        Move-Item -Path $_.FullName -Destination $destPath -Force
        Write-Host "✓ Moved: $($_.FullName) → $destPath"
    }
}

Write-Host ""
Write-Host "📊 Cleanup Summary" -ForegroundColor Cyan
Write-Host "✓ All temporary files organized in .local/"
Write-Host "✓ Safe to delete .local/ anytime (auto-generated)"
Write-Host "✓ Verify with: git status --short"
Write-Host ""
Write-Host "Next: Run git status to verify cleanup" -ForegroundColor Green
