@echo off
REM ProLaunch MVP Backup Restoration Script (Windows)

echo ========================================
echo ProLaunch MVP Backup Restoration
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Change to project root directory
cd /d "%~dp0\.."

REM Pass all arguments to the Python script
python scripts\restore_backup.py %*

pause