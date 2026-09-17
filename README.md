# StockPilot

**Inventory & POS SaaS for small businesses** - multi-tenant inventory management, point of sale,
purchasing, invoicing, finance reporting and AI-assisted insights.

Built with **FastAPI + PostgreSQL + SQLAlchemy** on the backend and **Next.js (App Router) +
TypeScript + TanStack Query + Tailwind CSS** on the frontend.

[![CI](https://github.com/Kaoserahamed/StockPilot_Updated/actions/workflows/ci.yml/badge.svg)](https://github.com/Kaoserahamed/StockPilot_Updated/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20%2B-brightgreen)

---

## Quickstart (fresh clone, no external services needed to run tests)

```bash
git clone https://github.com/Kaoserahamed/StockPilot_Updated.git
cd StockPilot_Updated

# --- One command per stack, and one for every gate ---
make install            # backend virtualenv (pinned deps) + frontend npm ci
make verify             # lint, types, tests and build - the exact CI commands

# --- Backend suite (in-memory SQLite; no database, no network, no API key) ---
pip install -r requirements.txt -r requirements-dev.txt   # root -> backend manifests
pytest                                                    # backend/tests, from the root
pytest --cov                                              # ... and enforce the 80% floor

# Equivalent, with an isolated virtualenv exactly like CI:
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing     # <- the canonical test command

# --- Frontend: install + verify ---
cd ../frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

The backend suite deliberately uses an **in-memory SQLite** database, so `pytest` works on a
machine that has never seen this project and has no PostgreSQL instance running.

### Running the apps locally

```bash
# Terminal 1 - database (optional, if PostgreSQL is not installed locally)
docker compose -f docker-compose.dev.yml up -d db

# Terminal 2 - backend
cd backend
cp .env.example .env        # fill in DATABASE_URL and SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload          # http://localhost:8000/docs

# Terminal 3 - frontend
cd frontend
cp .env.example .env.local
npm run dev                            # http://localhost:3000
```

### Containers

```bash
# Whole stack (PostgreSQL + API + web) in one command:
cp .env.example .env                   # set POSTGRES_PASSWORD, SECRET_KEY, NEXT_PUBLIC_API_URL
docker compose -f docker-compose.prod.yml up --build

# Or just the API image, built from the repository root with locked dependencies:
docker build -t stockpilot-api:local .
docker run --rm -p 8000:8000 --env-file .env stockpilot-api:local
curl -fsS http://localhost:8000/health
```

### Dev container (VS Code)

Open the repository and run **Dev Containers: Reopen in Container**.
`.devcontainer/post-create.sh` installs both stacks from the committed
manifests and runs the backend suite once, so the container is ready to work in
on first launch - no local Python or Node toolchain required. Ports `3000`
(frontend), `8000` (API) and `5432` (PostgreSQL) are forwarded automatically.

---

## Repository layout

```text
StockPilot_Updated/
|-- pyproject.toml      # root pytest / coverage / ruff / mypy config (gates run from here)
|-- requirements.txt    # root manifest -> backend/requirements.txt
|-- Dockerfile          # production API image (installs from the committed lockfile)
|-- .devcontainer/      # one-click dev environment (Python 3.11 + Node 20)
|-- backend/            # FastAPI service
|   |-- app/api/        #   HTTP layer: health + versioned routers (thin)
|   |-- app/core/       #   config, security, dependencies, middleware, logging, errors
|   |-- app/db/         #   engine / session / declarative base
|   |-- app/models/     #   SQLAlchemy models (schema truth)
|   |-- app/schemas/    #   Pydantic request + response contracts
|   |-- app/services/   #   business logic (inventory, sales, finance, ai, pdf, audit)
|   |-- alembic/        #   migrations
|   `-- tests/          #   pytest suite (unit + integration, in-memory DB)
|-- frontend/           # Next.js application (App Router)
|   |-- app/            #   routes
|   |-- components/     #   presentational + composite components
|   |-- hooks/          #   reusable React hooks
|   |-- lib/            #   api client, auth context, sanitisation, store
|   |-- services/       #   typed API service functions per domain
|   `-- types/          #   shared TypeScript domain types
|-- docs/               # API reference, architecture, runbook, testing, releasing
|-- scripts/            # backup / restore / maintenance (fail-fast, no default secrets)
|-- .github/workflows/  # CI: lint, types, tests, coverage, audits, secret scan,
|                       #     container builds and tag-triggered releases
`-- IMPLEMENTATION_PLAN.md
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the layered design and the multi-tenancy
model, and [`docs/API.md`](docs/API.md) for the endpoint reference.
---

## What the product does

| Domain | Capabilities |
|--------|--------------|
| Identity | Business registration, login, JWT access + refresh tokens, password reset |
| Tenancy & RBAC | Business profiles, owner/manager/cashier roles, employee lifecycle, audit log |
| Catalogue | Categories, products (SKU/barcode/brand/unit/prices), image upload, search, soft delete |
| Parties | Suppliers and customers with contact details, purchase/sales history, balances |
| Inventory | Stock movement ledger, low-stock alerts, manual adjustments, price-change history |
| Purchasing | Purchase orders, receiving into stock, supplier payables |
| POS & Sales | Fast checkout, barcode-driven search, discounts, invoices, cancellations, returns |
| Finance | Expenses, revenue, COGS, profit & loss, outstanding receivables/payables |
| Reporting | Dashboard metrics, sales/inventory/expense/profit reports, CSV + Excel export |
| AI | Assistant chat, business insights, demand forecasting, reorder recommendations, anomalies |

The full functional specification lives in [`docs/ProjectDetails.md`](docs/ProjectDetails.md).

---

## Environment variables

Backend (`backend/.env`) - see [`backend/.env.example`](backend/.env.example):

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | yes | SQLAlchemy connection string |
| `SECRET_KEY` | yes | JWT signing key |
| `CORS_ORIGINS` | yes | Comma-separated allowed origins |
| `GEMINI_API_KEY` | no | Enables AI features; AI endpoints degrade gracefully without it |
| `GEMINI_MODEL` | no | Model id used for AI calls |
| `ENVIRONMENT`, `LOG_LEVEL`, `JSON_LOGS` | no | Runtime and logging behaviour |

Frontend (`frontend/.env.local`) - see [`frontend/.env.example`](frontend/.env.example):

| Variable | Required | Purpose |
|----------|----------|---------|
| `NEXT_PUBLIC_API_URL` | yes | Base URL of the backend API |

A convenience template covering both stacks lives at the repository root:
[`.env.example`](.env.example).

---

## Quality gates

Everything below runs on every pull request, and again on `main`, via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml):

```bash
# backend
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# frontend
npm run lint
npm run typecheck
npm run test:coverage          # vitest, with coverage thresholds
npm run format:check
npm run build

# supply chain & hardening
pip-audit -r requirements.txt
npm audit --audit-level=high
python backend/scripts/scan_secrets.py     # fails on committed credentials
pip install -r backend/requirements.lock.txt   # proves the lockfile installs
docker build .                             # every Dockerfile is built in CI
```

| Gate | Floor |
|------|-------|
| Backend test coverage | 80% of `backend/app` (`fail_under` in `pyproject.toml` **and** `--cov-fail-under` in CI) |
| Frontend coverage | Vitest thresholds over `lib/`, `hooks/`, `services/`, `components/` |
| Backend suite | must pass on in-memory SQLite, no external services |
| Dependency audit | `pip-audit` and `npm audit --audit-level=high` must be clean |
| Secret scan | `backend/scripts/scan_secrets.py` must report nothing |

Pre-commit hooks mirror the lint and format rules:
`pip install pre-commit && pre-commit install`.

Version tags publish the API image to GHCR and open a GitHub Release - see
[`docs/RELEASING.md`](docs/RELEASING.md). Deploying stays a manual step.

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). The short version: one logical change per commit,
tests travel with the code, CI must be green, and never commit secrets.

---

## License

Proprietary - all rights reserved.