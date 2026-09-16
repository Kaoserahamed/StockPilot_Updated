# ADR 0004 — Short-lived access tokens + long-lived refresh tokens

- **Date:** 2026-09-16
- **Status:** Accepted

## Context

POS terminals stay logged in for full shifts on shared hardware, so tokens
live in `localStorage`. A single never-expiring token would be a standing
credential-theft risk; forcing full re-login every 15 minutes would be
unusable at a till.

## Decision

- **Access token:** 15-minute JWT (`type: "access"`), sent as
  `Authorization: Bearer …` on every call plus `X-Business-Id` for tenancy.
- **Refresh token:** 7-day JWT (`type: "refresh"`), usable only at
  `POST /auth/refresh`. The `type` claim is enforced so tokens cannot be
  replayed across endpoints.
- **Password reset:** single-use opaque token via `/forgot-password` →
  `/reset-password`; the response never reveals whether an account exists.

## Consequences

- A stolen access token is useful for minutes, not days.
- The frontend interceptor can silently refresh on 401 without operator action.
- Refresh-token theft is mitigated by short access-token life but not
  eliminated — token rotation on refresh is recorded as future work.
