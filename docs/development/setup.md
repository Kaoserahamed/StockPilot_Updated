# Development Setup

Everything needed to run StockPilot on a developer machine. For the checks a
change must pass, see [`testing.md`](testing.md); for the branching and commit
rules, [`git-workflow.md`](git-workflow.md).

---

## 1. Prerequisites

| Tool | Version | Needed for |
|------|---------|------------|
| Python | 3.11+ | API, pytest, ruff, mypy |
| Node.js | 20+ (`engines.node >=20`) | Next.js app, Vitest |
| npm | bundled with Node | frontend installs |
| Docker | any recent | PostgreSQL container, image builds (optional) |
| GNU make | any | the `make` shortcuts (optional on Windows) |

`make doctor` prints the versions it finds and checks that the committed
environment templates and the backend lockfile exist:

```bash
make doctor
```

## 2. Install

```bash
git clone https://github.com/Kaoserahamed/StockPilot_Updated.git
cd StockPilot_Updated
make install          # backend .venv (pinned deps) + frontend npm ci
```

Equivalent per-stack commands:

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# frontend
cd ../frontend
npm ci
```

A fresh clone can also run the backend suite from the repository root, which
uses the root `pyproject.toml` (`testpaths = ["backend/tests"]`):

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov
```

## 3. Configure

| File | Template | Required values |
|------|----------|-----------------|
| `backend/.env` | `backend/.env.example` | `DATABASE_URL`, `SECRET_KEY` |
| `frontend/.env.local` | `frontend/.env.example` | `NEXT_PUBLIC_API_URL` |
| `.env` (root, for compose) | `.env.example` | `POSTGRES_PASSWORD`, `SECRET_KEY`, `NEXT_PUBLIC_API_URL` |

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
cp .env.example .env                    # only needed for Docker compose
```

Generate real secrets locally; never commit a populated `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"    # SECRET_KEY
openssl rand -base64 32                                        # POSTGRES_PASSWORD
```

`ENVIRONMENT=production` or `staging` makes `core/config.py` reject a short or
placeholder `SECRET_KEY` at startup, so a weak secret fails fast instead of
shipping. The full key list is in
[`../security/secrets-management.md`](../security/secrets-management.md).

## 4. Run

```bash
# Terminal 1 - database (skip if PostgreSQL already runs on :5432)
make db-up                     # docker compose -f docker-compose.dev.yml up -d db

# Terminal 2 - API
cd backend && alembic upgrade head
uvicorn app.main:app --reload           # http://localhost:8000/docs

# Terminal 3 - web
cd frontend && npm run dev              # http://localhost:3000
```

Or the `make` equivalents: `make run-backend`, `make run-frontend`,
`make migrate`.

SQLite is not a supported runtime database — `DATABASE_URL` must point at
PostgreSQL. In-memory SQLite exists only inside the test suite
([ADR 0002](../architecture/decisions/0002-postgres-primary-sqlite-for-tests.md)).

## 5. Docker compose (whole stack)

```bash
cp .env.example .env            # fill in POSTGRES_PASSWORD / SECRET_KEY / NEXT_PUBLIC_API_URL
docker compose -f docker-compose.dev.yml up -d      # dev: reload + source mounts
docker compose -f docker-compose.prod.yml up --build # prod-shaped: db + api + web + nginx
```

Production compose refuses to start without `SECRET_KEY` and
`POSTGRES_PASSWORD` — there are no committed defaults. See
[`../deployment/production.md`](../deployment/production.md).

## 6. Dev container (VS Code)

Open the repository and run **Dev Containers: Reopen in Container**.
`.devcontainer/post-create.sh` installs both stacks from the committed manifests
and runs the backend suite once, so the container is ready on first launch with
no local Python or Node toolchain. Ports `3000` (web), `8000` (API) and `5432`
(PostgreSQL) are forwarded automatically.

## 7. Everyday commands

| Command | What it does |
|---------|--------------|
| `make verify` | lint + types + tests + build — exactly what CI runs |
| `make lint` / `make typecheck` / `make test` | one gate at a time, both stacks |
| `make test-cov` | pytest with a terminal coverage report |
| `make audit` | `pip-audit` + `npm audit --audit-level=high` |
| `make format` | `ruff check --fix` + `ruff format` |
| `make clean` | remove caches and build output |

Pre-commit hooks mirror the lint and format rules:

```bash
pip install pre-commit && pre-commit install
```

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `Field required ... database_url/secret_key` on import | `backend/.env` missing — copy it from `.env.example` |
| `SECRET_KEY is too weak for production` | `ENVIRONMENT` is `staging`/`production`; use a 32+ char random value |
| `alembic upgrade head` cannot connect | the `db` service is not up: `make db-up`, then retry |
| Frontend calls `http://localhost:8000` | set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` (it is inlined at build time) |
| `401` on every request | expired access token and a missing/invalid refresh token — clear `localStorage` and log in again |
| `404` on a row you just created | tenancy filter: the row belongs to another business (expected) |
| Docker build slow/offline | the root `Dockerfile` installs from `backend/requirements.lock` |