# StockPilot_Updated - Implementation Plan & Progress Tracker

> **Master tracking document.** Every milestone below is a checkbox list. Contributors MUST flip
> `[ ]` to `[x]`, fill in the commit SHA in the Commit Log, and update the Progress Summary after
> each completed step. Do NOT delete historical entries - this file is the audit trail.

- **New repository:** https://github.com/Kaoserahamed/StockPilot_Updated
- **Local path:** `E:\StockPilot_Updated`
- **Requirements source of truth:** `ProjectDetails.md` (FR-1 to FR-37, Phases 1-5, E2E flow)
- **Quality-bar source of truth:** `Modifications.md` (DataFactor re-score report)
- **Starting score:** 42.2 / 100 (grade D) - 27.8 points below the 70-point offer threshold
- **Deployment:** OUT OF SCOPE for this rebuild (no Azure). Docker/compose retained only for
  local production-parity verification.

---

## 1. Why this rebuild exists (gaps reported in `Modifications.md`)

| # | Category | Score | Reported gap | Priority |
|---|----------|-------|--------------|----------|
| 1 | Test Coverage | 15.0 | 6 spec files, 1:19 ratio, `ci_runs_tests=false`, no frontend tests | HIGH (~10 pts) |
| 2 | Architecture & Robustness | 58.0 | frontend/TS layering not evidenced, `error_tracking=null` | HIGH (~9 pts) |
| 3 | Code Cleanliness | 55.0 | `has_lint_config=false`, `linters_and_formatters=[]` | HIGH (~8 pts) |
| 4 | Docs & Onboarding | 55.0 | `env_example_file=null`, no changelog/contributing guide | MEDIUM |
| 5 | Dependency Health | 35.0 | only `frontend/package-lock.json`, no backend lock, `dep_update_tooling=none` | MEDIUM |
| 6 | CI/CD Maturity | 25.0 | deploy-only workflow, no PR gates, no lint/typecheck/test | HIGH |
| 7 | Security Hygiene | 45.0 | 6 x `DB_PASSWORD:-changeme` fallbacks, no dep audit in CI | MEDIUM |
| 8 | History & Maintenance | 20.0 | 16 commits, 1 author, ~4.5 h burst, no tags/releases | HIGH |

### 1.1 Required remediation checklist (each line maps to a scored item)

- [ ] `M1` Ship features together with their tests, in small focused commits
- [ ] `M2` Make install/build/test work from a fresh clone with no external services
- [ ] `M3` Grow commit history with paired tests (incremental, never bulk)
- [ ] `M4` `backend/requirements-dev.txt` + `[tool.pytest.ini_options]` pinning pytest, pytest-cov, httpx
- [ ] `M5` `conftest.py` uses in-memory SQLite / ephemeral fixtures (no live external DB)
- [ ] `M6` `Makefile` + `backend/README.md` documenting `pytest --cov=app --cov-report=term-missing`
- [ ] `M7` `.github/workflows/ci.yml` on `pull_request` with a `backend-test` job
- [ ] `M8` `frontend-check` job: `npm ci`, `npm run lint`, `npx tsc --noEmit`
- [ ] `M9` Cache pip + npm deps keyed on `requirements*.txt` / `package-lock.json` hashes
- [ ] `M10` Backend lockfile (`requirements.lock.txt`) with exact pins for fastapi/sqlalchemy/alembic/pydantic
- [ ] `M11` `.github/dependabot.yml` - weekly pip + npm + github-actions updates
- [ ] `M12` `backend/.env.example` complete (incl. `GEMINI_MODEL`) + `frontend/.env.example` + root `.env.example`
- [ ] `M13` Remove `:-changeme` from `scripts/*.sh`, fail fast when `DB_PASSWORD` is unset
- [ ] `M14` `grep -r changeme scripts/` returns zero matches
- [ ] `M15` `backend/pyproject.toml` with `[tool.ruff]` targeting `app` + `tests`
- [ ] `M16` `frontend/.eslintrc.json` (next/core-web-vitals) + `frontend/.prettierrc`
- [ ] `M17` Lint + typecheck steps wired into CI so PRs fail on violations
- [ ] `M18` Error tracking / observability evidence (`error_tracking` was null)
- [ ] `M19` `CHANGELOG.md` + `CONTRIBUTING.md` + root `README.md`
- [ ] `M20` Frontend test suite (report found none)
- [ ] `M21` Frontend layering evidence (`app/`, `components/`, `lib/`, `hooks/`, `services/`, `types/`)
- [ ] `M22` No committed secrets, no `temp.db` / `__pycache__` / `.next` artifacts
- [ ] `M23` Version tags / releases (`v0.1.0` ... `v1.0.0`)
- [ ] `M24` Dependency audit in CI (`pip-audit` + `npm audit`)
---

