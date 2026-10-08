#!/bin/sh
set -e

if [ "$1" = "gunicorn" ]; then
    # Solo el servicio web aplica migraciones (evita carreras de DDL entre
    # web/worker/beat, que compartían `migrate` y fallaban con
    # "column ... already exists").
    python manage.py migrate --noinput
    # Genera los estáticos (el volumen de 'web' puede arrancar vacío)
    python manage.py collectstatic --noinput
else
    # worker/beat: esperan a que web termine de migrar (máx ~90 s).
    n=0
    until python manage.py migrate --check >/dev/null 2>&1; do
        n=$((n + 1))
        [ "$n" -ge 30 ] && break
        sleep 3
    done
fi

exec "$@"
