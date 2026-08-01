#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="db_${DATE}.sql.gz"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

cd "$PROJECT_DIR"

# Load env for POSTGRES_USER / POSTGRES_DB
source .env 2>/dev/null || true

docker compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    "${POSTGRES_DB:-ai_cs}" \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

# Remove backups older than KEEP_DAYS days
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +"$KEEP_DAYS" -delete

echo "Backup OK: ${BACKUP_DIR}/${FILENAME}"
