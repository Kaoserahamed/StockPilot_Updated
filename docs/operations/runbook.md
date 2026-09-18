# Runbook

Day-to-day operations for StockPilot. Development uses SQLite-backed tests;
every runtime (dev container, staging, prod) uses PostgreSQL.

Companions: [`monitoring.md`](monitoring.md) (what to watch and alert on),
[`disaster-recovery.md`](disaster-recovery.md) (backups and restore drills),
[`../deployment/rollback.md`](../deployment/rollback.md) (bad release),
[`../deployment/production.md`](../deployment/production.md) (deploy procedure).

## Environments

| Concern | Backend | Frontend |
|---------|---------|----------|
| Local API | `uvicorn app.main:app --reload` (`:8000`) | `npm run dev` (`:3000`) |
| Env files | `backend/.env` (from `.env.example`) | `frontend/.env.local` (from `.env.example`) |
| Database | `docker compose -f docker-compose.dev.yml up -d db`, then `alembic upgrade head` | — (calls the API at `NEXT_PUBLIC_API_URL`) |

## Releases and container images

- Cut a release from `main` when CI is green: annotated tag `vX.Y.Z`, then push
  `main` and the tag. Full checklist: [`../deployment/ci-cd.md`](../deployment/ci-cd.md).
- The tag runs the `release` job in `.github/workflows/ci.yml`, which publishes
  `ghcr.io/kaoserahamed/stockpilot_updated:<version>` and opens a GitHub Release.
- Run a specific build:
  `docker run --rm -p 8000:8000 --env-file .env ghcr.io/kaoserahamed/stockpilot_updated:0.1.0`
  (the repository-root `Dockerfile` installs from `backend/requirements.lock`).
- Rollback: start the previous image tag;
  [`../deployment/rollback.md`](../deployment/rollback.md) has the procedure and
  the reason migrations are rolled forward, never down
  ([`../database/migrations.md`](../database/migrations.md)).
- Deploying to an environment stays manual - the workflow never pushes to
  production on its own.

## Database

```bash
# backup (fails fast when DB_PASSWORD is unset — no default secrets)
DB_PASSWORD=<secret> ./scripts/backup-db.sh ./backups

# restore (interactive confirmation)
DB_PASSWORD=<secret> ./scripts/restore-db.sh ./backups/stockpilot_<ts>.sql.gz

# routine maintenance (reindex / analyze / vacuum + table sizes)
DB_PASSWORD=<secret> ./scripts/db-maintenance.sh

# migrations
cd backend && alembic upgrade head            # apply
cd backend && alembic revision --autogenerate -m "what changed"
```

Authoring rules, verification (`alembic current`, `alembic check`) and recovery
are in [`../database/migrations.md`](../database/migrations.md). Backup policy,
retention and restore drills are in
[`disaster-recovery.md`](disaster-recovery.md).

## Health & observability

For the metric/log signals to alert on, see [`monitoring.md`](monitoring.md).

- `GET /health` — liveness (process is up).
- `GET /health/live` — orchestrator alias of liveness.
- `GET /health/ready` — readiness; returns `503` unless `SELECT 1` succeeds.
- `GET /health/detailed` — dependency status plus the error-tracking summary
  (`backend/app/core/error_tracking.py`): counters, fingerprints, recent
  reports. Served without PII so it is safe to attach to a ticket.
- Every response carries `X-Request-Id` (caller-supplied or generated) and
  `X-Response-Time-Ms`; errors use the `{ error: { code, message } }` envelope
  with the request id for correlation.

## Incidents (basics)

1. Confirm scope: `curl /health/detailed` — database vs app vs downstream.
2. Find the fingerprint: recent reports list exception type, route and count.
3. Mitigate: restart the container; roll back the last deploy if the
   fingerprint started with it (`CHANGELOG.md` + tags).
4. Follow up: add/extend the regression test in `backend/tests/` before
   closing the incident (rule 1 of [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)).
