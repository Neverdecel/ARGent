# ARGent Makefile
# Common development tasks

.PHONY: help install dev up down logs shell db-shell test lint format clean migrate ci check

# Default target
help:
	@echo "ARGent Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Install with dev dependencies"
	@echo ""
	@echo "Docker:"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make logs       - View logs (follow mode)"
	@echo "  make shell      - Shell into app container"
	@echo "  make db-shell   - PostgreSQL shell"
	@echo ""
	@echo "Development:"
	@echo "  make ci         - Run all checks (lint, typecheck, test)"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter (ruff)"
	@echo "  make format     - Format code (ruff)"
	@echo "  make typecheck  - Run type checker (mypy)"
	@echo ""
	@echo "Database:"
	@echo "  make migrate    - Run database migrations"
	@echo "  make migrate-create NAME=... - Create new migration"

# Setup
install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

# Docker commands
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec app bash

db-shell:
	docker compose exec postgres psql -U argent -d argent

# Development commands
test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/

# Run all checks (same as CI)
ci: lint typecheck test
check: ci

# Database
migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(NAME)"

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
