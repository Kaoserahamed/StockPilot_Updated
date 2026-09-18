# ADR 0005 — All stock mutations go through one writer

- **Date:** 2026-09-16
- **Status:** Accepted

## Context

Stock quantity is touched by purchases, sales, returns, cancellations, and
manual adjustments. Letting each router update `quantity_on_hand` inline
previously produced drift between the shelf count and the movement history.

## Decision

`services/inventory_service.apply_stock_change` is the **single writer** for
`Product.quantity_on_hand`. It validates (reason required, non-zero delta,
never negative), applies the delta, and inserts the `InventoryTransaction`
row in the same flush. All routers — including cancellation and return
reversals — call it; nothing else assigns `quantity_on_hand`.

## Consequences

- The ledger always reconciles: `sum(transactions) == on_hand - opening`.
- The negative-stock guard lives in one place with one error message that
  checkout surfaces as `400 Insufficient stock`.
- Future concurrency control (row-level locking / serializable retries) has a
  single function to harden.
