#!/bin/bash

echo "Building Tailwind CSS..."
uv run python manage.py tailwind build

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
uv run gunicorn project.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
