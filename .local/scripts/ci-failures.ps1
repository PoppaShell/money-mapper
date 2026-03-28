# CI Diagnostic Helper
# Gets only the FAILING step output from the latest CI run on the current branch.
#
# Instead of drowning in gh run view --log output (1000+ lines),
# this shows ONLY the failures that need fixing.
#
# Usage:
#   .\.local\scripts\ci-failures.ps1

Write-Host ""
Write-Host "Checking latest CI run on current branch..." -ForegroundColor Cyan

$branch = git branch --show-current

if (!$branch) {
    Write-Host "[ERROR] Not on a git branch" -ForegroundColor Red
    exit 1
}

Write-Host "   Branch: $branch" -ForegroundColor Yellow

# Get latest run ID
$runData = gh run list --branch $branch --limit 1 --json databaseId,conclusion,status 2>&1 | ConvertFrom-Json

if (!$runData) {
    Write-Host "[ERROR] No CI runs found for this branch" -ForegroundColor Red
    exit 1
}

$runId = $runData.databaseId
$conclusion = $runData.conclusion
$status = $runData.status

Write-Host "   Run ID: $runId" -ForegroundColor Yellow
Write-Host "   Status: $status" -ForegroundColor Yellow
Write-Host "   Conclusion: $conclusion" -ForegroundColor Yellow
Write-Host ""

if ($status -eq "completed") {
    if ($conclusion -eq "failure") {
        Write-Host "[FAILED] CI failed - Showing failed steps:" -ForegroundColor Red
        Write-Host ""
        gh run view $runId --log-failed
    } elseif ($conclusion -eq "success") {
        Write-Host "[SUCCESS] CI passed - No failures!" -ForegroundColor Green
    } else {
        Write-Host "[STATUS] CI Status: $conclusion" -ForegroundColor Yellow
    }
} else {
    Write-Host "[RUNNING] CI still running..." -ForegroundColor Yellow
    Write-Host "   Check status: gh run view $runId" -ForegroundColor Gray
}
