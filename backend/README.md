# StockPilot backend

FastAPI + SQLAlchemy service. Run it locally with PostgreSQL, or run the
test suite with zero external services (in-memory SQLite).

## Install & run

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                 # fill in DATABASE_URL + SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

## Test

```bash
# The exact, fully pinned environment CI installs for the suite:
pip install -r requirements-dev.lock
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

`requirements-dev.txt` (direct pins) works too; `requirements-dev.lock` also pins
the transitive closure.

See [`tests/README.md`](tests/README.md) for fixtures, factories and the
coverage policy, and
[`../docs/development/testing.md`](../docs/development/testing.md) for the
repository-wide testing guide. Architecture and data flow live under
[`../docs/architecture/`](../docs/architecture/).

## Layout

| Path | What lives there |
|------|------------------|
| `app/api/` | Thin HTTP layer (`health.py`, `v1/*.py` routers) |
| `app/core/` | Config, security, deps, middleware, errors, logging, tracing |
| `app/db/` | Engine / session / declarative base |
| `app/models/` | SQLAlchemy models (schema truth) |
| `app/schemas/` | Pydantic request/response contracts |
| `app/services/` | Business logic (inventory, sales, finance, ai, pdf, audit) |
| `alembic/` | Migrations (`alembic upgrade head` in every runtime) |
| `tests/` | pytest suite, hermetic — no live DB required |
