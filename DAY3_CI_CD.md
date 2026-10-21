# Day 3 CI/CD: Build / Test / Deploy Pipeline

## Repository
`StockPilot_Updated` — Inventory & POS SaaS (FastAPI + PostgreSQL + Next.js)

## Pipeline Overview
GitHub Actions CI/CD for FastAPI + Next.js monorepo (Makefile-driven).

### Trigger
- Push/Pull Request to `main`
- Manual workflow dispatch

### Stages

#### 1. Lint & Format
- Backend: Ruff/Black (Python)
- Frontend: ESLint + Prettier (TypeScript/Next.js)

#### 2. Typecheck
- Backend: `mypy` (Python strict mode)
- Frontend: `tsc --noEmit` (TypeScript)

#### 3. Test
- Backend: `pytest --cov=app --cov-report=term-missing` (80% coverage floor)
- Frontend: `npm test -- --run` (Vitest)
- Coverage enforcement: 80% floor for backend

#### 4. Build
- Backend: `pip install -r requirements.txt -r requirements-dev.txt`
- Backend: Docker image (`Dockerfile` in backend/)
- Frontend: `npm ci` + `npm run build` (Next.js)
- Multi-arch Docker images

#### 5. Security Scan
- `pip audit` / `safety` (Python dependencies)
- `npm audit` (frontend dependencies)
- Secret detection (no `DATABASE_URL`, no `SECRET_KEY` committed)
- Dependency vulnerability check

#### 6. Deploy (on merge to `main`)
- Build and push Docker images
- Deploy with `docker compose -f docker-compose.prod.yml up -d`
- Run migrations: `alembic upgrade head`
- Health check: `GET /docs` (Swagger UI)

### Quality Gates
- `make verify` (lint + types + tests + build) must pass
- 80% test coverage floor enforced
- TypeScript strict mode clean
- `mypy` clean
- No secrets committed

### Artifacts
- Docker images (backend + frontend)
- Test reports
- Coverage reports
- Alembic migration files
- Deployment URL

## Day 3 Outcome
CI/CD pipeline documented. No code changes. 0 PRs. Ready for Day 4 (project restructuring).
<!-- Feature branch commit for PR -->
