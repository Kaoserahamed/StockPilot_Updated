# Changelog

All notable changes to StockPilot are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `docs/` reorganised into audience-scoped folders (see the README documentation
  map): `architecture/` (plus `decisions/` for the ADRs), `development/`, `api/`,
  `database/`, `deployment/`, `operations/` and `security/`.
- `docs/api/openapi.yaml`: the OpenAPI 3.1 contract generated from the running
  app and committed so it can be reviewed and diffed, with
  `backend/scripts/export_openapi.py` to regenerate it.
- `docs/architecture/data-flow.md`: request lifecycle, the per-endpoint stock
  write paths, AI flow and frontend data flow.
- `docs/development/setup.md` and `docs/development/git-workflow.md`.
- `docs/api/authentication.md`: token model, tenancy headers, RBAC, error
  contract and endpoint catalogue.
- `docs/database/schema.md` (table-by-table reference) and
  `docs/database/migrations.md`.
- `docs/deployment/ci-cd.md` and `docs/deployment/rollback.md`.
- `docs/operations/monitoring.md` and `docs/operations/disaster-recovery.md`.
- `docs/security/threat-model.md` and `docs/security/secrets-management.md`.
- `PyYAML==6.0.3` pinned in `backend/requirements.txt` (already in the lockfile
  via `uvicorn[standard]`) because the OpenAPI export imports it directly.

### Changed

- Existing documents were moved, not rewritten: `ARCHITECTURE.md` ->
  `docs/architecture/system-architecture.md`, `TESTING.md` ->
  `docs/development/testing.md`, `DEPLOYMENT.md` ->
  `docs/deployment/production.md`, `RUNBOOK.md` ->
  `docs/operations/runbook.md` and `adr/` ->
  `docs/architecture/decisions/`.
- `docs/RELEASING.md` was absorbed into `docs/deployment/ci-cd.md`,
  `docs/API.md` into `docs/api/authentication.md`, and the Postman collection
  moved to `docs/api/`.
- `backend/tests/test_api_contract.py` now asserts that
  `docs/api/openapi.yaml` matches `app.openapi()`, so the published contract
  cannot drift from the code.
- The architecture and data-flow documents record two drifts found while
  verifying them against the code: the trading paths write
  `quantity_on_hand` inline (only manual adjustments call
  `apply_stock_change`), and the rate-limit and CSRF middleware are implemented
  but not registered in `app/main.py`.

### Removed

- Build, test and type-check artifacts from the working tree (all untracked and
  already ignored): the root and backend `.mypy_cache/`, `.pytest_cache/`,
  `.ruff_cache/` and every `__pycache__/`; the root `.coverage`;
  `frontend/.next/`, `frontend/coverage/` and
  `frontend/tsconfig.tsbuildinfo`. `make clean` reclaims the same set.
- `.env.production.example`: an unused duplicate of the root `.env.example`
  (no document, workflow or compose file referenced it), together with its
  now-dead `!.env.production.example` entry in `.gitignore`.
- A stray empty `audit.json` at the repository root.

## [0.1.0] - 2026-09-17

### Added

- Repository bootstrap: root `.gitignore`, `.editorconfig`, `.env.example`,
  `IMPLEMENTATION_PLAN.md`, `CHANGELOG.md` and `CONTRIBUTING.md`.
- Backend (FastAPI): layered `api`/`core`/`db`/`models`/`schemas`/`services`
  packages, Alembic migrations, structured JSON logging, request-id middleware,
  error-tracking sink, `/health`, `/health/ready`, `/health/detailed`.
- Frontend (Next.js App Router): typed `services/` layer, hooks, shared
  components, POS/inventory/finance/reports/AI screens.
- Test suites: 25 pytest modules against an in-memory SQLite database and a
  Vitest + Testing Library suite for the frontend.
- Repository-root configuration so the whole monorepo is driven from one place:
  `pyproject.toml` (pytest + coverage + ruff + mypy), `requirements.txt`
  pointer manifest, `Dockerfile` (locked dependency install) and `.dockerignore`.
- `.devcontainer/` (Python 3.11 + Node 20 features, port forwarding and a
  one-shot `post-create.sh` bootstrap).
- `backend/scripts/scan_secrets.py`: provider-token, private-key and
  quoted-credential-literal scanner, wired into CI and into the test suite.
- Contract tests that keep the gates honest:
  `backend/tests/test_dependency_manifests.py`,
  `backend/tests/test_quality_gates.py`, `backend/tests/test_secret_scan.py`
  and `backend/tests/test_logging_config.py`.
- `docs/RELEASING.md` describing the tag -> CI -> GHCR image -> GitHub Release
  flow.

### Changed

- CI now runs, on every pull request and on `main`: backend lint/format/types,
  the backend suite with an enforced coverage floor, frontend lint/types/tests/
  build, dependency audits for both stacks, a reproducible lockfile install, a
  secret scan, and a container build for every Dockerfile.
- Version tags (`v*`) publish the API image to GHCR and open a GitHub Release;
  deploying remains a manual, reviewed step.
- Coverage is enforced rather than reported: `fail_under = 80` in the pytest
  configuration and on the CI command line, plus Vitest thresholds scoped to
  the unit-tested modules.
- `backend/requirements.lock` (runtime closure) and `backend/requirements-dev.lock`
  (runtime + tooling closure) are regenerated as plain UTF-8 text from pip's own
  resolver, and a canonical `*.lock` filename is now used for lockfile tooling.
- Frontend coverage configuration documents its scope (units are measured,
  route pages are smoke-tested by `tests/pages.test.ts` and `npm run build`).

### Fixed

- `docker-compose.yml` no longer publishes MySQL/root credentials: every secret
  comes from the environment and compose aborts when it is missing.
- `backend/tests/factories.py` no longer contains a hardcoded default password
  (environment variable or generated per process).
- `scripts/*.sh` fail fast instead of falling back to a placeholder database
  password.
- `frontend/vitest.config.ts` no longer starts with a UTF-8 BOM and ends with a
  newline.

[Unreleased]: https://github.com/Kaoserahamed/StockPilot_Updated/compare/v0.1.0...main
[0.1.0]: https://github.com/Kaoserahamed/StockPilot_Updated/releases/tag/v0.1.0