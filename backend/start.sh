#!/bin/bash
set -e

echo "🚀 Running migrations..."
alembic upgrade head || echo "⚠️ Migrations failed, continuing anyway."

echo "🚀 Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
