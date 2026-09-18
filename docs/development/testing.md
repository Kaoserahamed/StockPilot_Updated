# Testing

How to run the suites, what they cover, and how to read the output. All
suites are hermetic: **no external database, network, or API key required.**

Setup that gets a machine to this point is in [`setup.md`](setup.md); the CI
jobs that run these commands are in
[`../deployment/ci-cd.md`](../deployment/ci-cd.md).

## Backend (`backend/`, pytest)

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing   # canonical command (also in CI)
```

- **Isolation:** `tests/conftest.py` builds a fresh in-memory SQLite database
  per test (StaticPool, sessions rolled back), then overrides `get_db` and
  the settings object. Tests can run in any order and in parallel workers.
- **Helpers:** `tests/factories.py` creates owners, staff, catalogue, parties
  and trading documents through the real HTTP API — never by poking the ORM
  directly — so tests exercise the same paths clients use.

| File | Covers |
|------|--------|
| `test_health.py` | `/health`, `/ready`, security headers, request-id propagation |
| `test_auth.py` | register, login, refresh rotation guards, logout, forgot/reset flow |
| `test_categories.py` / `test_products.py` | catalogue CRUD, SKU/barcode uniqueness, search, soft delete, audit |
| `test_businesses.py` | business profile, logo upload, second-branch creation |
| `test_parties.py` | suppliers/customers, history endpoints, outstanding balances |
| `test_inventory.py` | overview/conditions, alerts, manual adjustments, price history |
| `test_purchases.py` | receiving, payment schedule, overpay guard, cancellation reversal |
| `test_sales_pos.py` | checkout, tax/discount maths, POS search, cancel, invoices + PDF |
| `test_returns.py` | partial/full refunds, restocking, over-return guard |
| `test_expenses.py` | category allow-list, filters, update/delete |
| `test_finance_reports.py` | revenue/COGS/profit agreement, dashboard, analytics, CSV/Excel/PDF exports |
| `test_employees_rbac.py` | employee lifecycle, role matrix, cross-tenant isolation |
| `test_settings_subscription.py` | settings round-trip, plan changes, usage counters |
| `test_ai.py` | chat/insights/forecast/reorder/anomalies offline, review workflow |
| `test_end_to_end.py` | register → … → AI summary in one trading shop |
| `test_logging_config.py` | JSON vs text log output, `app` correlation field, `JSON_LOGS` switch |
| `test_dependency_manifests.py` | manifests committed, exact pins, lockfile is UTF-8 text and covers every direct pin |
| `test_quality_gates.py` | coverage floors, CI jobs/commands, container + devcontainer artefacts, secret-scan wiring |
| `test_secret_scan.py` | provider-token and literal detection, placeholder precision, allowlist pragma, clean-tree scan |

From the repository root, `pip install -r requirements.txt -r requirements-dev.txt`
followed by `pytest` uses the root `pyproject.toml`
(`testpaths = ["backend/tests"]`, `pythonpath = ["backend"]`), so the same suite
runs with the same coverage floor without changing directory.

Coverage is **enforced**, not just reported:

- `backend/pyproject.toml` sets `[tool.coverage.report] fail_under = 80` and CI
  passes `--cov-fail-under=80`, so a drop below the floor fails the build.
- The repository-root `pyproject.toml` carries the same floor, so
  `pytest --cov` from the root is gated too.
- The frontend suite runs with `npm run test:coverage`; `frontend/vitest.config.ts`
  holds the thresholds (lines, functions, branches and statements must each stay
  at or above 70%).
- CI uploads `coverage.xml` as an artifact for every run.

Frontend coverage scope: `coverage.include` measures the unit-tested modules
(`lib/`, `hooks/`, `services/`, `components/`). The route pages under `app/` are
verified by `tests/pages.test.ts` (render smoke tests) and by the production
build, and are deliberately excluded from the percentage so it stays meaningful.

### Committed-secret scan

`backend/scripts/scan_secrets.py` fails the build on private-key blocks,
provider tokens (AWS, Google, GitHub, Slack, Stripe), JSON Web Tokens and
quoted literals assigned to password/secret/token names. Placeholders such as
`changeme`, `replace-with-...` or `${DB_PASSWORD}` are ignored, and a line can
opt out with `pragma: allowlist secret`. CI runs it on every push and
`backend/tests/test_secret_scan.py` scans the tracked tree as part of the suite.

## Frontend (`frontend/`, Vitest + jsdom)

```bash
cd frontend
npm ci
npm test -- --run        # single run (CI); `npm run test:watch` to iterate
```

| File | Covers |
|------|--------|
| `tests/sanitize.test.ts` | `escapeHtml`, `sanitizeInput`, email/phone validators |
| `tests/api.test.ts` | `errMsg` envelope parsing, 401 redirect interceptor |
| `tests/session.test.ts` | token + tenant storage round-trip, logout clearing |
| `tests/useFormValidation.test.ts` | required/length/pattern rules, per-field clearing |
| `tests/services.test.ts` | typed `services/` layer posts to the documented routes |
| `tests/components.test.tsx` | `Card`/`Stat`/`Badge`/`Empty`, `Skeleton*`, `ToastProvider`, `ErrorBoundary` fallback |
| `tests/store.test.tsx` | cart add/merge/remove/clear, `cartTotal` maths, toasts + auto-dismiss, preferences, provider guard |
| `tests/optimisticUpdate.test.tsx` | `useOptimisticUpdate` snapshot/cancel, rollback on failure, `onSuccess`, invalidation |
| `tests/shortcuts.test.tsx` | `useKeyboardShortcuts` fires on keydown, respects `enabled=false` |
| `tests/pages.test.ts` | route components import (auth, POS, products, inventory) + report export paths |

Coverage is enforced by `npm run test:coverage`
(`frontend/vitest.config.ts` → `coverage.thresholds`, `all: true`): the
percentage is computed over `components/`, `hooks/`, `lib/` and `services/`.
The route pages in `app/` are smoke-tested by `tests/pages.test.ts` and the
production build instead, so the number keeps measuring unit-testable logic.
A newly added module with no tests shows up at 0% and pulls the floor down.

Type and lint gates run alongside: `npm run lint`, `npm run typecheck`
(`tsc --noEmit`), `npm run format:check`, and the `npm run build` smoke
build — all in CI (`frontend-check` job).

## Interpreting failures

- `401` where `200` was expected → the test's login helper or
  `X-Business-Id` header is stale; check `factories.login`.
- `404` on a seeded row → tenancy filter: the fixture belongs to another
  business (intended — see the isolation tests).
- `422` → Pydantic rejected the payload; the response `detail` names the
  field (`pytest -vv` prints the body).
- Coverage drop on a new router → add the matching `test_*.py` before
  merging; `M1` forbids merging features without their tests.
