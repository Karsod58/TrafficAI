@echo off
echo ========================================
echo Creating Fresh Git Repository
echo This will remove old git history with large files
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Backup current .git folder
if exist .git.backup (
    echo Removing old backup...
    rmdir /s /q .git.backup
)
echo Moving .git to .git.backup...
move .git .git.backup

echo.
echo Step 2: Initialize fresh git repository
git init
git branch -M main

echo.
echo Step 3: Add all files (venv and node_modules excluded by .gitignore)
git add .

echo.
echo Step 4: Create initial commit
git commit -m "Initial commit: Bengaluru Traffic AI System with video upload feature"

echo.
echo Step 5: Add remote (update with your GitHub URL)
echo.
echo IMPORTANT: Run this command manually with your repo URL:
echo git remote add origin https://github.com/Karsod58/TrafficAI.git
echo.

echo.
echo ========================================
echo DONE!
echo ========================================
echo.
echo Next steps:
echo 1. Verify files: git ls-files ^| findstr venv
echo    (should return nothing)
echo.
echo 2. Add remote:
echo    git remote add origin https://github.com/Karsod58/TrafficAI.git
echo.
echo 3. Push to GitHub:
echo    git push -f -u origin main
echo.
echo Note: Use -f (force) because this is a fresh repo
echo.
pause
