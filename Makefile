.PHONY: help dev-up dev-down rebuild migrate migrate-create fmt lint test clean

help:
	@echo "Higgsfield Backend - Available Commands"
	@echo "========================================"
	@echo "dev-up          - Start all services (docker compose)"
	@echo "dev-down        - Stop all services"
	@echo "rebuild         - Rebuild images from scratch (no cache)"
	@echo "migrate         - Run database migrations"
	@echo "migrate-create  - Create new migration (use MSG=description)"
	@echo "fmt             - Format code with black"
	@echo "lint            - Run ruff linter"
	@echo "test            - Run pytest"
	@echo "clean           - Remove cache and temp files"

dev-up:
	docker compose up -d --build
	@echo "Waiting for services to be ready..."
	@sleep 5
	@make migrate

dev-down:
	docker compose down

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@make migrate

migrate:
	docker compose exec -T api alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

fmt:
	black backend/ tests/
	ruff check --fix backend/ tests/

lint:
	ruff check backend/ tests/
	mypy backend/

test:
	pytest tests/ -v --cov=backend --cov-report=term-missing

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

