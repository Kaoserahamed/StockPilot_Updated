# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

Security fixes are released as patch versions on `main` and published
through GitHub Releases. Version tags also publish a signed container image
to GHCR (see `docs/deployment/ci-cd.md`). Technical detail behind this policy:
[`docs/security/threat-model.md`](docs/security/threat-model.md) and
[`docs/security/secrets-management.md`](docs/security/secrets-management.md).

## Reporting a Vulnerability

**Do not open a public issue for a suspected vulnerability.**

1. Email the maintainers privately, or use GitHub's
   *Security > Report a vulnerability* form on this repository.
2. Include: affected version/commit, exact reproduction steps or PoC,
   full error output, and your environment (OS / Python / Node).
3. Allow up to **48 hours** for an initial acknowledgement and up to
   **90 days** for coordinated disclosure before publishing details.

We ask reporters not to access other users' data, not to degrade service
availability, and not to exfiltrate data beyond a minimal proof of concept.

## What to Expect

- Acknowledgement within 2 business days.
- A private fix branch + regression test (backend `pytest` and/or frontend
  `vitest`) that fails without the fix.
- A `fix(sec): ...` release with a `CHANGELOG.md` entry crediting the
  reporter (unless anonymity is requested).
- Revocation guidance if secrets were exposed (rotate `SECRET_KEY`,
  `POSTGRES_PASSWORD`, `GEMINI_API_KEY`).

## Hardening Already in Place

- `backend/scripts/scan_secrets.py` + CI `backend-secret-scan` job fail the
  build on committed credential literals (see `CONTRIBUTING.md` §1.4).
- `pip-audit` (backend) and `npm audit --audit-level=high` (frontend) run on
  every PR via `.github/workflows/ci.yml`.
- Production compose (`docker-compose.prod.yml`) requires `SECRET_KEY` and
  `POSTGRES_PASSWORD` from the environment — no committed defaults.