## 2. Target repository structure

```text
StockPilot_Updated/
|-- .github/
|   |-- workflows/
|   |   `-- ci.yml                  # PR gate: lint + typecheck + tests (backend & frontend) + audit
|   |-- dependabot.yml              # weekly pip + npm + github-actions updates
|   `-- PULL_REQUEST_TEMPLATE.md
|-- backend/
|   |-- app/
|   |   |-- api/                    # health.py, v1/*.py routers (thin HTTP layer)
|   |   |-- core/                   # config, security, deps, middleware, errors, logging, tracing
|   |   |-- db/                     # base.py, session.py
|   |   |-- models/                 # SQLAlchemy models (owner of schema truth)
|   |   |-- schemas/                # Pydantic request/response contracts
|   |   `-- services/               # business logic (inventory, sales, finance, ai, pdf, audit)
|   |-- alembic/                    # migrations
|   |-- tests/                      # pytest suite (unit + integration), no external services
|   |-- pyproject.toml              # ruff + pytest + mypy + coverage config
|   |-- requirements.txt            # high-level runtime deps
|   |-- requirements-dev.txt        # pinned test/lint tooling
|   |-- requirements.lock.txt       # full pinned lock set (generated)
|   |-- .env.example
|   |-- README.md
|   `-- Dockerfile
|-- frontend/
|   |-- app/                        # Next.js App Router routes
|   |-- components/                 # presentational + composite components
|   |-- hooks/                      # reusable React hooks
|   |-- lib/                        # api client, auth, sanitize, utils
|   |-- services/                   # typed API service functions per domain
|   |-- types/                      # shared TypeScript domain types
|   |-- tests/                      # vitest unit + component tests
|   |-- .eslintrc.json
|   |-- .prettierrc
|   |-- vitest.config.ts
|   |-- .env.example
|   |-- package.json
|   `-- Dockerfile
|-- scripts/                        # backup / restore / maintenance (fail-fast, no default secrets)
|-- docs/                           # API.md, ARCHITECTURE.md, RUNBOOK.md, TESTING.md, postman
|-- Makefile                        # single entry point for install/lint/test/build
|-- docker-compose.dev.yml
|-- docker-compose.prod.yml
|-- .env.example
|-- CHANGELOG.md
|-- CONTRIBUTING.md
|-- IMPLEMENTATION_PLAN.md          # this file
`-- README.md
```

---

## 3. Commit discipline (binding rules)

These rules come directly from the "How to raise your score" section of `Modifications.md`.

1. **One logical change per commit.** Never mix formatting, refactoring and features.
2. **Tests travel with the code.** Any commit touching `backend/app/api/v1/*.py` or a service MUST
   include its test file change in the same commit. A test-less feature commit is a scoring miss.
