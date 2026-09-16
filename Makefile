# StockPilot - single entry point for local install, verification and build.
# Works with GNU make (Linux/macOS, or `choco install make` / Git Bash on Windows).
# Every target below is the same command CI runs, so "make verify" == "CI is green".

SHELL := /bin/bash
BACKEND := backend
FRONTEND := frontend

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- install ----
.PHONY: install
install: install-backend install-frontend ## Install both stacks

.PHONY: install-backend
install-backend: ## Create a virtualenv and install backend deps
	cd $(BACKEND) && python -m venv .venv && \
		.venv/bin/python -m pip install --upgrade pip && \
		.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt

.PHONY: install-frontend
install-frontend: ## Install frontend deps from the lockfile
	cd $(FRONTEND) && npm ci

# ------------------------------------------------------------------ verify ----
.PHONY: lint
lint: lint-backend lint-frontend ## Lint both stacks

.PHONY: lint-backend
lint-backend: ## Ruff lint + format check (backend)
	cd $(BACKEND) && python -m ruff check app tests && python -m ruff format --check app tests

.PHONY: lint-frontend
lint-frontend: ## ESLint (frontend)
	cd $(FRONTEND) && npm run lint

.PHONY: format
format: ## Auto-fix formatting and import order (backend)
	cd $(BACKEND) && python -m ruff check --fix app tests && python -m ruff format app tests

.PHONY: typecheck
typecheck: typecheck-backend typecheck-frontend ## Type-check both stacks

.PHONY: typecheck-backend
typecheck-backend: ## mypy (backend)
	cd $(BACKEND) && python -m mypy app

.PHONY: typecheck-frontend
typecheck-frontend: ## tsc --noEmit (frontend)
	cd $(FRONTEND) && npm run typecheck

.PHONY: test
test: test-backend test-frontend ## Run both test suites

.PHONY: test-backend
test-backend: ## pytest (backend, in-memory SQLite)
	cd $(BACKEND) && python -m pytest

.PHONY: test-frontend
test-frontend: ## vitest run (frontend)
	cd $(FRONTEND) && npm test -- --run

.PHONY: test-cov
test-cov: ## pytest with a terminal coverage report
	cd $(BACKEND) && python -m pytest --cov=app --cov-report=term-missing

.PHONY: audit
audit: ## Dependency vulnerability audit for both stacks
	cd $(BACKEND) && python -m pip_audit -r requirements.txt
	cd $(FRONTEND) && npm audit --audit-level=high

.PHONY: verify
verify: lint typecheck test build ## Everything CI enforces, in one command

# ------------------------------------------------------------------- build ----
.PHONY: build
build: build-frontend ## Build production artifacts

.PHONY: build-frontend
build-frontend: ## Next.js production build
	cd $(FRONTEND) && npm run build

# --------------------------------------------------------------------- run ----
.PHONY: run-backend
run-backend: ## Start the API with autoreload
	cd $(BACKEND) && uvicorn app.main:app --reload --port 8000

.PHONY: run-frontend
run-frontend: ## Start the Next.js dev server
	cd $(FRONTEND) && npm run dev

.PHONY: db-up
db-up: ## Start the development PostgreSQL container
	docker compose -f docker-compose.dev.yml up -d db

.PHONY: migrate
migrate: ## Apply database migrations
	cd $(BACKEND) && alembic upgrade head

# ------------------------------------------------------------------- housekeeping ----
.PHONY: clean
clean: ## Remove caches and build output
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
	rm -rf $(BACKEND)/htmlcov $(BACKEND)/.coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(FRONTEND)/.next $(FRONTEND)/coverage