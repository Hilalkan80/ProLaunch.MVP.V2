#!/bin/bash
# ProLaunch MVP Backup Restoration Script (Unix/Linux/Mac)

set -e  # Exit on error

echo "========================================"
echo "ProLaunch MVP Backup Restoration"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

# Change to project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Pass all arguments to the Python script
python3 scripts/restore_backup.py "$@"