# Data Flow

How a request travels through StockPilot, which process owns each write, and
where the read paths get their numbers. Layer responsibilities live in
[`system-architecture.md`](system-architecture.md); the tables themselves in
[`../database/schema.md`](../database/schema.md).

---

## 1. Request lifecycle

```text
Browser (Next.js App Router)
  |  axios instance in frontend/lib/api.ts
  |  Authorization: Bearer <access>   X-Business-Id: <id>
  v
CORS -> SecurityHeaders -> Timeout -> CacheHeaders -> RequestContext
  v
FastAPI route (app/api/v1/*.py)
  -> Pydantic validation (app/schemas/schemas.py)
  -> get_current_context  (JWT -> User -> UserBusiness -> Context)
  -> one service call or one query block
  -> db.commit()
  v
{ payload }   or   { "error": { "code": ..., "message": ... } }
```

| Step | Owner | Notes |
|------|-------|-------|
| Transport | `frontend/lib/api.ts` | Adds the bearer token + `X-Business-Id`, redirects to `/login` on `401` |
| CORS | `main.py` | Registered last, so it is outermost and wraps timeout `504`s too |
| Security headers | `core/middleware.SecurityHeadersMiddleware` | HSTS, CSP, `X-Frame-Options`, `Permissions-Policy` |
| Timeout | `core/timeouts.TimeoutMiddleware` | Per-path: search 10s, checkout 15s, default 30s, reports/analytics 45s, AI 60s -> `504` |
| Cache | `core/middleware.CacheHeadersMiddleware` | Mutations `no-store`; catalogue reads `private, max-age=30`; other reads `max-age=60` |
| Correlation | `core/middleware.RequestContextMiddleware` | `X-Request-Id` (caller-supplied or generated) + `X-Response-Time-Ms` |
| Auth | `core/security.decode_token` | Verifies signature, expiry and the `type` claim |
| Tenancy | `core/deps.get_current_context` | Resolves `Context(user, business_id, role)`, else `401`/`403` |
| Validation | `app/schemas/schemas.py` | Failures surface as `422` |
| Errors | `core/exceptions` | Every failure is the uniform `{error: {code, message}}` envelope |
| Audit | `services/audit.write_audit` | One row per significant mutation |

Tenancy is enforced at the **query** level: every row read or written is
filtered by `ctx.business_id`, so another tenant's id returns `404` rather than
`403` — there is no id oracle. Roles are checked per route with
`ctx.role not in (...)` or `core.deps.require_roles`.

---

## 2. Stock write path (the most important invariant)

`quantity_on_hand` and its ledger row in `inventory_transactions` are written
**together, in one transaction**, by the feature that caused the movement:

| Trigger | Endpoint | Allowed roles | Ledger `tx_type` | Effect on `quantity_on_hand` |
|---------|----------|---------------|------------------|------------------------------|
| Purchase created / received | `POST /purchases` | Owner, Manager | `purchase` | `+ quantity` |
| Purchase cancelled | `POST /purchases/{id}/cancel` | Owner, Manager | `purchase` | `- quantity` |
| POS checkout | `POST /sales/checkout` | Owner, Manager, Cashier | `sale` | `- quantity` |
| Sale cancelled | `POST /sales/{id}/cancel` | Owner, Manager | `sale` | `+` non-returned quantity |
| Return recorded | `POST /returns` | Owner, Manager | `return` | `+` returned quantity |
| Manual adjustment | `POST /inventory/adjust` | Owner, Manager | `adjustment` | `± delta` |

`services/inventory_service.apply_stock_change` is the **guarded** writer: it
requires a reason, rejects a zero delta, loads the product tenant-filtered and
refuses to go negative (`400 Insufficient stock`) unless the caller is an
adjustment. The trading paths apply the delta inline and insert the same ledger
row in the same commit; the ledger therefore always reconciles as
`sum(quantity_change) == on_hand - opening`.

> **Known gap (verified against the code).** ADR 0005 states that
> `apply_stock_change` is the single writer for `quantity_on_hand`; today only
> `/inventory/adjust` calls it (`grep apply_stock_change backend/app`). Sales,
> purchases and returns assign `quantity_on_hand` directly next to their ledger
> insert, so the negative-stock guard is duplicated at those call sites. The
> data stays consistent — the invariant that matters — but the "one writer"
> claim is aspirational. Do not rewrite the ADR
> ([`decisions/0005-single-stock-writer.md`](decisions/0005-single-stock-writer.md));
> record a superseding ADR when the call sites are consolidated.

