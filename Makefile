.PHONY: help setup dev dev-api dev-frontend test lint format clean

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Setup
# ============================================================================

setup: ## Install all dependencies
	cd api && pip install -e ".[dev]"
	cd frontend && npm install
	pre-commit install

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

# ============================================================================
# Data
# ============================================================================

data-download: ## Download MovieLens 25M dataset
	bash scripts/download_data.sh

data-process: ## Run Spark ETL pipeline
	cd spark && python -m etl.pipeline

# ============================================================================
# Database
# ============================================================================

db-migrate: ## Run Alembic migrations
	cd api && alembic upgrade head

db-rollback: ## Rollback last migration
	cd api && alembic downgrade -1

db-revision: ## Create new migration (usage: make db-revision msg="add users table")
	cd api && alembic revision --autogenerate -m "$(msg)"

db-seed: ## Seed database with sample data
	cd api && python -m app.scripts.seed_db

db-reset: ## Drop and recreate database
	cd api && alembic downgrade base && alembic upgrade head

# ============================================================================
# ML Training
# ============================================================================

train-als: ## Train ALS model with MLflow
	cd spark && python -m models.train_als

export-models: ## Export models for serving
	cd spark && python -m models.export_als

# ============================================================================
# Development
# ============================================================================

dev: ## Start all services with Docker Compose
	docker compose up -d

dev-api: ## Start API in development mode
	cd api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend in development mode
	cd frontend && npm run dev

dev-down: ## Stop all Docker Compose services
	docker compose down

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	cd api && pytest tests/ -v

test-unit: ## Run unit tests only
	cd api && pytest tests/unit/ -v

test-integration: ## Run integration tests
	cd api && pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	cd api && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linters (ruff + mypy)
	cd api && ruff check app/ tests/
	cd api && mypy app/

format: ## Auto-format code
	cd api && ruff format app/ tests/
	cd api && ruff check --fix app/ tests/

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build all Docker images
	docker compose build

docker-push: ## Push images to registry
	docker compose push

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	rm -rf api/dist api/build api/*.egg-info