3. **Split large work:** schema -> service -> route -> test, as separate commits where possible.
4. **Conventional prefixes:** `feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`, `refactor:`, `sec:`.
5. **Subject line:** imperative, max 72 chars. Body explains *why*.
6. **Never commit:** `.env`, `*.db`, `__pycache__/`, `.next/`, `node_modules/`, `tsconfig.tsbuildinfo`.
7. **Tag releases** at the end of each phase: `v0.1.0` (Phase 1) ... `v1.0.0` (final).
8. **Spread across sessions.** History should look like sustained work, not a single burst.

---

## 4. Milestones

Status legend: `[ ]` todo, `[~]` in progress, `[x]` done.

### Milestone 0 - Bootstrap & repo hygiene

- [ ] `M0.1` Create new repo folder, `git init -b main`, add `origin` remote
- [ ] `M0.2` Root `.gitignore` (Python + Node + env + build artifacts)
- [ ] `M0.3` Root `.editorconfig` (consistent line endings / indent across the monorepo)
- [ ] `M0.4` Root `README.md` rewritten for fresh-clone onboarding
- [ ] `M0.5` Root `.env.example` (documented, placeholder-only)
- [ ] `M0.6` Move `Modifications.md` + `ProjectDetails.md` into `docs/` for traceability
- [ ] `M0.7` `CHANGELOG.md` (Keep-a-Changelog format, `Unreleased` section)
- [ ] `M0.8` `CONTRIBUTING.md` (workflow, commit rules, local dev, PR checklist)

### Milestone 1 - Tooling, lint, lockfiles, security hygiene

- [ ] `M1.1` `backend/pyproject.toml`: add `[tool.ruff]` + coverage config
- [ ] `M1.2` `backend/requirements.txt`: exact pins for fastapi / sqlalchemy / alembic / pydantic
- [ ] `M1.3` `backend/requirements-dev.txt` (pytest, pytest-cov, pytest-asyncio, httpx, ruff, mypy, pip-audit)
- [ ] `M1.4` Generate and commit `backend/requirements.lock.txt`
- [ ] `M1.5` `backend/.env.example` completed (adds `GEMINI_MODEL`, documents every setting)
- [ ] `M1.6` `frontend/.env.example` verified / normalised to placeholder-only values
- [ ] `M1.7` `frontend/.eslintrc.json` extending `next/core-web-vitals`
- [ ] `M1.8` `frontend/.prettierrc` + `.prettierignore` + `format` / `format:check` scripts
- [ ] `M1.9` `frontend` scripts: `lint`, `typecheck`, `test`, `test:coverage`
- [ ] `M1.10` Fix `scripts/*.sh` to fail fast instead of falling back to `changeme`
- [ ] `M1.11` `.github/dependabot.yml` for pip + npm + github-actions
- [ ] `M1.12` `.pre-commit-config.yaml` updated (ruff replaces black / isort / flake8)
- [ ] `M1.13` `Makefile` with install / lint / typecheck / test / test-cov / build targets
- [ ] `M1.14` Verify: `grep -r changeme scripts/` returns 0 matches

### Milestone 2 - CI/CD maturity (PR gates, no deploy)

- [ ] `M2.1` `.github/workflows/ci.yml`: `backend-test` job (pip cache, ruff, mypy, pytest --cov)
- [ ] `M2.2` `.github/workflows/ci.yml`: `frontend-check` job (npm cache, lint, tsc, vitest, build)
- [ ] `M2.3` `.github/workflows/ci.yml`: dependency audit jobs (`pip-audit`, `npm audit`)
- [ ] `M2.4` Triggers: `pull_request` + `push` to `main` + `workflow_dispatch`
- [ ] `M2.5` Retire the Azure deploy-only workflow from this repo
- [ ] `M2.6` `.github/PULL_REQUEST_TEMPLATE.md` encoding the CI checklist
### Milestone 3 - Backend test foundation

- [ ] `M3.1` `tests/conftest.py` rebuilt: in-memory SQLite, session fixtures, factories, auth helpers
- [ ] `M3.2` `tests/README.md` documenting `pytest --cov=app --cov-report=term-missing`
- [ ] `M3.3` `tests/factories.py` helpers to remove duplication across specs
- [ ] `M3.4` Verify the suite runs green from a clean checkout with no external services

