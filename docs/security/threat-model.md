# Threat Model

A working model of what StockPilot protects, where trust changes, and which
threats are mitigated, accepted or still open. Policy and reporting live in
[`../../SECURITY.md`](../../SECURITY.md); secret handling in
[`secrets-management.md`](secrets-management.md).

---

## 1. Scope and assets

In scope: the FastAPI API, the Next.js frontend, the PostgreSQL database, the
upload volume and the CI/CD pipeline. Out of scope: the operating system, the
managed database provider's internal controls, and the user's device.

| Asset | Why it matters | Where it lives |
|-------|----------------|----------------|
| Business/trading data (sales, purchases, stock, finance) | the product's core value; per-tenant confidentiality | PostgreSQL, always filtered by `business_id` |
| Credentials | account takeover, lateral movement | bcrypt hashes in `users.hashed_password`; JWTs in client `localStorage` |
| `SECRET_KEY` | forges any token for any tenant | environment / secrets manager |
| `GEMINI_API_KEY` | billable third-party spend | environment / secrets manager |
| Uploaded files | logos/product images; stored paths in the DB | `UPLOAD_DIR` volume |
| Audit trail | non-repudiation and incident forensics | `audit_logs` |

## 2. Trust boundaries

```text
[ Browser ] --untrusted network--> [ Reverse proxy / TLS ]
                                        |
                                        v
                                  [ FastAPI API ]  <-- trusts: proxy headers, CORS allow-list
                                        |
                        +---------------+---------------+
                        v                               v
                 [ PostgreSQL ]                   [ Upload volume ]
                        |
                        v
                 [ GHCR / CI ]  <-- trusts: GitHub Actions, repository secrets
```

Each boundary carries an assumption worth testing:

1. **Browser -> API.** All input is untrusted: Pydantic validates shape, the
   tenancy filter decides visibility, `decode_token` decides identity. The API
   holds no session state.
2. **API -> database.** The API is the only writer. Tenancy is a **query-layer**
   control — a query that forgets `business_id` would leak.
3. **API -> filesystem.** `UPLOAD_DIR` is written by the API and is *not* served
   by the application (no static mount), so a stored file is not directly
   reachable over HTTP.
4. **CI -> registry.** Only a `v*` tag triggers publishing, and only after the
   lint/test/build jobs pass.

## 3. Threats and mitigations

| # | Threat | Category | Mitigation | Status |
|---|--------|----------|------------|--------|
| T1 | Read or modify another tenant's data | Information disclosure / Tampering | every query filtered by `ctx.business_id`; cross-tenant ids return `404`; `tests/test_employees_rbac.py` asserts isolation | mitigated |
| T2 | Forged or replayed token | Spoofing | HS256 signature verified with a single algorithm + `type` claim enforced (`decode_token`); access token lifetime 15 min | mitigated |
| T3 | Password brute force / credential stuffing | Spoofing | bcrypt hashing, uniform `401 Invalid credentials` (no enumeration on login), strong-`SECRET_KEY` check at startup | partly mitigated (rate limiting not wired — G1) |
| T4 | Stolen refresh token reused indefinitely | Spoofing | 7-day expiry; short access-token life limits the window | accepted (no server-side revocation — G2) |
| T5 | Privilege escalation between roles | Elevation of privilege | role read from `user_business` per request; writes gated inline (`Owner`/`Manager`, checkout also `Cashier`) | mitigated |
| T6 | Injection through search/filters/inputs | Tampering | SQLAlchemy ORM with bound parameters, Pydantic validation, no string-built SQL | mitigated |
| T7 | XSS reaching stored tokens | Information disclosure | React escaping, `lib/sanitize.ts`, CSP without `script-src 'unsafe-inline'` | partly mitigated (token in `localStorage` — G3) |
| T8 | CSRF against a cookie-bearing browser | Tampering | `SameSite=Strict` cookies + same-origin CORS allow-list | partly mitigated (middleware not registered — G4) |
| T9 | Malicious file upload (type/size) | Tampering | owner-only endpoint, random filename, stored outside the web root and not served | **open (G5)** |
| T10 | Committed credentials leaking via git | Information disclosure | `.gitignore` + `backend/scripts/scan_secrets.py` in CI and in the suite | mitigated |
| T11 | Vulnerable dependency shipped | Tampering | `pip-audit` + `npm audit --audit-level=high` on every PR; two accepted findings documented in `SECURITY.md` | partly mitigated (G6) |
| T12 | Malicious or drifted release artefact | Tampering | tag-only release gated on all jobs; image built from the committed lockfile; deploying is manual | mitigated |
| T13 | Denial of service via expensive endpoints | Denial of service | per-path request timeouts (`core/timeouts.py`) -> `504`; reports/AI are the slowest and bounded | partly mitigated (no in-app rate limit — G1) |
| T14 | Reconnaissance via verbose errors / probes | Information disclosure | uniform error envelope (no stack traces to clients), `/docs` and `/redoc` disabled in production | partly mitigated (G7) |
| T15 | AI prompt injection changing numbers | Tampering | the LLM only rewrites prose; figures come from deterministic SQL aggregates ([ADR 0003](../architecture/decisions/0003-offline-first-ai.md)) | mitigated |
| T16 | Insider/guest misuse at a shared POS till | Repudiation | every mutation writes `audit_logs` with user + tenant; cashier role is limited to search/checkout | mitigated |

