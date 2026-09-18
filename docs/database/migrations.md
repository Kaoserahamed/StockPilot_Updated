# Database Migrations

How a schema change is authored, reviewed, applied and verified. The schema
itself is documented in [`schema.md`](schema.md); the production deploy sequence
is in [`../deployment/production.md`](../deployment/production.md).

---

## 1. How the pieces fit together

| Piece | Path | Role |
|-------|------|------|
| Models | `backend/app/models/*.py` | **schema truth** — `Base.metadata` is what autogenerate compares against |
| Alembic env | `backend/alembic/env.py` | overrides `sqlalchemy.url` with `settings.database_url`, so the migration always targets the configured database |
| Alembic config | `backend/alembic.ini` | `script_location = alembic`; its fallback URL line is **inert** because `env.py` overwrites it |
| Migrations | `backend/alembic/versions/` | forward-only history; one initial revision exists today |
| Startup convenience | `app/db/session.ensure_indexes()` + `Base.metadata.create_all()` | creates missing tables/indexes on boot for a fresh local run — **not** a substitute for migrations |

Because `env.py` reads `settings.database_url`, running Alembic under the wrong
environment is easy to do. Check the target before applying anything:

```bash
cd backend
alembic current          # revision the connected database is on
alembic history --verbose
```

## 2. Everyday commands

```bash
cd backend

alembic current                                   # what the DB is on
alembic upgrade head                              # apply every pending revision
alembic upgrade +1                                # apply exactly one
alembic downgrade -1                              # go back one (add -v to inspect first)
alembic revision --autogenerate -m "add supplier code"
alembic history --verbose                         # full chain, offline
alembic upgrade head --sql > upgrade.sql          # offline SQL for a DBA to review
```

`testpaths`/coverage never touch Alembic: the suite builds its schema from the
models on an in-memory SQLite database, so a migration mistake is not caught by
`pytest` — review it deliberately.

## 3. Authoring a migration

1. Change the model in `backend/app/models/` first.
2. Generate: `alembic revision --autogenerate -m "short imperative description"`.
3. **Read the generated file.** Autogenerate misses data migrations, renames
   (it emits drop+add), check constraints, and enum changes; fix them by hand.
4. Make it forward-safe for existing rows:
   - add columns as `nullable=True` (or with a `server_default`), backfill, then
     tighten to `NOT NULL` in a follow-up revision;
   - never drop a column the running code still selects;
   - keep `op.f(...)` index naming so index names stay deterministic.
5. Add the migration to the pull request together with the model change and the
   test that proves the new behaviour.
6. Update [`schema.md`](schema.md) if the shape changed, and add a
   `CHANGELOG.md` entry.

Rules for this repository:

| Rule | Why |
|------|-----|
| Forward-only in practice | there is no automatic downgrade path; a bad revision is fixed with a new revision |
| One logical change per revision | a failing `upgrade head` should point at one idea |
| Dialect-portable application code | tests run on SQLite (ADR 0002); dialect-specific SQL belongs in the migration |
| Never edit a migration already applied to a shared database | `alembic_version` would disagree with reality |

## 4. Applying in each environment

| Environment | Procedure |
|-------------|-----------|
| Local / dev container | `docker compose -f docker-compose.dev.yml up -d db` then `alembic upgrade head` |
| Staging | back up first, then run `alembic upgrade head` from the release image before starting the new API container |
| Production | back up, **review** (`alembic upgrade head --sql`), apply, verify — see [`../deployment/production.md`](../deployment/production.md) |

The API container's entrypoint starts the app with `create_all()` +
`ensure_indexes()` enabled, which is safe but not a migration: a new column that
autogenerate would have added with a backfill will simply appear as `NULL`.
Always run `alembic upgrade head` as part of a deploy.

## 5. Verifying and recovering

```bash
alembic current                     # must equal the head revision after a deploy
alembic check                       # fails when models and the DB have drifted apart
```

- **Migration failed halfway:** most DDL in PostgreSQL is transactional, so the
  revision is rolled back automatically. Re-read the error, fix the revision
  (if it has not reached a shared database) and retry.
- **Migration applied but the app is broken:** roll forward with a new revision
  or roll the **image** back ([`../deployment/rollback.md`](../deployment/rollback.md)).
  Do not hand-edit `alembic_version`.
- **Schema drift after a manual fix:** `alembic check` reports the difference;
  capture it in a revision so the next environment gets the same change.

## 6. Backups

Migrations are not a backup strategy. Take a dump first, and keep the
restore path rehearsed in
[`../operations/disaster-recovery.md`](../operations/disaster-recovery.md):

```bash
DB_PASSWORD=<secret> ./scripts/backup-db.sh ./backups
```