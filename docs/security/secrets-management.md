# Secrets Management

Where every secret comes from, how it is kept out of git, how it is rotated, and
what to do when one leaks. Reporting a vulnerability is covered in
[`../../SECURITY.md`](../../SECURITY.md); the requirements context is in
[`threat-model.md`](threat-model.md).

---

## 1. Secret inventory

| Name | Used by | Required | If leaked |
|------|---------|----------|-----------|
| `SECRET_KEY` | JWT signing (`core/security.py`) | yes | attacker can forge a token for **any** user and tenant; rotating it signs every user out |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | API, compose, backup scripts | yes | full read/write access to every tenant's data |
| `GEMINI_API_KEY` | optional AI polishing | no | billed third-party usage; no tenant data access |
| `SENTRY_DSN` | optional error sink | no | ability to inject noise into the error stream |
| `REDIS_URL` | optional rate-limit storage | no | access to the counter store only |
| `MYSQL_*` (root, user, password) | legacy `docker-compose.yml` only | no | throw-away local instance; keep it that way |
| `GITHUB_TOKEN` | CI release job | CI-provided | publish packages/writes while the job runs; the token is short-lived and never echoed |

Non-secrets that look like secrets: `NEXT_PUBLIC_API_URL` (inlined into the
browser bundle — never put anything sensitive behind a `NEXT_PUBLIC_` name) and
the CI-only `SECRET_KEY` in `.github/workflows/ci.yml`.

## 2. Rules

1. **Never commit a real secret.** `.env`, `*.db`, `uploads/*` are in
   `.gitignore`; only `.env.example` templates with placeholders are tracked.
2. **Templates list every key** so an operator can see the full surface:
   [`.env.example`](../../.env.example) (root, compose),
   [`backend/.env.example`](../../backend/.env.example),
   [`frontend/.env.example`](../../frontend/.env.example).
3. **No defaults in production.** `docker-compose.prod.yml` declares
   `POSTGRES_PASSWORD` and `SECRET_KEY` with no fallback value and aborts when
   they are missing; `scripts/*.sh` fail fast on an unset `DB_PASSWORD`.
4. **Enforce strength at startup.** `core/config.py` rejects a `SECRET_KEY`
   shorter than 32 characters or containing `test-secret-key`, `dev-secret-key`,
   `changeme`, `replace-with-`, `secret` or `password` when
   `ENVIRONMENT` is `staging` or `production`.
5. **Secrets stay out of logs and reports.** Settings are read through
   pydantic-settings, never `os.environ` spread into log lines; error reports
   carry route/request id/tenant, not payloads.
6. **Rotate on suspicion, not on certainty.** A rotated key costs a re-login; an
   unrotated leaked key costs the business.

## 3. Local development

```bash
cp .env.example .env                     # compose only
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# generate real values locally (never reuse them anywhere real)
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
openssl rand -base64 32                                       # POSTGRES_PASSWORD
```

Committed dev conveniences (`dev-secret-key-not-for-production`,
`devpassword`) exist only so `docker compose -f docker-compose.dev.yml` works
out of the box; they are listed as placeholders by the scanner and must never
reach staging or production.

## 4. Production provisioning

Preferred order of preference:

1. A secrets manager injected into the process environment at start-up (cloud
   secret manager, Vault, Kubernetes `Secret`, Docker `--env-file` from a
   protected path, or `_FILE`-style injection).
2. Compose with a `.env` file that lives outside the repository and is
   `chmod 600`, owned by the deploy user.
3. **Never** a `.env` baked into the image or committed to git — the image is
   published to GHCR and readable by anyone who can pull it.

```bash
# compose reads the root .env; nothing sensitive is baked into the image
docker compose -f docker-compose.prod.yml up -d
```

`docker-compose.prod.yml` fixes the safe defaults for the *non-secret* security
settings: `ENVIRONMENT=production`, `JSON_LOGS=true`, `ALGORITHM=HS256`,
`ACCESS_TOKEN_EXPIRE_MINUTES=15`, `REFRESH_TOKEN_EXPIRE_DAYS=7`.

## 5. Keeping secrets out of git

`backend/scripts/scan_secrets.py` fails the build when a credential-looking
literal is committed. It scans only files tracked by `git ls-files` and reports:

| Rule | Catches |
|------|---------|
| private-key block | `-----BEGIN … PRIVATE KEY-----` |
| provider token | AWS, Google, GitHub, Slack, Stripe token formats |
| JSON Web Token | a literal `eyJ…` token |
| quoted credential literal | `"password": "Hunt3r2"`-style values |
| credential in env assignment | `API_KEY=Ab3…` in dotenv/compose/YAML lines |

Placeholders are ignored: `changeme`, `replace-with-...`, `ci-only-...`,
`test-...`, `${DB_PASSWORD}` expansions, `<...>`, `dummy`, `example`,
`local-only`, and empty values. A matched value must also look like a secret (a
digit, or mixed case, and no whitespace), which keeps identifiers such as
`stockpilot_token` out of the report — the deliberate cost is that an
all-lowercase, digit-free credential is not detected. A line can opt out with
`pragma: allowlist secret` when it is a genuine non-secret.

```bash
python backend/scripts/scan_secrets.py            # the tracked tree
python backend/scripts/scan_secrets.py --quiet    # summary only
```

It runs in CI (`backend / secret scan`) and inside the backend suite
(`backend/tests/test_secret_scan.py`), so both a pull request and a stray commit
are covered. `pre-commit` runs the lint/format/type hooks; the secret scan is a
CI and suite gate.

## 6. Rotation

Rotate on a schedule you can defend (for example annually for `SECRET_KEY`,
quarterly for `POSTGRES_PASSWORD`) and immediately on any suspicion.

| Secret | Procedure | User-visible impact |
|--------|-----------|---------------------|
| `SECRET_KEY` | generate a new value -> update the secret store -> restart every API process | **all sessions invalidated** (no `kid`/key-ring support, so there is no overlap window — see `SECURITY.md` §Key Rotation); every user logs in again |
| `POSTGRES_PASSWORD` | `ALTER ROLE … WITH PASSWORD` -> update the secret store and the connection string -> restart the API -> re-run `scripts/backup-db.sh` to prove the new credential | a restart of the API; in-flight requests fail |
| `GEMINI_API_KEY` | revoke in the Google console -> issue a new key -> update the environment -> restart | none; AI prose falls back to the deterministic answer while unset |
| `SENTRY_DSN` | roll the project DSN in the Sentry UI -> update -> restart | none |
| `REDIS_URL` | rotate the Redis credential, or unset it to fall back to in-process storage (single instance only) | none today, because rate limiting is not wired in-app (see [`threat-model.md`](threat-model.md) G1) |

Verification after any rotation:

```bash
curl -fsS http://localhost:8000/health/ready        # 200
curl -fsS http://localhost:8000/health/detailed     # no config errors
# log in through the UI (SECRET_KEY rotations force this by design)
```

## 7. If a secret leaks

1. **Contain** — rotate the affected secret first (§6). Do not wait for a
   post-mortem; a leaked `SECRET_KEY` is a standing forgery capability.
2. **Scope** — find when the literal entered git
   (`git log -S '<value>' --all`, `git log --patch -- <path>`) and whether the
   repository was ever public.
3. **Assess** — for `DATABASE_URL`/`POSTGRES_PASSWORD`, review
   `audit_logs` and database logs for access you cannot attribute to a user;
   for `SECRET_KEY`, treat every token as suspect and force re-login.
4. **Clean up** — remove the literal from the working tree, add it to the
   scanner's history if useful, and (only if the repository was public and the
   secret was reachable) rewrite history with the team's agreement — rotation,
   not history rewriting, is what actually removes the exposure.
5. **Record** — add the fix as `fix(sec): ...` to `CHANGELOG.md` and follow the
   disclosure guidance in `SECURITY.md`.

## 8. CI/CD secrets

- The workflow default is `permissions: contents: read`; only the `release` job
  raises that to `contents: write` + `packages: write`, and it uses the
  repository-provided `GITHUB_TOKEN` — no long-lived registry password.
- Secrets are never printed: no `env:` dump step and no `echo` of a variable.
- Dependabot needs no secrets; it opens PRs that re-run the same gates.
- A fork pull request never receives repository secrets, and the release job is
  tag-only, so forked code can never publish an image.

## 9. Checklist

- [ ] Every key in the inventory has a documented source and owner
- [ ] `.env` files ignored; only `.env.example` templates are tracked
- [ ] Production secrets injected from a secrets manager, never baked into an image
- [ ] `scan_secrets.py` clean on the branch
- [ ] Rotation dates recorded; `SECRET_KEY` rotation rehearsed at least once
- [ ] Leak-response steps known by the on-call operator (rotate -> scope -> assess -> clean -> record)