# Contributing to StockPilot

Thanks for taking the time to contribute. This document explains how to set up the project,
how work is organised, and the rules a change must satisfy before it is merged.

---

## 1. Ground rules

1. **Every behaviour change ships with a test.** A pull request that changes an API route,
   a service, or a React component without a corresponding test update will not be merged.
2. **One logical change per commit.** Do not mix formatting, refactoring, and features.
3. **CI must be green.** `lint`, `typecheck`, `test`, and `build` all run on every PR.
4. **Never commit secrets or build artifacts.** `.env`, `*.db`, `node_modules/`, `.next/`,
   `__pycache__/` are ignored - keep it that way.
5. **Keep the tracking document current.** Update `IMPLEMENTATION_PLAN.md` when you complete
   a milestone item.

---

## 2. Local development setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env               # then fill in DATABASE_URL and SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

### Or use the Makefile

```bash
make install     # installs both stacks
make lint        # ruff + eslint
make typecheck   # mypy + tsc
make test        # pytest + vitest
```

---

## 3. Running the checks locally (same commands CI runs)

```bash
# Backend
cd backend
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

If these pass locally, CI will pass.

---

## 4. Commit message convention

Use Conventional Commits with an imperative subject of at most 72 characters:

```text
<type>(<scope>): <subject>

<why this change is needed>
```

Allowed types: `feat`, `fix`, `test`, `ci`, `docs`, `chore`, `refactor`, `perf`, `sec`.

Examples:

```text
feat(products): reject duplicate SKU within the same business
test(products): cover duplicate SKU and barcode rejection
fix(pos): restock inventory when a sale is cancelled
ci: gate pull requests on ruff, mypy and pytest
docs: document the fresh-clone test command
```

---

## 5. Pull request checklist

- [ ] Branch is up to date with `main`
- [ ] `ruff check` and `ruff format --check` pass
- [ ] `mypy app` passes
- [ ] `pytest --cov=app --cov-report=term-missing` passes (no live DB required)
- [ ] `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` pass
- [ ] New behaviour has a test that fails without the change
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] `IMPLEMENTATION_PLAN.md` checkboxes updated
- [ ] No secrets, no build artifacts, no large binaries committed

---

## 6. Reporting issues

Please include the exact commands you ran, the full error output, and your OS / Python / Node
versions. Screenshots help for UI issues.