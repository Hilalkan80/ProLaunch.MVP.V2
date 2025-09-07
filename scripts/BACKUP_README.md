# ProLaunch MVP Automated Backup System

## Overview
The automated backup system provides comprehensive backup capabilities for the ProLaunch MVP project, including Git operations, archive creation, and verification reporting.

## Features

### 1. Git Operations
- Automatically stages and commits all changes
- Creates annotated Git tags (default: v0.17.0)
- Pushes changes and tags to remote repository
- Handles existing tags gracefully

### 2. Archive Creation
- Creates timestamped tar.gz or zip archives
- Includes all AI system directories and critical files
- Preserves directory structure
- Supports both Windows and Unix systems

### 3. Verification & Reporting
- Calculates SHA256 checksums for all files
- Verifies archive integrity
- Generates comprehensive JSON and text reports
- Provides detailed backup summaries

## Usage

### Quick Start

#### Windows:
```batch
# Run with default settings (Git + tar archive)
scripts\run_backup.bat

# Skip Git operations (for testing)
scripts\run_backup.bat --skip-git

# Use zip format instead of tar
scripts\run_backup.bat --format zip

# Custom version tag
scripts\run_backup.bat --version v0.18.0

# Custom commit message
scripts\run_backup.bat --message "Feature: Add new AI capabilities"
```

#### Unix/Linux/Mac:
```bash
# Run with default settings
./scripts/run_backup.sh

# Skip Git operations (for testing)
./scripts/run_backup.sh --skip-git

# Use zip format instead of tar
./scripts/run_backup.sh --format zip

# Custom version tag
./scripts/run_backup.sh --version v0.18.0
```

### Direct Python Execution
```bash
# With all options
python scripts/automated_backup.py \
    --version v0.17.0 \
    --format tar \
    --message "Custom commit message" \
    --skip-git  # Optional
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--skip-git` | Skip Git operations (staging, commit, tag, push) | False |
| `--format` | Archive format: 'tar' or 'zip' | tar |
| `--version` | Git tag version to create | v0.17.0 |
| `--message` | Custom Git commit message | Auto-generated |

## Backup Contents

### AI System Directories
- `backend/src/ai/` - Core AI modules
- `prolaunch_prompts/` - Prompt templates and configurations
- `prolaunch_prompts/milestones/` - Milestone-specific prompts
- AI-related API routes and services

### Critical Files
- `.env.example` - Environment configuration template
- `docker-compose.yml` - Docker configuration
- `Makefile` - Build automation
- `README.md` - Project documentation
- `CLAUDE.md` - Claude AI guidance

## Output Files

All backup files are created in the `backups/` directory:

### Archive Files
- `prolaunch_backup_YYYYMMDD_HHMMSS.tar.gz` - Compressed tar archive
- `prolaunch_backup_YYYYMMDD_HHMMSS.zip` - ZIP archive (if selected)

### Report Files
- `backup_report_YYYYMMDD_HHMMSS.json` - Machine-readable JSON report
- `backup_report_YYYYMMDD_HHMMSS.txt` - Human-readable text report
- `backup.log` - Detailed operation log

## Report Contents

### JSON Report Structure
```json
{
  "timestamp": "20240907_143022",
  "version": "v0.17.0",
  "files_backed_up": ["list of all files"],
  "checksums": {
    "file_path": "sha256_hash"
  },
  "git_info": {
    "has_changes": true,
    "commit_hash": "abc123...",
    "tag": "v0.17.0",
    "tag_message": "Release message"
  },
  "archive_info": {
    "path": "backups/prolaunch_backup_20240907_143022.tar.gz",
    "size": 1048576,
    "type": "tar.gz",
    "checksum": "sha256_hash"
  },
  "verification": {
    "total_files": 150,
    "verified": true
  },
  "summary": {
    "total_files_backed_up": 150,
    "total_checksums_calculated": 150,
    "backup_successful": true
  }
}
```

## Error Handling

The backup system includes comprehensive error handling:

1. **Git Errors**: Continues with backup even if Git operations fail
2. **Missing Files**: Logs warnings but continues with available files
3. **Archive Errors**: Stops execution and reports failure
4. **Verification Errors**: Marks backup as failed in reports

## Logging

All operations are logged to:
- Console output (real-time progress)
- `backup.log` file (detailed debugging information)

Log levels:
- INFO: Normal operations
- WARNING: Non-critical issues (e.g., missing optional files)
- ERROR: Critical failures requiring attention

## Best Practices

1. **Regular Backups**: Run weekly or before major changes
2. **Version Management**: Use semantic versioning for tags
3. **Verification**: Always check reports after backup
4. **Storage**: Move archives to secure storage after creation
5. **Testing**: Use `--skip-git` flag for testing without affecting repository

## Troubleshooting

### Common Issues

#### "Python is not installed"
- Install Python 3.8 or higher
- Ensure Python is in system PATH

#### "Git operations failed"
- Check Git is installed and configured
- Verify remote repository access
- Use `--skip-git` to bypass Git operations

#### "Archive verification failed"
- Check disk space availability
- Verify file permissions
- Review backup.log for details

#### "Tag already exists"
- Script automatically handles existing tags
- Use different version with `--version` flag

## Security Considerations

1. **Sensitive Data**: The script excludes `.env` files (only includes `.env.example`)
2. **Checksums**: SHA256 used for file integrity verification
3. **Permissions**: Ensure backup directory has appropriate access controls
4. **Storage**: Store backups in secure, encrypted locations

## Requirements

- Python 3.8 or higher
- Git (for version control operations)
- 500MB+ free disk space
- Read access to project directories
- Write access to backups directory

## Support

For issues or questions:
1. Check `backup.log` for detailed error messages
2. Review the generated reports in `backups/` directory
3. Ensure all requirements are met
4. Contact the development team with error logs