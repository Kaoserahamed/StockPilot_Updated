# Architecture

How StockPilot is put together, where code lives, and which rules keep the
layers honest. For the product scope (what it does), see
[`ProjectDetails.md`](ProjectDetails.md).

## System overview

```text
                    +-------------------+
                    |   Next.js (App    |
                    |   Router, :3000)  |
                    +--------+----------+
                             |  HTTPS/JSON (axios, Bearer + X-Business-Id)
                    +--------v----------+
                    |  FastAPI (:8000)  |
                    |  api -> services  |
                    |      -> models    |
                    +--------+----------+
                             | SQLAlchemy 2.0
                    +--------v----------+
                    |  PostgreSQL       |
                    |  (SQLite in tests)|
                    +-------------------+
```

- **Monorepo** (`docs/adr/0001-monorepo-layout.md`): `backend/` + `frontend/`
  versioned and released together.
- **Database:** PostgreSQL in every runtime; in-memory SQLite in tests
  (`docs/adr/0002-postgres-primary-sqlite-for-tests.md`).
- **AI:** deterministic SQL-backed answers first, Gemini as an optional
  rewriter (`docs/adr/0003-offline-first-ai.md`).

## Backend layering (`backend/app/`)

| Layer | Directory | May import | Must NOT import |
|-------|-----------|------------|-----------------|
| HTTP | `api/` (routers), `main.py` | `core`, `db`, `schemas`, `services`, `models` (read-only for tiny lookups) | contain business rules |
| Contracts | `schemas/` (Pydantic) | stdlib, Pydantic | `db`, `models`, `services` |
| Business logic | `services/` | `core`, `db`, `models` | `api`, `schemas` response types |
| Persistence | `models/` (SQLAlchemy) | `db`, stdlib | `api`, `services`, `schemas` |
| Cross-cutting | `core/` (config, security, deps, middleware, logging, errors) | stdlib + libs | `api`, `services`, `models` |
| Session | `db/` (engine, session, base) | `core` (settings) | everything else |

Rules of thumb:

1. Routers are **thin**: parse input (`schemas`), resolve the tenant
   (`core/deps.get_current_context`), call one service function, return.
2. Money and stock rules live in `services/` (`finance_service`,
   `inventory_service.apply_stock_change` — the single stock writer per
   `docs/adr/0005-single-stock-writer.md`).
3. Tenancy is enforced at the query level: every row read/write is filtered
   by `ctx.business_id`. Cross-tenant access returns `404`, never `403`
   (no id oracle).

## Tenancy & roles

- `User` ↔ `UserBusiness` ↔ `Business`: one login can belong to several
  businesses with a different role each.
- Request carries `Authorization: Bearer <access>` + `X-Business-Id`;
  `get_current_context` resolves `(user, business_id, role)` or `401`.
- Roles: **Owner** (everything incl. settings/plans/employees) >
  **Manager** (catalogue, trading, finance, reports) >
  **Cashier** (POS search + checkout only).
- Every mutation writes an `AuditLog` row (`services/audit.write_audit`).

## Data model (key tables)

- Identity: `users`, `user_businesses`, `businesses`, `password_reset_tokens`
- Catalogue: `categories`, `products`, `product_images`, `price_adjustments`
- Parties: `suppliers`, `customers`
- Trading: `purchases`, `purchase_items`, `sales`, `sale_items`, `returns`,
  `return_items`, `expenses`
- Stock: `inventory_transactions` (append-only ledger)
- Platform: `audit_logs`, `subscriptions`, `ai_recommendations`

Migrations live in `backend/alembic/`; the app also runs
`Base.metadata.create_all` on startup as a first-boot convenience
(Alembic is authoritative in production).

## Frontend layering (`frontend/`)

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| Routes | `app/` (20+ pages incl. `pos/`, `ai/`) | Composition only: fetch via services, render via components |
| Components | `components/` | Presentational UI (`ui.tsx`, `Shell`, `Toast`, `Skeleton`, `ErrorBoundary`) |
| Hooks | `hooks/` | `useFormValidation`, `useKeyboardShortcuts` (POS hotkeys), `useOptimisticUpdate` |
| State | `lib/store.tsx`, `lib/auth.tsx` | Session + business context, token storage |
| Services | `services/` | One typed module per domain calling `lib/api` (axios) — the only fetch layer |
| Types | `types/` | Shared domain types; no runtime code |
| Styling | Tailwind CSS | Utility-first, no CSS-in-JS runtime |

Data flow is one-way: `app/ → services/ → lib/api → backend`, with
TanStack Query caching reads and `useOptimisticUpdate` masking write latency.

## Observability & hardening

- `core/logging_config`: structlog-style JSON logs in production
  (`JSON_LOGS=true`), human-readable locally; every record carries a
  request id.
- `core/middleware`: `RequestContextMiddleware` (id + timing),
  `SecurityHeadersMiddleware` (HSTS/CSP/X-Frame…), `CacheHeadersMiddleware`.
- `core/exceptions`: uniform `{error: {code, message}}` envelope for every
  failure, including validation errors.
- `core/rate_limit` (slowapi) + `core/timeouts` bound abuse and hanging calls.
- Health: `/health` (liveness) and `/ready` (DB check) for orchestrators.

## Configuration

Twelve-factor via `core/config.Settings` (pydantic-settings): environment
first, `.env` fallback. Every key is documented in
`backend/.env.example`; the frontend needs only `NEXT_PUBLIC_API_URL`.