- Auth uses short-lived JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES=15`), bcrypt
  password hashing, rate-limited login (`slowapi`), and security headers via
  `app/core/middleware.py`.
- Never commit `.env`, `*.db`, or `uploads/*` user content. Copy from
  `.env.example` instead.

## Known Audit Findings

Findings from `pip-audit` and manual review that are either mitigated at the
application layer or tracked for follow-up. Each entry notes the current
mitigation and the reason it is not yet closed by a version bump.

### PyJWT legacy alg confusion (PYSEC-2025-183 / 2026-*)

- **Package:** `PyJWT==2.10.1` (pinned in `backend/requirements.txt`)
- **Class:** JWT algorithm confusion — a naive consumer of `jwt.decode` could
  be tricked into accepting a token signed with an unexpected algorithm if the
  `algorithms` argument is omitted or too permissive.
- **Status:** mitigated at the application layer.
- **Mitigation:**
  - `backend/app/core/security.py:decode_token` calls
    `jwt.decode(token, key, algorithms=[settings.algorithm])` with a single
    algorithm derived from `settings.algorithm` (default `HS256`).
  - The same function verifies the `type` claim (`access` vs `refresh`), so a
    token issued for one purpose cannot be presented for the other.
  - `PyJWT` is the only JWT backend installed: `python-jose`,
    `ecdsa`, `rsa` and `pyasn1` are **not** in `requirements.txt`, so there is
    no fallback to a less-secure decoder.
- **Why not bump:** upgrading to a newer `PyJWT` wants `cryptography>=46` and
  the HS256-only allowlist the codebase already enforces. The upgrade is
  desirable but is a dependency-policy change, not a security hole today.
  Tracked as a routine dependency update, not a release-blocker.

### `google-generativeai` package deprecated by Google

- **Package:** `google-generativeai==0.8.6` (pinned in `backend/requirements.txt`)
- **Class:** maintenance / supply-chain — Google ended support for the
  `google.generativeai` package and directs new code to `google-genai`
  (`google.genai`). The deprecated package no longer receives updates or bug
  fixes.
- **Status:** accepted risk with a documented migration path.
- **Mitigation:**
  - AI is fully optional: `settings.ai_enabled` is `False` when
    `GEMINI_API_KEY` is empty, and every AI endpoint returns the deterministic
    analytics answer on any import or API error (`ai_service.py`). A broken or
    missing AI SDK therefore cannot take the API down.
  - The API key is read from pydantic-settings (`settings.gemini_api_key`),
    never from `os.environ` directly, and is never logged.
- **Migration:** replace `google-generativeai` with `google-genai` and update
  `backend/app/services/ai_service.py` to call the new SDK client. The rest of
  the application (the deterministic path, the finance service, the schemas)
  is untouched. This is a Phase-5 feature, not a core trading or finance flow,
  so the migration can be scheduled alongside routine dependency updates.

## Dependency Vulnerability Response

When `pip-audit` (backend) or `npm audit --audit-level=high` (frontend) flags
a new issue in CI:

1. Confirm whether the vulnerable code path is reachable from this application.
   Many CVEs apply to a feature the app does not use (e.g. a parsing mode,
   a protocol, a subclass).
2. If the path **is** reachable, either patch to a fixed version or, when a
   patch is not yet available, add an application-layer mitigation and open a
   tracking issue linked from the CI run.
3. If the path **is not** reachable, document the non-applicability in the
   CI audit log / the PR comment and close the finding. Do not silently ignore
   the advisory — record why it does not apply.
4. Computed-inconsequential findings (e.g. dev-only dependencies) are exempt
   from release-blocking but are still listed in the audit output for
   transparency.

## Key Rotation

The JWT signing key is `SECRET_KEY` from `app.core.config.Settings`. There is
currently **no key versioning** (`kid` claim) in issued tokens.

- Rolling `SECRET_KEY` immediately invalidates **every** access and refresh
  token in circulation. There is no graceful overlap window.
- If you need graceful rotation (e.g. rotate without forcing every user to
  log in again), add a key ring plus a `kid` claim to `create_access_token` /
  `create_refresh_token` and a matching lookup in `decode_token` before
  rotating. That work is not scheduled yet.

For the current release, the intended rotation procedure is:
1. Treat a suspected `SECRET_KEY` leak as an incident.
2. Generate a new key, set it in the environment, and restart every process.
3. Communicate that all users will be signed out; refresh tokens do not survive
   a key change.

## CSRF Token Cookie Design

The CSRF cookie (`csrf_token`) is set with `httponly=False` so that JavaScript
can read it. This is intentional for the double-submit cookie pattern used
here:

- The cookie value is also sent in the `X-CSRF-Token` header on every
  state-changing request.
- The backend compares cookie and header with `hmac.compare_digest`
  (constant-time) in `app/core/csrf.py`.
- A cross-origin attacker cannot read the cookie (SameSite=Strict + browser
  cookie policy), so they cannot forge the header. They also cannot write the
  header cross-origin (no CORS allow-listing of `X-CSRF-Token`).

The tradeoff — "the cookie is readable by the same origin's JS" — is safe
because the token is bound to the header, not to the cookie alone. If a future
change sets `httponly=True`, the double-submit flow breaks and every mutating
request returns `403`. Do not make that change without also switching to a
different CSRF mechanism.

When `ENVIRONMENT=production`, the cookie is set with `Secure` and
`SameSite=Strict`. The cookie name is not prefixed with `__Host-` today; that
prefix would additionally lock the cookie to path `/` and require `Secure`.
Adding `__Host-csrf_token` is a safe hardening improvement when the app is
always served from a single path at the root.

## Content Security Policy Tradeoff

`app/core/middleware.py` sets a strict CSP that allows inline styles
(`style-src 'self' 'unsafe-inline'`) because the frontend (Next.js + Tailwind)
emits inline style blocks as part of its normal rendering. Removing
`'unsafe-inline'` without a nonce or hash-based policy would break the UI.

This is a documented tradeoff:

- The policy still blocks inline `<script>` (no `'unsafe-inline'` for
  `script-src`), which is the more important boundary for XSS.
- If the frontend ever migrates away from Tailwind's inline-style model (or
  adopts a nonce-based CSP), the `'unsafe-inline'` on `style-src` should be
  removed and replaced with a hash or nonce.

## Health Endpoint Exposure

- `GET /health` and `GET /health/live` are liveness probes. They return
  service name, version and environment only. They are safe to expose without
  authentication in container/orchestrator setups.
- `GET /health/ready` returns database connectivity (`connected` / `disconnected`).
  It is a readiness probe and is also safe to expose without authentication.
- `GET /health/detailed` returns dependency status **plus** the error-tracking
  summary (`app/core/error_tracking.py`): counters, fingerprints, and the most
  recent reports. The reports intentionally exclude PII (no passwords, no full
  request bodies, no tokens) — only exception type, route, request id, and
  fingerprint are exposed.

**Policy:** `/health/detailed` is currently served without authentication.
That is acceptable for a small internal deployment behind a trusted network,
but it should be gated (authentication or network restriction) in any
environment where untrusted parties can reach the API.

## Password Policy

`app/core/sanitization.py:validate_password_strength` enforces:

- Minimum 8 characters, maximum 128 characters.
- At least one letter **and** at least one digit.

This is a length-first policy inspired by OWASP guidance, but it is **not** a
literal copy of any specific OWASP recommendation. In particular:

- OWASP's current guidance leans toward longer passphrases (12+ characters) and
  away from composition rules. This app's policy is lighter than that: it keeps
  a letter+digit rule and a lower minimum length so that short passphrases are
  not rejected.
- The `letter AND digit` rule is intentionally conservative for a small team /
  early-stage app. If the project moves to passphrase-first auth, update this
  function and the comment to match.

Do not cite this policy as "OWASP-compliant" without qualification. Call it
"length-first, inspired by OWASP guidance" instead.

## Refresh Token Behavior

The refresh endpoint (`POST /api/v1/auth/refresh`) exchanges a valid refresh
token for a **new access + new refresh token pair**. The old refresh token is
not recorded or invalidated server-side — the app uses stateless JWTs, so
"rotation" here means *issue a fresh pair*, not *maintain a used-token family
and reject replays*.

Consequences:

- If a refresh token is stolen and used by an attacker, the legitimate user's
  next refresh also succeeds (the token is not revoked on use). Both parties
  hold a valid refresh token until it expires (`REFRESH_TOKEN_EXPIRE_DAYS=7`).
- There is no refresh-token family tracking, no reuse detection, and no
  server-side token blacklist.
- Logout (`POST /api/v1/auth/logout`) is client-side only: the server returns
  `{"message": "Logged out"}` and trusts the client to discard the token.

This is a deliberate simplicity tradeoff for an early-stage app. If refresh
token theft becomes a concern (e.g. the app gains high-value accounts),
add a server-side token store with reuse detection before the next release.
