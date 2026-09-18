#!/bin/bash
# StockPilot Database Backup Script
# Usage: ./scripts/backup-db.sh [backup_dir]
# Environment variables (or defaults):
#   DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-stockpilot}"
DB_USER="${DB_USER:-stockpilot}"
BACKUP_DIR="${1:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="stockpilot_${DATE}.sql.gz"

# SECURITY: There is deliberately NO default password. A silent placeholder
# fallback would produce confusing authentication errors against production
# and leak a weak credential into shell history and process listings.
# PGPASSWORD is ONLY sourced from the DB_PASSWORD env var, never defaulted.
: "${DB_PASSWORD:?DB_PASSWORD is not set. Export it before running this script; no default password is provided.}"
export PGPASSWORD="${DB_PASSWORD}"  # pragma: allowlist secret

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting backup of ${DB_NAME}..."
pg_dump \
  -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
  --format=custom --compress=9 --verbose \
  "$DB_NAME" | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "[backup] Complete: ${BACKUP_DIR}/${FILENAME}"
ls -lh "${BACKUP_DIR}/${FILENAME}"

