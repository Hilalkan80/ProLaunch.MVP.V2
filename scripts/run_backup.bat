@echo off
REM ProLaunch MVP Automated Backup Script (Windows)
REM Executes the Python backup script with proper error handling

echo ========================================
echo ProLaunch MVP Automated Backup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Change to project root directory
cd /d "%~dp0\.."

REM Create backups directory if it doesn't exist
if not exist "backups" mkdir backups

REM Run the backup script
echo Starting backup process...
echo.
python scripts\automated_backup.py %*

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Backup completed successfully!
    echo Check the backups directory for archives and reports
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Backup failed!
    echo Check backup.log for details
    echo ========================================
)

pause