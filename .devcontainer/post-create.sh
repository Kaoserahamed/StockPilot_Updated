#!/usr/bin/env bash
# =============================================================================
# StockPilot - dev container bootstrap
#
# Runs once when the container is created (`postCreateCommand` in
# devcontainer.json). It installs both stacks from the committed manifests and
# proves the backend suite runs, so a fresh container is ready in one step.
#
# Manual re-run after changing dependencies:
#     bash .devcontainer/post-create.sh
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[devcontainer] Installing the API dependencies (pinned) + test tooling..."
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt

echo "[devcontainer] Installing frontend dependencies from package-lock.json..."
npm --prefix frontend ci

echo "[devcontainer] Smoke-testing the backend suite from the repository root..."
python -m pytest -q

cat <<'EOF'
[devcontainer] Ready.
  make test           # backend + frontend suites
  make run-backend    # uvicorn on :8000
  make run-frontend   # Next.js on :3000
  make db-up          # PostgreSQL for local runs (docker-compose.dev.yml)
EOF
