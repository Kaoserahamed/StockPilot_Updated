# Production Deployment

How to build, deploy, and operate StockPilot in each environment. For the
release *cut* process (tag -> CI -> GHCR -> GitHub Release) see
[`ci-cd.md`](ci-cd.md). For rolling a bad deploy back, see
[`rollback.md`](rollback.md). For day-to-day incidents and health probes see
[`../operations/runbook.md`](../operations/runbook.md). For environment
variables see the root [`.env.example`](../../.env.example) and
[`backend/.env.example`](../../backend/.env.example).

## Environments

| Environment | Backend | Frontend | Database | Who deploys |
| ----------- | ------- | -------- | -------- | ----------- |
| Local dev | `uvicorn app.main:app --reload` (:8000) | `npm run dev` (:3000) | SQLite (tests) or `docker compose -f docker-compose.dev.yml up -d db` | Developer |
| Dev container | pre-installed, `make verify` runs on first launch | same | PostgreSQL forwarded on :5432 | Developer (VS Code) |
| Staging | container from GHCR tag | container or `npm run build` + static host | PostgreSQL, real secrets from env | Manual, reviewed |
| Production | container from GHCR tag (`latest` or pinned version) | container or static build behind reverse proxy | PostgreSQL, secrets from secrets manager / env | Manual, reviewed |

Deployment is deliberately **manual and reviewed** at every non-local stage.
The CI workflow (`.github/workflows/ci.yml`) never pushes to a runtime
environment on its own.

## Container images

Three Dockerfiles live in the repository:

| Dockerfile | What it builds | Where CI runs it |
| ---------- | -------------- | ---------------- |
| `Dockerfile` (repo root) | API image from locked `backend/requirements.lock` | `docker` job (root context) |
| `backend/Dockerfile` | API image from `backend/` context, also installed from the locked closure | `docker` job (backend context) |
| `frontend/Dockerfile` | Next.js static/SSR image | `docker` job (frontend context) |

The repository-root `Dockerfile` is the one used for releases: it installs
Python dependencies from the committed `backend/requirements.lock`, so the
published image is reproducible from the tagged commit. See
[`ci-cd.md`](ci-cd.md) §4 for the exact tag -> image flow.

Run a released image locally:

```bash
docker run --rm -p 8000:8000 --env-file .env ghcr.io/kaoserahamed/stockpilot_updated:0.1.0
curl -fsS http://localhost:8000/health
```

## Reverse proxy / production front-end

The repository includes an [`nginx.conf`](../../nginx.conf) that terminates TLS,
serves the frontend static build, and proxies `/api` to the backend. It is a
starting point, not a drop-in production config — adjust TLS certificates,
logging, rate limiting, and compression for your infrastructure.

A production deployment typically looks like:

```
Client → TLS-terminating reverse proxy (nginx / ALB / Cloudflare)
       → frontend static assets (or frontend container on :3000)
       → backend container on :8000 (proxy /api/* to it)
       → PostgreSQL
```

Do not expose the backend container's port 8000 directly to the internet.
The backend assumes it is behind a proxy that handles TLS and, where relevant,
sends `X-Forwarded-Proto` / `X-Forwarded-For`.

## Database migrations

Migrations are forward-only and live in
[`backend/alembic/versions/`](../../backend/alembic/versions/). Alembic is
authoritative in production; the app runs `Base.metadata.create_all` on first
boot only as a convenience for fresh local setups. The full workflow is in
[`../database/migrations.md`](../database/migrations.md).

```bash
cd backend
alembic upgrade head              # apply pending migrations
alembic revision --autogenerate -m "what changed"   # create a new migration
```

Before downgrading an image, check the migration chain — there is no automatic
downgrade path. See [`rollback.md`](rollback.md) and
[`../operations/runbook.md`](../operations/runbook.md).

## Secrets management

- **Never commit real secrets.** `.env`, `*.db`, and `uploads/*` are in
  `.gitignore`. The committed files are `.env.example` templates with
  placeholders.
- `backend/scripts/scan_secrets.py` fails CI on committed credential literals
  (AWS/GCP/GitHub/Slack/Stripe tokens, private keys, quoted password/secret/
  token assignments). Placeholders such as `changeme` or `${POSTGRES_PASSWORD}`
  are ignored.
- Production secrets (database password, `SECRET_KEY`, `GEMINI_API_KEY`,
  `SENTRY_DSN`) should come from the environment or a secrets manager, not
  from a checked-in `.env` file.
- If a secret is suspected leaked, rotate it and follow the revocation guidance
  in [`../../SECURITY.md`](../../SECURITY.md) §Key Rotation, then work through
  [`../security/secrets-management.md`](../security/secrets-management.md).