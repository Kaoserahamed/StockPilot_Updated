# ADR 0002 — PostgreSQL in production, in-memory SQLite for tests

- **Date:** 2026-09-16
- **Status:** Accepted

## Context

The test suite must run on a fresh clone with no external services (see
`Modifications.md` M5), yet production needs a real multi-user RDBMS with
concurrent writers (POS terminals) and durable backups.

## Decision

- **Production / local runtime:** PostgreSQL (psycopg2 driver), migrated with
  Alembic. MySQL+pymysql stays as a legacy driver option only.
- **Tests:** in-memory SQLite via a `StaticPool` + `Session` override in
  `backend/tests/conftest.py`. No test ever touches the network or a server DB.

## Consequences

- `pytest` works with zero setup; CI needs no service containers.
- SQL must stay portable across both dialects: no Postgres-only constructs in
  ORM queries used by tests. Anything dialect-specific lives in a migration,
  not in application code.
- `detect_anomalies` and the finance aggregations were written against this
  constraint (plain `func.date / count / sum`, computed z-scores in Python).
