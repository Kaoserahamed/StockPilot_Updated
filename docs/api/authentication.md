# Authentication & API Access

How a client authenticates, how tenancy is resolved, which role may call what,
and the error contract every endpoint shares.

- **Base URL:** `https://<your-domain>/api/v1` (local: `http://localhost:8000/api/v1`)
- **Protocol:** HTTPS only outside local development
- **Format:** JSON, `Content-Type: application/json`
- **Contract:** [`openapi.yaml`](openapi.yaml) (generated from the app) +
  [`stockpilot-api.postman_collection.json`](stockpilot-api.postman_collection.json)
- **Interactive docs:** `/docs` and `/redoc` — **disabled when
  `ENVIRONMENT=production`**

## 1. Required headers

| Header | When | Value |
|--------|------|-------|
| `Authorization` | every endpoint except `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/forgot-password`, `/auth/reset-password` and the `/health*` probes | `Bearer <access_token>` |
| `X-Business-Id` | optional; required in practice for a user with more than one membership | numeric business id |
| `X-Request-Id` | optional | echoed back for log correlation |
| `X-CSRF-Token` | *not enforced today* — see §7 | matches the `csrf_token` cookie |

If `X-Business-Id` is omitted, the first active membership is used. A business
the user does not belong to returns `403 No access to this business`; a row
that belongs to another business returns `404` (no id oracle).

## 2. Token model

| Token | Lifetime | Claim | Used at |
|-------|----------|-------|---------|
| Access | 15 min (`ACCESS_TOKEN_EXPIRE_MINUTES`) | `type: "access"` | every authenticated endpoint |
| Refresh | 7 days (`REFRESH_TOKEN_EXPIRE_DAYS`) | `type: "refresh"` | `POST /auth/refresh` only |

Tokens are HS256 JWTs signed with `SECRET_KEY`. `core.security.decode_token`
always passes `algorithms=[settings.algorithm]` **and** verifies the `type`
claim, so a refresh token cannot be replayed as an access token and vice versa.
Passwords are hashed with bcrypt. See
[`../architecture/decisions/0004-jwt-access-refresh.md`](../architecture/decisions/0004-jwt-access-refresh.md).

## 3. Flows

### Register a business + owner

```http
POST /api/v1/auth/register
{
  "owner_name": "Ayesha Rahman",
  "email": "owner@example.com",
  "phone": "+8801700000000",
  "password": "<strong password>",
  "business_name": "Rahman Traders"
}
```

Creates `users` + `businesses` + an `Owner` row in `user_business` in one
transaction and returns the user (`201`). `email` or `phone` is required (else
`422`); a taken identifier returns `409`. The password policy is
`core/sanitization.py:validate_password_strength` — 8–128 characters with at
least one letter and one digit; see
[`../security/threat-model.md`](../security/threat-model.md) §Password policy.

### Log in

```http
POST /api/v1/auth/login
{"username": "owner@example.com", "password": "..."}
-> 200 {"access_token": "...", "refresh_token": "..."}
```

`username` accepts either the email or the phone number. A wrong password, an
inactive user or a user with no active membership all return the same
`401 Invalid credentials`.

### Refresh

```http
POST /api/v1/auth/refresh
{"refresh_token": "..."}
-> 200 {"access_token": "<new>", "refresh_token": "<new>"}
```

A new **pair** is issued. The old refresh token is not recorded or revoked —
these are stateless JWTs, so "rotation" means *issue another pair*, not
*detect reuse*.

### Log out

```http
POST /api/v1/auth/logout        # requires the access token
-> 200 {"message": "Logged out"}
```

Client-side only: the server holds no token state, so the client must discard
both tokens (`frontend/lib/session.ts`).

### Current user

```http
GET /api/v1/auth/me             # requires the access token
```

### Password reset

```http
POST /api/v1/auth/forgot-password   {"username": "owner@example.com"}
POST /api/v1/auth/reset-password    {"token": "<opaque>", "new_password": "..."}
```

A single-use `password_reset_tokens` row is created with a 1-hour expiry; the
message is generic, so it never says whether the account exists. In Phase 1 the
first call also returns `dev_token` **when the account exists** — see
[`../security/threat-model.md`](../security/threat-model.md) §Known gaps before
exposing this endpoint to untrusted traffic.

### Employees (Owner only)

`GET|POST /employees`, `PATCH /employees/{id}/role`,
`POST /employees/{id}/activate`, `POST /employees/{id}/deactivate`,
`POST /employees/{id}/reset-password`, `DELETE /employees/{id}`.

## 4. Roles and permissions

Role lives on `user_business.role` and is resolved into `ctx.role` per request;
the checks are inline in each router (`ctx.role not in (...)`), and a mismatch
is `403`.

| Role | May do |
|------|--------|
| **Owner** | everything, including employee lifecycle, business profile/settings, subscription and audit log |
| **Manager** | catalogue, parties, inventory adjustments, purchases, sales cancel, returns, expenses, finance, reports, analytics, AI |
| **Cashier** | POS search and checkout, plus creating/reading parties (`parties.py` accepts all three roles) |

