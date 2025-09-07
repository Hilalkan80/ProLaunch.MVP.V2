#!/bin/bash

# Get current timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p backups

# Create backup filename
BACKUP_FILE="backups/prolaunch_backup_$TIMESTAMP.sql"

# Backup database
echo "Creating database backup..."
docker-compose exec -T db pg_dump -U prolaunch prolaunch > "$BACKUP_FILE"

# Compress backup
echo "Compressing backup..."
gzip "$BACKUP_FILE"

# Remove backups older than 7 days
echo "Removing old backups..."
find backups -name "prolaunch_backup_*.sql.gz" -type f -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"