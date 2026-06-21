@echo off
echo ========================================
echo Git Repository Cleanup Script
echo Removing large files from Git history
echo ========================================
echo.

cd /d "%~dp0"

echo Removing venv from git cache...
git rm -r --cached BengaluruTrafficAI-Backend/venv

echo Removing model weights from git cache...
git rm --cached BengaluruTrafficAI-Backend/yolo11s.pt
git rm --cached BengaluruTrafficAI-Backend/yolov8s.pt

echo Removing database from git cache...
git rm --cached BengaluruTrafficAI-Backend/bengaluru_traffic.db

echo Removing .env file from git cache...
git rm --cached BengaluruTrafficAI-Backend/.env

echo.
echo ========================================
echo Adding .gitignore changes...
echo ========================================
git add .gitignore
git add BengaluruTrafficAI-Backend/.gitignore

echo.
echo ========================================
echo Committing changes...
echo ========================================
git commit -m "Remove venv, model weights, and large files from git tracking"

echo.
echo ========================================
echo DONE!
echo ========================================
echo.
echo Next steps:
echo 1. Run: git push -u origin main
echo.
echo Note: Users will need to:
echo - Create their own venv: python -m venv venv
echo - Install packages: pip install -r requirements.txt
echo - Download model weights separately
echo.
pause