## 4. Known gaps (verified against the code)

Each gap is a deliberate-now / fix-later decision, not an unknown:

| ID | Gap | Where | Recommended fix |
|----|-----|-------|-----------------|
| G1 | `setup_rate_limiting()` is never called, so `RATE_LIMIT_*` values are declared but unenforced | `app/core/rate_limit.py`, `app/main.py` | call `setup_rate_limiting(app)` (and set `REDIS_URL` for multiple replicas) or enforce limits at the proxy |
| G2 | Refresh tokens are stateless: issued in pairs, never revoked or reuse-detected; logout is client-side | `app/api/v1/auth.py`, `SECURITY.md` §Refresh Token Behavior | add a server-side token store with rotation + reuse detection |
| G3 | Access/refresh tokens live in `localStorage`, readable by any XSS | `frontend/lib/session.ts` | move to an httpOnly cookie flow (needs the CSRF work in G4) |
| G4 | `CSRFMiddleware` is implemented but not registered, so no mutating request is CSRF-checked | `app/core/csrf.py`, `app/main.py` | register the middleware and send `X-CSRF-Token` from `lib/api` — `SECURITY.md` §CSRF documents the intended design |
| G5 | Logo upload accepts any content type/size and derives the extension from the client filename | `app/api/v1/businesses.py` | allow-list extensions + magic-byte sniff, cap size, re-encode images |
| G6 | Two dependency findings accepted with mitigations (PyJWT alg-confusion, `google-generativeai` deprecation) | `SECURITY.md` §Known Audit Findings | schedule the `google-genai` migration and the PyJWT/`cryptography` bump |
| G7 | `/health/detailed` is unauthenticated | `app/api/v1/health.py` | gate it by network policy or authentication outside trusted networks |
| G8 | `POST /auth/forgot-password` returns `dev_token` when the account exists | `app/api/v1/auth.py` | remove the field (or gate it on `ENVIRONMENT == "development"`) before public exposure |

G1, G4 and G8 are the ones most likely to surprise a reader, because
`docs/` behaviour is described as active elsewhere: rate limits in
[`../api/authentication.md`](../api/authentication.md) §6, CSRF in
`SECURITY.md`, and the reset flow in §3 there. The code above is the current
truth.

## 5. Accepted risks

- **Money as float** and **tenancy as an application control** — see
  [`../database/schema.md`](../database/schema.md) §5.
- **Stateless auth** — operational simplicity over sophisticated revocation at
  this stage; exposure is bounded by token lifetimes and `SECRET_KEY` rotation.
- **CSP `style-src 'unsafe-inline'`** — required by the Tailwind/Next.js
  rendering model; documented in `SECURITY.md` §Content Security Policy Tradeoff.

## 6. Review cadence

Re-read this document when any of these change: a new endpoint or role, an auth
or crypto change, a new external dependency or SaaS integration, the deployment
topology, or a security fix. Record resulting decisions as an ADR in
[`../architecture/decisions/`](../architecture/decisions/) and update the status
column above — the gaps list should shrink, not grow silently.