### POS checkout, step by step

`POST /api/v1/sales/checkout` (`app/api/v1/sales.py`) is the reference write
path — every other mutation follows the same shape:

1. Role gate (`Owner`/`Manager`/`Cashier`) and `payment_method` allow-list.
2. Load the customer and all cart products in one tenant-filtered query; any
   id from another business fails with `400 Invalid product in cart`.
3. Per line: product active, `quantity_on_hand >= quantity`, non-negative
   price/discount, `line_total >= 0`.
4. Totals: `subtotal -> discount -> taxable -> tax_percent -> total`;
   `paid_amount` must be within `0..total`; `credit` requires a customer.
5. `services/invoice_service.next_invoice_no` allocates the next sequence from
   `invoice_counters` using `Business.invoice_format`
   (placeholders `{yyyy}`, `{yy}`, `{mm}`, `{seq:04d}`).
6. Insert `Sale` + `SaleItem`s, decrement stock and append one
   `InventoryTransaction` per line.
7. Credit / partial payment increases `customers.outstanding_balance`.
8. `services/audit.write_audit(action="sale.checkout")`, then **one**
   `db.commit()`; the sale is re-read so the client sees committed state.

Cancellation is the inverse: it restocks the un-returned quantity, reverses the
customer balance and flips `sales.status` to `cancelled`.

---

## 3. Other write paths

| Domain | Endpoint | Writes |
|--------|----------|--------|
| Catalogue | `POST/PATCH /products`, `/categories` | Row + `audit_logs`; SKU/barcode uniqueness per business; soft delete via `is_active` |
| Price change | `POST /inventory/adjust-price` | `price_adjustments` row + audit; never mutates history |
| Parties | `POST/PATCH /suppliers`, `/customers` | Row + audit; balances are derived from purchases/sales |
| Purchases | `POST /purchases/{id}/pay` | `purchases.paid_amount`/`payment_status`, `suppliers.outstanding_balance` |
| Returns | `POST /returns` | `sale_returns` + `sale_return_items`, `sale_items.returned_qty`, `sales.refunded_amount`, restock |
| Expenses | `POST/PATCH/DELETE /expenses` | Row + audit; category checked against an allow-list |
| Identity | `POST /employees/*`, `PATCH /businesses/me` | `user_business` role/lifecycle, business profile, logo file in `UPLOAD_DIR` |
| Platform | `PATCH /subscription`, `GET/PATCH /settings` | `subscriptions` plan/limits, business settings |

---

## 4. Read paths

- **Dashboard / analytics / reports** are computed in `services/finance/*` from
  the same tables the write paths maintain: revenue from `sales`, COGS from
  `purchase_items` / `sale_items`, expenses from `expenses`. Reports stream
  JSON, CSV, XLSX (openpyxl) or PDF (reportlab).
- **Inventory overview / low-stock / out-of-stock** compare `quantity_on_hand`
  against `min_stock`; they never recompute stock from the ledger.
- **Cache behaviour** is per path prefix (see the middleware table above), so a
  POS re-read after checkout is never served stale.
- **List endpoints batch** their joins (`_sales_to_out`, `_many_to_out`) so a
  page of documents costs a fixed handful of queries instead of N+1.

## 5. AI data flow

1. `services/ai_service`, `ai2_service` and `ai3_service` compute a
   deterministic answer from live SQL aggregates (profit, best seller, reorder
   quantity, z-score anomalies).
2. `maybe_polish_with_gemini` optionally rewrites the **wording** when
   `settings.has_gemini_configured`; any failure returns the draft unchanged.
3. Answers a user keeps are stored in `ai_recommendations` with the
   `reviewed` / `acted_upon` workflow. No LLM output can change a figure — see
   [`decisions/0003-offline-first-ai.md`](decisions/0003-offline-first-ai.md).

## 6. Frontend data flow

```text
app/ (route page)
  -> hooks/  (useFormValidation, useKeyboardShortcuts, useOptimisticUpdate)
  -> services/  (one typed module per domain - the only fetch layer)
  -> lib/api  (axios, bearer token, 401 refresh, error envelope -> errMsg)
  -> backend
  <- TanStack Query cache (reads) / optimistic update (writes)
```

`lib/session.ts` owns token + business storage; `lib/auth.tsx` and
`lib/store.tsx` expose session and cart state. `services/` is the single place a
backend contract change has to be mirrored, which is why
`frontend/tests/services.test.ts` asserts the documented routes.
