# Transition Documentation Report Generator

## Overview
This script generates a comprehensive transition documentation report for ProLaunch MVP, specifically designed for tracking Step 17 development milestones and system status.

## Features

### 1. Development Status Report
- Tracks completion of major systems:
  - Context Management (75% complete)
  - Citation Tracking (60% complete)
  - Milestone Infrastructure (30% complete)
  - M0 Processing Engine (50% complete)
- Checks for actual file existence
- Calculates overall progress percentage

### 2. Service Status Documentation
- Lists all Docker services and their status
- Includes container health checks
- Documents service dependencies
- Generates dependency graph in Mermaid format

### 3. Database Schema Export
- Connects to PostgreSQL database
- Exports current schema structure
- Documents migrations and version
- Includes vector storage setup (pgvector)
- Lists indexes and constraints

### 4. AI Component Inventory
- Documents LlamaIndex integration status
- Lists MCP (Model Context Protocol) adapters
- Includes model configurations
- Documents vector store setup

## Installation

### Basic Usage (Without Dependencies)
The script can run without optional dependencies but will have limited functionality:
```bash
python scripts/generate_transition_report.py
```

### Full Installation (Recommended)
For complete functionality, install required dependencies:
```bash
pip install -r scripts/requirements-report.txt
```

## Output Files

The script generates three output files:

1. **transition-log.md** - Comprehensive markdown report with:
   - Status badges
   - Progress charts
   - Detailed component tables
   - Service dependency graphs
   - Recommendations and next steps

2. **transition-log.json** - Structured JSON data for programmatic access

3. **transition_report.log** - Detailed execution logs

## Configuration

The script uses environment variables for database connection:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=prolaunch
DB_USER=postgres
DB_PASSWORD=postgres
```

## Report Sections

### Development Status
- Overall completion percentage with color-coded badges
- Component-level tracking for each system
- File existence validation
- Last modification timestamps

### Service Status
- Docker service health monitoring
- Port mappings
- Service dependencies visualization
- Container status tracking

### Database Schema
- Table structure documentation
- Column types and constraints
- Index definitions
- Vector extension status
- Migration history

### AI Components
- LlamaIndex configuration status
- MCP adapter inventory
- Model configurations
- Vector store setup

## Error Handling

The script includes comprehensive error handling:
- Gracefully handles missing dependencies
- Provides fallback data when services are unavailable
- Logs all errors to transition_report.log
- Continues execution even if individual components fail

## Status Indicators

### Progress Badges
- 🟢 Green: 75-100% complete
- 🟡 Yellow: 50-74% complete
- 🔴 Red: 0-49% complete

### Component Status Icons
- ✅ Complete
- 🔄 In Progress
- ⏳ Pending/Planning
- ❌ Not Found/Error

## Recommendations

The report automatically generates recommendations based on:
- Service health status
- Database connectivity
- Missing components
- Configuration issues

## Usage in CI/CD

The script can be integrated into CI/CD pipelines:
```yaml
- name: Generate Transition Report
  run: |
    pip install -r scripts/requirements-report.txt
    python scripts/generate_transition_report.py
    
- name: Upload Report Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: transition-reports
    path: |
      transition-log.md
      transition-log.json
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Ensure PostgreSQL is running
   - Check environment variables
   - Verify network connectivity

2. **Docker Status Unavailable**
   - Ensure Docker is running
   - Check Docker Compose configuration
   - Verify user has Docker permissions

3. **Unicode Encoding Errors (Windows)**
   - Script automatically configures UTF-8 encoding
   - If issues persist, set environment variable: `PYTHONIOENCODING=utf-8`

## Development

To extend the report generator:

1. Add new status tracking in `generate_development_status()`
2. Add new service checks in `document_service_status()`
3. Extend schema export in `export_database_schema()`
4. Add AI components in `inventory_ai_components()`

## License

Part of ProLaunch MVP V2 project.