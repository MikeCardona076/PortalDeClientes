#!/bin/sh
set -e

# Aplica migraciones antes de arrancar el servicio
python manage.py migrate --noinput

# Genera los estáticos (el volumen de 'web' puede arrancar vacío)
if [ "$1" = "gunicorn" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
