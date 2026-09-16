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

# --- Backend: install + run the full test suite (in-memory SQLite, no DB required) ---
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

---

## Repository layout

```text
StockPilot_Updated/
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
|-- docs/               # API reference, architecture, runbook, testing, requirements
|-- scripts/            # backup / restore / maintenance (fail-fast, no default secrets)
|-- .github/workflows/  # CI (lint, typecheck, test, build, dependency audit)
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

Everything below runs on every pull request via
[`.github/workflows/ci.yml`](.github/workflows/ci.yml):

```bash
# backend
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing

# frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build

# supply chain
pip-audit -r requirements.txt
npm audit --audit-level=high
```

Pre-commit hooks mirror the lint and format rules:
`pip install pre-commit && pre-commit install`.

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). The short version: one logical change per commit,
tests travel with the code, CI must be green, and never commit secrets.

---

## License

Proprietary - all rights reserved.