Every read endpoint still requires a valid token and is tenant-filtered; the
`Owner`/`Manager` gates sit on the state-changing routes. Full per-route detail
is in [`openapi.yaml`](openapi.yaml).

## 5. Error contract

Every failure — including validation errors — uses one envelope:

```json
{
  "error": {
    "code": 422,
    "message": "Request validation failed",
    "details": { "fields": [] }
  }
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad request (business rule violated, e.g. insufficient stock) |
| 401 | Missing/invalid/expired credentials, or inactive user |
| 403 | Authenticated but not permitted (role, or business membership) |
| 404 | Not found **or** belongs to another tenant |
| 409 | Conflict (duplicate user, SKU, barcode) |
| 422 | Validation error |
| 429 | Too many requests — *declared, not enforced today* (§6) |
| 500 | Unhandled server error |
| 504 | Request exceeded its per-path timeout |

The response also carries `X-Request-Id` and `X-Response-Time-Ms`; quote the
request id when reporting an issue.

## 6. Rate limits

`REDIS_URL`, `RATE_LIMIT_DEFAULT` (100/minute) and `RATE_LIMIT_AUTH`
(5/minute) are defined in `core/config.py`, and `core/rate_limit.py` builds a
slowapi limiter (per-user key, fallback to IP) with Redis or in-memory storage.

**Status:** `setup_rate_limiting()` is not called from `app/main.py` today, so
the documented limits are configuration the deployment is expected to apply
(in-process or at the reverse proxy) rather than behaviour enforced by the
app. Treat the table below as the intended policy:

| Endpoint type | Intended limit |
|---------------|----------------|
| Default | 100 / minute per user |
| Auth (`/auth/login`, `/auth/register`) | 5 / minute per IP |
| AI | 10 / minute |
| Reports | 20 / minute |

Per-path request **timeouts** *are* enforced (`core/timeouts.py`): search 10 s,
checkout 15 s, default 30 s, reports/analytics 45 s, AI 60 s — exceeding one
returns `504`.

## 7. Versioning

The API is URL-versioned (`/api/v1`). Breaking changes require a new prefix; a
deprecated prefix is supported for **6 months** with a warning header. The
generated document version (`info.version`) tracks the app's `1.0.0` literal,
not the package version.

## 8. Endpoint catalogue

The authoritative, always-complete list is
[`openapi.yaml`](openapi.yaml) (80 paths, generated from the FastAPI app).
Groups:

| Group | Router | Highlights |
|-------|--------|------------|
| Auth & tenancy | `auth`, `businesses`, `employees` | register, login, refresh, logout, me, forgot/reset, profile, logo, staff |
| Catalogue | `categories`, `products` | CRUD, image upload, activate/deactivate, search |
| Parties | `parties` | suppliers + customers, history endpoints, balances |
| Inventory | `inventory` | overview, low/out-of-stock, ledger, adjust, price history |
| Purchasing | `purchases` | create/receive, pay, cancel |
| POS & sales | `pos`, `sales`, `invoices`, `returns` | barcode search, checkout, cancel, invoice + PDF, refunds |
| Finance | `expenses`, `finance` | expenses, revenue, COGS, profit |
| Reporting | `dashboard`, `analytics`, `reports` | dashboard, analytics, exports (`json`/`csv`/`xlsx`/`pdf`) |
| Platform | `settings`, `subscription`, `audit-logs` | business settings, plan + limits, audit trail |
| AI | `ai` | chat, insights, forecast, reorder, anomalies, recommendations |
| Probes | `health` | `/health`, `/health/live`, `/health/ready`, `/health/detailed` |

`backend/tests/test_api_contract.py` fails the build when a published route is
renamed, dropped or loses its response model, so this list cannot silently drift.

## 9. Security notes for clients

- Store tokens where XSS cannot reach them where possible; the app uses
  `localStorage` because POS terminals keep a shift-long session
  ([ADR 0004](../architecture/decisions/0004-jwt-access-refresh.md)).
- `POST /auth/logout` is client-side; there is no server-side revocation, so a
  stolen refresh token stays valid until it expires. Rotate `SECRET_KEY` to
  invalidate every token at once
  ([`../security/secrets-management.md`](../security/secrets-management.md)).
- Never put real secrets in `NEXT_PUBLIC_*` variables — they are inlined into
  the browser bundle at build time.
- Send `X-Request-Id` from your own client if you want to correlate a response
  with your logs; the API echoes it back.

## 10. Postman collection and regenerating the spec

Import [`stockpilot-api.postman_collection.json`](stockpilot-api.postman_collection.json)
for a ready-made request set.

`openapi.yaml` is generated from the running app and kept in the repository so
it can be reviewed and diffed. Regenerate it after changing a route, schema or
response model:

```bash
cd backend
python scripts/export_openapi.py          # writes ../docs/api/openapi.yaml
```

`backend/tests/test_api_contract.py` asserts the committed file still matches
`app.openapi()`, so a stale document fails the suite. Requires
`DATABASE_URL` and `SECRET_KEY` to be set (any value) because importing the app
builds the settings object.