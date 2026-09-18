# ADR 0001 — Backend + frontend in one monorepo

- **Date:** 2026-09-16
- **Status:** Accepted

## Context

StockPilot ships a FastAPI API and a Next.js UI that evolve together: every
backend phase (catalogue, purchases, POS, finance, AI) has a matching
frontend surface. Two repositories would force lock-step PRs and version
skew between the API contract and its only consumer.

## Decision

Keep `backend/` and `frontend/` in a single repository with one CI pipeline,
one issue tracker, and one release tag covering both halves.

## Consequences

- One `git clone` gives a contributor everything; `make install` sets up both.
- CI can gate a backend contract change on the frontend build in the same run.
- Release tags (`v1.0.0`) always describe a known-good backend+frontend pair.
- The tradeoff (larger checkout, mixed toolchains) is handled with per-stack
  ignore rules, lockfiles, and working-directory-scoped CI jobs.
