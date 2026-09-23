#!/bin/sh
set -e

RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
INTERVAL_SECONDS=${BACKUP_INTERVAL_SECONDS:-86400}
PGHOST=${PGHOST:-db}
PGPORT=${PGPORT:-5432}
PGUSER=${PGUSER:-clientesd}
PGDATABASE=${PGDATABASE:-clientesd}

echo "[backup] Iniciando loop: cada ${INTERVAL_SECONDS}s, retención ${RETENTION_DAYS} días (host=${PGHOST}:${PGPORT} db=${PGDATABASE})"

while true; do
    ts=$(date +%Y%m%d_%H%M%S)
    out="/backups/${PGDATABASE}_${ts}.dump"
    if pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -Fc -f "$out"; then
        echo "[backup] OK $(date) -> $out"
    else
        echo "[backup] ERROR $(date) pg_dump falló (¿db lista?)" >&2
    fi
    find /backups -name '*.dump' -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
    sleep "$INTERVAL_SECONDS"
done
