#!/bin/sh
flask db upgrade

: "${GUNICORN_WORKERS:=3}"
: "${GUNICORN_THREADS:=2}"
: "${GUNICORN_TIMEOUT:=60}"
: "${GUNICORN_KEEPALIVE:=5}"

exec gunicorn \
  -b 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --keep-alive "${GUNICORN_KEEPALIVE}" \
  wsgi:app
