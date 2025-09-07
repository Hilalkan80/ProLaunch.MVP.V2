#!/bin/bash
# ProLaunch MVP Automated Backup Script (Unix/Linux/Mac)
# Executes the Python backup script with proper error handling

set -e  # Exit on error

echo "========================================"
echo "ProLaunch MVP Automated Backup"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Change to project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Create backups directory if it doesn't exist
mkdir -p backups

# Run the backup script
echo "Starting backup process..."
echo ""
python3 scripts/automated_backup.py "$@"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Backup completed successfully!"
    echo "Check the backups directory for archives and reports"
    echo "========================================"
else
    echo ""
    echo "========================================"
    echo "ERROR: Backup failed!"
    echo "Check backup.log for details"
    echo "========================================"
    exit 1
fi