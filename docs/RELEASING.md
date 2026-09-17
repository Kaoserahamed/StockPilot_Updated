# Releasing

How a version of StockPilot becomes a published artifact. The pipeline lives in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml); nothing here needs a
human at the keyboard except the tag push and the review that follows it.

## 1. Versioning

[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Change | Bump |
|--------|------|
| Breaking API or response-shape change | MAJOR |
| New endpoint, screen or capability (backwards compatible) | MINOR |
| Bug fix, dependency bump, documentation | PATCH |

Tags are annotated and prefixed with `v` (`v0.1.0`). Every release is cut from
`main` after CI is green - never from an unreviewed branch.

## 2. Before you tag

```bash
git switch main
git pull --ff-only
make verify                       # lint + types + tests + build, exactly what CI runs
python backend/scripts/scan_secrets.py
git status --short                # must be clean
```

`CHANGELOG.md` must have a section for the version you are about to tag, with
its date. CI enforces the gates; the changelog and the tag are the two things it
cannot check for you.

## 3. Tag and push

```bash
git tag -a v0.1.0 -m "StockPilot v0.1.0"
git push origin main
git push origin v0.1.0
```

## 4. What CI does with the tag

1. `backend-lint`, `backend-test`, `frontend-check` and `docker` run again on the
   tagged commit (a tag can never publish code that did not pass the gates).
2. The `release` job then:
   - builds the API image from the repository-root `Dockerfile` (dependencies
     installed from the committed `backend/requirements.lock.txt`),
   - pushes it to GHCR as
     `ghcr.io/kaoserahamed/stockpilot_updated:<version>`,
     `<major>.<minor>` and `latest`,
   - opens a GitHub Release with generated notes.

Deployment is deliberately out of scope: promoting the image to staging or
production is a manual, reviewed step (see [`RUNBOOK.md`](RUNBOOK.md)).

## 5. After the tag

```bash
# verify the published image (any machine with Docker)
docker run --rm -p 8000:8000 --env-file .env ghcr.io/kaoserahamed/stockpilot_updated:0.1.0
curl -fsS http://localhost:8000/health
```

Rollback: re-run the previous image tag; the database schema is forward-only, so
check `backend/alembic/versions/` before rolling a migration back.

## 6. Checklist

- [ ] `make verify` green locally
- [ ] Secret scan clean
- [ ] `CHANGELOG.md` has the dated version section
- [ ] Working tree clean and `main` pushed
- [ ] Annotated tag pushed
- [ ] `release` job green, image pulls, `/health` returns `200`
