# ADRs — Architecture Decision Records

Short, dated notes explaining *why* the system looks the way it does. New
decisions get a new file; old ones are never rewritten.

Context for these decisions lives in
[`../system-architecture.md`](../system-architecture.md) and the flow-level
detail in [`../data-flow.md`](../data-flow.md).

## Index

| ADR | Date | Decision |
|-----|------|----------|
| [0001](0001-monorepo-layout.md) | 2026-09-16 | Backend + frontend in one monorepo |
| [0002](0002-postgres-primary-sqlite-for-tests.md) | 2026-09-16 | PostgreSQL in production, in-memory SQLite for tests |
| [0003](0003-offline-first-ai.md) | 2026-09-16 | Deterministic analytics first, Gemini only as a polisher |
| [0004](0004-jwt-access-refresh.md) | 2026-09-16 | Short-lived access tokens + long-lived refresh tokens |
| [0005](0005-single-stock-writer.md) | 2026-09-16 | All stock mutations go through `apply_stock_change` |