### Milestone 4 - Backend feature tests per router / service (paired commits)

- [ ] `M4.1` `test_auth.py` - register / login / refresh / me / reset, validation + rate-limit edges
- [ ] `M4.2` `test_business.py` - profile CRUD, tenant isolation
- [ ] `M4.3` `test_employees.py` - create / list / role assignment / deactivate, RBAC denials
- [ ] `M4.4` `test_categories.py` - CRUD, deactivate, delete-guard when products attached
- [ ] `M4.5` `test_products.py` - CRUD, duplicate SKU / barcode rejection, search, activate
- [ ] `M4.6` `test_parties.py` - suppliers + customers CRUD, outstanding balances
- [ ] `M4.7` `test_inventory.py` - overview, low-stock, adjust, price-adjustment ledger
- [ ] `M4.8` `test_purchases.py` - purchase create, stock increment, supplier balance
- [ ] `M4.9` `test_sales_pos.py` - checkout, stock decrement, insufficient stock, cancel + restock
- [ ] `M4.10` `test_invoices.py` - invoice generation, numbering, PDF output
- [ ] `M4.11` `test_returns.py` - return flow, restock, refund accounting
- [ ] `M4.12` `test_expenses.py` and `test_finance.py` - revenue / COGS / profit aggregates
- [ ] `M4.13` `test_reports.py` and `test_analytics.py` - report endpoints, dashboard metrics
- [ ] `M4.14` `test_ai.py` - AI endpoints with Gemini mocked (no API key required)
- [ ] `M4.15` `test_settings_subscription.py` - business settings, plan / subscription limits
- [ ] `M4.16` `test_tenancy_rbac.py` - cross-business access denial per resource family
- [ ] `M4.17` `test_health_security.py` - `/health`, security headers, CSRF, error envelope shape

### Milestone 5 - Architecture & robustness hardening

- [ ] `M5.1` Error-tracking hook (`app/core/error_tracking.py`) wired into exception handlers
- [ ] `M5.2` Request-ID propagation end to end (middleware -> logs -> response header)
- [ ] `M5.3` `/health/live` + `/health/ready` (with DB probe) instead of a single `/health`
- [ ] `M5.4` Audit Pydantic validation coverage at every API boundary
- [ ] `M5.5` Structured logging test coverage; JSON formatter verified
- [ ] `M5.6` Move the root `audit-logs` endpoint out of `main.py` into `api/v1/audit.py`

### Milestone 6 - Frontend layering + test suite

- [ ] `M6.1` `frontend/types/` domain types; remove inline `any` usage
- [ ] `M6.2` `frontend/services/` typed API functions per domain (over `lib/api.ts`)
- [ ] `M6.3` Refactor pages to consume `services/` + `hooks/` instead of ad-hoc logic
- [ ] `M6.4` `frontend/tests/setup.ts` + `vitest.config.ts`
- [ ] `M6.5` Unit tests for `lib/sanitize.ts`, `lib/api.ts`, `hooks/*`
- [ ] `M6.6` Component tests for `Shell`, `ui`, `Toast`, `ErrorBoundary`, `Skeleton`
- [ ] `M6.7` Page smoke tests for auth, POS, products, inventory
- [ ] `M6.8` Verify `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build` all green

### Milestone 7 - Docs & onboarding

- [ ] `M7.1` Root `README.md`: fresh-clone quickstart with the exact test command
- [ ] `M7.2` `docs/ARCHITECTURE.md` - layered design, tenancy model, data flow
- [ ] `M7.3` `docs/API.md` refreshed against the real router surface
- [ ] `M7.4` `docs/RUNBOOK.md` - ops tasks, backups, migrations, incident basics
- [ ] `M7.5` `docs/TESTING.md` - how to run and interpret the suite + coverage

