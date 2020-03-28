#!/usr/bin/env sh

PORT=${PORT:-8000}

gunicorn -w 4 -b 0.0.0.0:$PORT app:app --timeout=90