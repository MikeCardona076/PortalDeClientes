#!/bin/sh
set -e

# Aplica migraciones antes de arrancar el servicio
python manage.py migrate --noinput

exec "$@"