### Milestone 8 - Final verification & release

- [ ] `M8.1` Fresh-clone simulation: install -> lint -> typecheck -> test -> build, all green
- [ ] `M8.2` Coverage report captured and documented
- [ ] `M8.3` Zero committed secrets / artifacts (`git ls-files` audit)
- [ ] `M8.4` Tag `v1.0.0`, push `main` + tags to `origin`
- [ ] `M8.5` Update this file: all checkboxes `[x]`, progress 100%
- [ ] `M8.6` Map results back to the `Modifications.md` re-score checklist
---

## 5. Verification commands (run these to prove a milestone)

```bash
# ---------- Backend ----------
cd backend
pip install -r requirements.txt -r requirements-dev.txt
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing

# ---------- Frontend ----------
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm test -- --run
npm run build

# ---------- Repository hygiene ----------
grep -ri changeme scripts/ || echo "OK: no secret fallbacks"
git ls-files | grep -E "(__pycache__|\.next/|node_modules/|\.env$|temp\.db)" || echo "OK: no artifacts tracked"
```

```powershell
# Windows equivalents
cd E:\B\StockPilot_Updated\backend; ruff check app tests; pytest --cov=app --cov-report=term-missing
cd E:\B\StockPilot_Updated\frontend; npm ci; npm run lint; npx tsc --noEmit; npm test -- --run; npm run build
```

---

## 6. Commit log (append one row per commit, newest last)

| # | Date | SHA | Message | Milestone | Tests in same commit |
|---|------|-----|---------|-----------|----------------------|
| - | - | - | _(populated as commits land)_ | - | - |

---

## 7. Progress summary

| Milestone | Done / Total | % |
|-----------|--------------|---|
| M0 Bootstrap | 0 / 8 | 0% |
| M1 Tooling & hygiene | 0 / 14 | 0% |
| M2 CI/CD | 0 / 6 | 0% |
| M3 Test foundation | 0 / 4 | 0% |
| M4 Backend feature tests | 0 / 17 | 0% |
| M5 Robustness | 0 / 6 | 0% |
| M6 Frontend layering & tests | 0 / 8 | 0% |
| M7 Docs | 0 / 5 | 0% |
| M8 Final verification | 0 / 6 | 0% |
| **Overall** | **0 / 74** | **0%** |

> Update both the per-milestone rows and the Overall row whenever a checkbox flips.
> The Commit Log is append-only: every commit gets a row, no exceptions.

---

## 8. Cross-reference: DataFactor re-score target

| Scored category | Where the fix lives in this repo |
|-----------------|----------------------------------|
| Test Coverage | `backend/tests/*` (M3+M4), `frontend/tests/*` (M6), `.github/workflows/ci.yml` (M2) |
| Architecture & Robustness | `app/core/error_tracking.py` (M5.1), request-id middleware (M5.2), health split (M5.3), frontend layering (M6.1-M6.3) |
| Code Cleanliness | `backend/pyproject.toml [tool.ruff]` (M1.1), `frontend/.eslintrc.json` + `.prettierrc` (M1.7/M1.8) |
| Docs & Onboarding | `README.md` (M7.1), `docs/*` (M7.2-M7.5), `CHANGELOG.md` + `CONTRIBUTING.md` (M0.7/M0.8) |
| Dependency Health | `backend/requirements.lock.txt` (M1.4), pinned `requirements.txt` (M1.2), `.github/dependabot.yml` (M1.11) |
| CI/CD Maturity | `.github/workflows/ci.yml` (M2.1-M2.4), deploy workflow retired (M2.5) |
| Security Hygiene | `scripts/*.sh` fail-fast (M1.10/M1.14), `*.env.example` (M0.5/M1.5/M1.6), audit jobs (M2.3) |
| History & Maintenance | Commit discipline (section 3), tags `v0.1.0`-`v1.0.0` (M8.4) |

