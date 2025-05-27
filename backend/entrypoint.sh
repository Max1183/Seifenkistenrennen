#!/bin/sh

set -e

DB_HOST_TO_CHECK="${DB_HOST:-db}"
DB_PORT_TO_CHECK="${DB_PORT:-5432}"
DB_USER_TO_CHECK="${DB_USER}"

echo "Warte auf PostgreSQL auf ${DB_HOST_TO_CHECK}:${DB_PORT_TO_CHECK}..."

export PGHOST="$DB_HOST_TO_CHECK"
export PGPORT="$DB_PORT_TO_CHECK"
export PGUSER="$DB_USER_TO_CHECK"

until pg_isready -q; do
  >&2 echo "PostgreSQL ist nicht verfügbar - schlafe"
  sleep 1
done

>&2 echo "PostgreSQL ist hochgefahren - fahre fort"

echo "Führe Datenbankmigrationen aus..."
python manage.py migrate --noinput

echo "Sammle statische Dateien..."
python manage.py collectstatic --noinput --clear

echo "Versuche, initialen Superuser zu erstellen..."
python manage.py create_initial_superuser

echo "Starte Gunicorn..."
exec "$@"