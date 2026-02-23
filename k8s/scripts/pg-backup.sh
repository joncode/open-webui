#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/jaco-backups"
RETENTION_DAYS=14
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Starting backup: jaco_${TIMESTAMP}.sql.gz"
pg_dump -h localhost -U jaco jaco | gzip > "$BACKUP_DIR/jaco_${TIMESTAMP}.sql.gz"

# Prune old backups
find "$BACKUP_DIR" -name "jaco_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: jaco_${TIMESTAMP}.sql.gz"
echo "Backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/jaco_*.sql.gz | tail -5
