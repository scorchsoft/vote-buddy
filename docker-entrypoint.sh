#!/bin/sh
flask db upgrade
exec gunicorn -b 0.0.0.0:8000 wsgi:app
