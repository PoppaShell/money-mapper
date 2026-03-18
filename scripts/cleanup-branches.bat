@echo off
REM Cleanup script to delete merged branches locally and remotely (Windows)

setlocal enabledelayedexpansion

echo.
echo 7F8C Cleaning up merged branches...
echo.

REM Fetch latest from remote
echo Fetching from origin...
git fetch origin

REM Delete remote branches that are merged to main
echo.
echo 219F Remote branches ^(merged to main^):
for /f "tokens=*" %%i in ('git branch -r --merged origin/main 2^>nul') do (
    set "branch=%%i"
    set "branch=!branch:origin/=!"
    if not "!branch!"=="main" if not "!branch!"=="HEAD -^> origin/main" (
        echo   Deleting !branch!...
        git push origin --delete !branch! >nul 2>&1 || echo     ^(Already deleted or protected^)
    )
)

REM Delete local branches that are merged to main
echo.
echo 219F Local branches ^(merged to main^):
for /f "tokens=*" %%i in ('git branch --merged main 2^>nul ^| findstr /v "main"') do (
    set "branch=%%i"
    set "branch=!branch:*=!"
    echo   Deleting !branch!...
    git branch -d !branch! >nul 2>&1 || echo     ^(Already deleted^)
)

REM Prune stale remote references
echo.
echo 219F Pruning stale remote references...
git remote prune origin

echo.
echo 2705 Cleanup complete!
echo.
