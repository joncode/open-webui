#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/jaco-stg-backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Starting backup: jaco_stg_${TIMESTAMP}.sql.gz"
pg_dump -h localhost -U jaco_stg jaco_stg | gzip > "$BACKUP_DIR/jaco_stg_${TIMESTAMP}.sql.gz"

# Prune old backups
find "$BACKUP_DIR" -name "jaco_stg_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: jaco_stg_${TIMESTAMP}.sql.gz"
echo "Backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/jaco_stg_*.sql.gz | tail -5
