# Testing

How to run the suites, what they cover, and how to read the output. All
suites are hermetic: **no external database, network, or API key required.**

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

Coverage is enforced with `--cov=app --cov-report=term-missing`; the CI job
uploads `coverage.xml` as an artifact. The target is ≥ 80% statements on
`app/` (routers + services).

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
| `tests/shortcuts.test.tsx` | `useKeyboardShortcuts` fires on keydown, respects `enabled=false` |
| `tests/pages.test.ts` | route components import (auth, POS, products, inventory) + report export paths |

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
