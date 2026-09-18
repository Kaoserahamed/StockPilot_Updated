# Disaster Recovery

How StockPilot is backed up, restored and rehearsed. Backup scripts live in
`scripts/`; the day-to-day incident path is in [`runbook.md`](runbook.md).

---

## 1. What exists, and what can be lost

| Asset | Where | Backed up by |
|-------|-------|--------------|
| Business data (all PostgreSQL tables) | managed PostgreSQL / compose `pgdata` volume | `scripts/backup-db.sh` |
| Uploaded logos and product images | `UPLOAD_DIR` (`uploads/` volume) | **nothing automatic** — see §3 |
| Secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`, `GEMINI_API_KEY`, `SENTRY_DSN`) | environment / secrets manager | the secrets manager; never a dump |
| Release images | GHCR (`ghcr.io/kaoserahamed/stockpilot_updated:<version>`) | the registry, built from a tagged commit |
| Code and migrations | GitHub | git history |

**Targets** (proposals for a small deployment — agree and record the real ones
before you rely on them):

| Metric | Target |
|--------|--------|
| RPO (max data loss) | 24 h with daily dumps; 1 h with continuous archiving |
| RTO (time to restore service) | < 2 h from a verified dump, < 30 min for an image rollback |

Losing `SECRET_KEY` is not data loss but it is a full outage for sessions: every
issued token becomes invalid and every user logs in again
([`../security/secrets-management.md`](../security/secrets-management.md)).

## 2. Backups

```bash
# dump: pg_dump custom format, gzip -9, verbose; fails fast when DB_PASSWORD is unset
DB_PASSWORD=<secret> ./scripts/backup-db.sh ./backups
```

`backup-db.sh` honours `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
(all but the password have defaults) and writes
`backups/stockpilot_<YYYYmmdd_HHMMSS>.sql.gz`. There is deliberately **no
default password**: a silent placeholder would fail against production and leak
a weak credential into shell history and `ps` output.

Recommended cadence and retention:

| Frequency | Keep | Notes |
|-----------|------|-------|
| Daily | 30 days | off-host (object storage or another machine), not the same volume |
| Weekly | 12 weeks | a long-lived copy survives a slow corruption that daily retention would age out |
| Before every migration or release | until the next release is verified | the cheapest insurance in this repository |

```bash
# cron example: 02:15 daily, log to a file, alert on failure
15 2 * * * cd /srv/stockpilot && DB_PASSWORD="$(< /run/secrets/db_password)" \
  ./scripts/backup-db.sh /var/backups/stockpilot >> /var/log/stockpilot-backup.log 2>&1
```

## 3. File uploads

The dump contains no files. Back up `UPLOAD_DIR` (`uploads/`, mounted as the
`uploads` volume in `docker-compose.prod.yml`) alongside the database so restored
rows keep working:

```bash
tar -czf "backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz" uploads/
```

A missing file is not fatal — a logo/product image renders as a placeholder —
but a restored database with an empty `uploads/` looks broken to users.

## 4. Restore

`restore-db.sh` replaces the target database (`pg_restore --clean --if-exists
--no-owner --no-privileges`) after an interactive `y/N` confirmation.

```bash
DB_PASSWORD=<secret> ./scripts/restore-db.sh ./backups/stockpilot_20260918_021500.sql.gz
```

Procedure — never restore straight into a live production database if you can
avoid it:

1. **Stop writes** (scale the API to zero or put it in maintenance mode) so the
   restore is not fighting live traffic.
2. **Preserve the current state** before overwriting it, in case the backup is
   the wrong one: `DB_PASSWORD=<secret> ./scripts/backup-db.sh ./backups-pre-restore`.
3. **Restore** with the command above (or restore into a scratch database first
   and inspect it).
4. **Restore files** if the asset volume was lost: `tar -xzf uploads_<ts>.tar.gz`.
5. **Apply migrations** up to the release you are about to run:
   `cd backend && alembic upgrade head` (a dump from an older release needs this;
   see [`../database/migrations.md`](../database/migrations.md)).
6. **Start the app** and verify:
   - `GET /health` -> `200`, `GET /health/ready` -> `200`
   - log in as a real user, list products, open the dashboard
   - reconcile one product: `sum(inventory_transactions.quantity_change)` vs
     `products.quantity_on_hand`
   - confirm the newest sale in the UI matches the dump timestamp
7. **Re-enable traffic** and watch `/health/detailed` for new fingerprints.

`RESTORE` is destructive and irreversible: `--clean` drops and recreates objects
in the target database.

## 5. Scenario playbook

| Scenario | Action |
|----------|--------|
| A bad release (no data damage) | roll the image back — much faster than a restore: [`../deployment/rollback.md`](../deployment/rollback.md) |
| Accidental deletion of business rows | stop writes, restore the most recent dump into a **scratch** database, export the affected rows, and re-insert; avoid replacing live data for a small loss |
| Database volume/server lost | provision a new instance, restore the latest dump, `alembic upgrade head`, point `DATABASE_URL` at it, restart the API |
| Corrupted dump discovered late | fall back to the weekly copy; note the data gap in the incident report |
| Secret leaked or lost | rotate per [`../security/secrets-management.md`](../security/secrets-management.md); a new `SECRET_KEY` signs out every user |
| Image no longer in GHCR | rebuild from the tagged commit with the repository-root `Dockerfile` (`docker build -t ... .`) |
| Whole host/region lost | rebuild from git + GHCR + the off-host dump; the RTO is dominated by the database restore |

## 6. Rehearsal

A backup that has never been restored is a hypothesis. Rehearse **quarterly**
and after any change to the scripts or the deployment topology:

```bash
# 1. provision a scratch PostgreSQL (any host, never production)
docker run --rm -d --name dr-drill -e POSTGRES_PASSWORD=drill -p 55432:5432 postgres:16-alpine

# 2. restore into it
DB_HOST=localhost DB_PORT=55432 DB_NAME=postgres DB_USER=postgres DB_PASSWORD=drill \
  ./scripts/restore-db.sh ./backups/stockpilot_<ts>.sql.gz

# 3. verify row counts against the source
DB_HOST=localhost DB_PORT=55432 DB_NAME=postgres DB_USER=postgres DB_PASSWORD=drill \
  psql -c "SELECT count(*) FROM sales;" -c "SELECT count(*) FROM products;"

# 4. record the result (date, dump used, measured restore time, row counts)
docker rm -f dr-drill
```

Drill evidence to keep: the dump timestamp, the wall-clock restore time
(measured RTO), the row counts compared, and any step that did not match this
document. A drill that fails is a successful drill — fix the document and the
script, not the memory of the person who ran it.

## 7. Checklist

- [ ] Off-host daily dumps running, with failure alerting
- [ ] Retention agreed (daily 30 / weekly 12) and enforced by the storage lifecycle
- [ ] `uploads/` included in the backup set
- [ ] Secrets live in a secrets manager, not in the dumps or the repository
- [ ] Latest dump restored into a scratch database within the last quarter
- [ ] RTO measured and recorded; restore runbook updated with any deviation
- [ ] `SECRET_KEY` rotation procedure known and tested (it signs everyone out)