# Rollback

What to do when a release is live and wrong. The rule that shapes everything
below: **application code rolls back cleanly, the database does not.** Images
are immutable and tagged; migrations are forward-only.

Related: [`ci-cd.md`](ci-cd.md) (how the image was published),
[`production.md`](production.md) (deploy procedure),
[`../operations/runbook.md`](../operations/runbook.md) (incidents),
[`../database/migrations.md`](../database/migrations.md) (migration policy).

---

## 1. Decide first

| Symptom | Action |
|---------|--------|
| Elevated 5xx / failures with a new fingerprint (`/health/detailed`) | roll the image back |
| Wrong business behaviour, data still intact | roll the image back, then fix forward |
| A migration already applied and the old code cannot read the new schema | **roll forward** — do not downgrade the schema |
| Data corrupted by the bad release | stop writes, restore from the last verified dump ([`../operations/disaster-recovery.md`](../operations/disaster-recovery.md)) |

Ask two questions before touching anything:

1. **Did this version change the schema?** Compare
   `git diff v<previous>..v<current> -- backend/alembic/versions`.
2. **Can the previous image read the current schema?** If a column was dropped
   or renamed, it cannot. Then roll forward with a new patch release instead.

## 2. Roll the application image back

Identify the previous good tag (checklist: IAM/registry tags, GitHub Releases,
`CHANGELOG.md`), then:

```bash
# 1. Confirm the target image still exists and starts
docker pull ghcr.io/kaoserahamed/stockpilot_updated:0.1.0
docker run --rm -p 8000:8000 --env-file .env \
  ghcr.io/kaoserahamed/stockpilot_updated:0.1.0
curl -fsS http://localhost:8000/health/ready        # expect 200

# 2. Stop the bad container (keep it for logs), start the previous tag
docker stop stockpilot-api-bad
docker run -d --name stockpilot-api \
  -p 8000:8000 --env-file .env \
  ghcr.io/kaoserahamed/stockpilot_updated:0.1.0

# 3. Verify
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/health/detailed | head
```

For a compose deployment, the service builds from source
(`docker-compose.prod.yml` -> `build: ./backend`), so "rolling back" means
checking out the previous tag's commit and rebuilding, or pointing the service
at the published image:

```bash
git switch --detach v0.1.0
docker compose -f docker-compose.prod.yml up -d --build api
```

The frontend is stateless: redeploy the previous build (or previous static
bundle) the same way. `NEXT_PUBLIC_API_URL` is inlined at **build** time, so a
frontend image is only valid for the API URL it was built with.

## 3. Schema: forward-only

- Do **not** run `alembic downgrade` in production. Downgrade scripts are not
  written or reviewed for this repository, and a partially reverted schema is
  worse than a reverted image.
- Never hand-edit the `alembic_version` table; `alembic current` and the real
  schema would disagree from then on.
- If the bad release added a column the old code ignores, roll the image back and
  fix forward in the next release — the extra column is harmless.
- If the bad release *removed or renamed* something the old code needs, restore
  the shape with a new revision and release it as a PATCH.

## 4. After the rollback

1. Confirm recovery: `/health/ready` is `200`, the error fingerprint from
   `/health/detailed` stops incrementing, and a known-good business flow
   (e.g. a test checkout in staging) succeeds.
2. Freeze deploys until the cause is understood — `git log` between the two tags
   plus `CHANGELOG.md` is the change set.
3. Add the regression test that fails without the fix (rule 1 of
   `CONTRIBUTING.md`) and land it before re-releasing.
4. Cut a PATCH release, tag it, and follow [`production.md`](production.md)
   again — do not re-tag the same version.
5. Record what happened in `CHANGELOG.md` under the fixed version and, if
   customer-visible, in the incident notes.

## 5. Rollback checklist

- [ ] Previous image tag identified and verified to start locally
- [ ] `/health/ready` returns `200` on the rolled-back version
- [ ] Schema compatibility confirmed before or instead of the rollback
- [ ] No `alembic downgrade`, no manual `alembic_version` edits
- [ ] Frontend redeployed if the API contract or `NEXT_PUBLIC_API_URL` changed
- [ ] Regression test added and green
- [ ] PATCH release cut, tagged and deployed
- [ ] `CHANGELOG.md` entry written