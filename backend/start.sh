#!/bin/bash
set -e

echo "🚀 Starting internal PostgreSQL..."
pg_ctl -D /var/lib/postgresql/data -o "-p 5432" -l logfile start || true
sleep 3
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='app'" | grep -q 1 || psql -U postgres -c "CREATE DATABASE app"

echo "🚀 Running Alembic migrations..."
cd /app
alembic -c alembic.ini upgrade head || true

echo "🚀 Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
