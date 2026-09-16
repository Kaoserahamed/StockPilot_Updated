# Runbook

Day-to-day operations for StockPilot. Development uses SQLite-backed tests;
every runtime (dev container, staging, prod) uses PostgreSQL.

## Environments

| Concern | Backend | Frontend |
|---------|---------|----------|
| Local API | `uvicorn app.main:app --reload` (`:8000`) | `npm run dev` (`:3000`) |
| Env files | `backend/.env` (from `.env.example`) | `frontend/.env.local` (from `.env.example`) |
| Database | `docker compose -f docker-compose.dev.yml up -d db`, then `alembic upgrade head` | — (calls the API at `NEXT_PUBLIC_API_URL`) |

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

## Health & observability

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
   closing the incident (rule 1 of `CONTRIBUTING.md`).
