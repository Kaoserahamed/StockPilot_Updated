# Day 2 Architecture: Service Boundaries, Database Schema, API Contracts

## Repository
`StockPilot_Updated` — Inventory & POS SaaS (FastAPI + PostgreSQL + Next.js)

## Proposed Concept
Comprehensive POS and inventory platform with multi-location inventory, barcode scanning, supplier purchase orders, customer loyalty, sales forecasting, and e-commerce integration.

## Service Boundaries
| Service | Responsibility | Technology |
|---------|---------------|------------|
| POS Service | Checkout, cart, payment processing, receipt printing | FastAPI, PostgreSQL |
| Inventory Service | Stock levels, reservations, adjustments, transfers | FastAPI, PostgreSQL |
| Sales Service | Transactions, reporting, forecasting | FastAPI, PostgreSQL |
| Supplier Service | Purchase orders, supplier management, invoice matching | FastAPI, PostgreSQL |
| Customer Loyalty Service | Points, tiers, rewards, redemption | FastAPI, PostgreSQL |
| Reporting Service | Sales reports, dashboards, analytics | FastAPI, PostgreSQL |
| Frontend | Next.js POS interface, manager dashboard | Next.js, TypeScript, Tailwind |

## Database Schema (PostgreSQL)
- `stores` — id, name, location, hours, tax_settings, currency, payment_methods, created_at
- `users` — id, email, password_hash, role (cashier/manager/admin), store_id, created_at
- `products` — id, sku, barcode, name, description, price, cost, category_id, supplier_id, created_at
- `categories` — id, name, parent_id, created_at
- `suppliers` — id, name, contact_info, performance_rating, lead_time, created_at
- `inventory` — id, product_id, store_id, quantity, reserved, reorder_point, location, created_at
- `stock_movements` — id, inventory_item_id, type (receipt/sale/adjustment/transfer/waste), quantity, reference_id, created_at
- `stock_transfers` — id, from_store, to_store, status, items, created_at, completed_at
- `purchase_orders` — id, supplier_id, status, items, total, created_at, received_at
- `supplier_invoices` — id, po_id, invoice_number, amount, status, matched, created_at
- `sales` — id, store_id, cashier_id, transaction_id, line_items, payment_method, tender, change, total, created_at
- `sale_line_items` — id, sale_id, product_id, quantity, price, discount
- `payments` — id, sale_id, type (cash/card/mobile), amount, transaction_id, created_at
- `refunds` — id, sale_id, amount, reason, method, created_at
- `customers` — id, name, contact_info, loyalty_status, points, purchase_history, created_at
- `loyalty_transactions` — id, customer_id, points_earned, points_redeemed, reason, created_at
- `loyalty_tiers` — id, name, min_points, benefits, created_at
- `shifts` — id, cashier_id, store_id, opened_at, closed_at, cash_start, cash_end, discrepancies
- `cash_drawers` — id, shift_id, opening_balance, deposits, expected, actual, variance
- `gift_cards` — id, code, balance, issued_at, redeemed_at, created_at
- `promotions` — id, type (bogo/bundle/time-limited), rules, start_date, end_date, created_at
- `sales_forecasts` — id, product_id, store_id, period, predicted_demand, confidence, created_at

## API Contracts
### POS
- `POST /api/v1/pos/cart` — {items} → {cart}
- `POST /api/v1/pos/checkout` — {cart, paymentMethod, tender} → {receipt}
- `POST /api/v1/pos/barcode/scan` — {barcode} → {product}
- `POST /api/v1/pos/receipts/{id}/print` → 204
- `POST /api/v1/pos/shifts/open` — {cashierId, openingBalance} → {shift}
- `POST /api/v1/pos/shifts/{id}/close` — {cashEnd} → {shift, reconciliation}

### Inventory
- `GET /api/v1/inventory` → list (filters: store, low stock)
- `POST /api/v1/inventory/adjustments` — {itemId, quantity, type, reason} → {movement}
- `POST /api/v1/inventory/transfers` — {fromStore, toStore, items} → {transfer}
- `GET /api/v1/inventory/reorder-suggestions` → list

### Sales
- `GET /api/v1/sales` → list (filters: date, store, cashier)
- `GET /api/v1/sales/{id}` → {sale, lineItems, payments}
- `GET /api/v1/sales/reports` — {period, store} → {report}
- `GET /api/v1/sales/forecast` — {productId, storeId} → {prediction}

### Suppliers
- `POST /api/v1/purchase-orders` — {supplierId, items} → {po}
- `GET /api/v1/purchase-orders` → list
- `PUT /api/v1/purchase-orders/{id}/receive` — {items} → 204
- `POST /api/v1/suppliers` → {supplier}

### Customers & Loyalty
- `POST /api/v1/customers` → {customer}
- `GET /api/v1/customers/{id}` → {profile, points, history}
- `POST /api/v1/loyalty/earn` — {customerId, points, reason} → {balance}
- `POST /api/v1/loyalty/redeem` — {customerId, points, reward} → {balance}

### Gift Cards
- `POST /api/v1/gift-cards/issue` — {amount} → {code, balance}
- `POST /api/v1/gift-cards/redeem` — {code, amount} → {balance}

## Technical Notes
- Currently FastAPI + PostgreSQL backend, Next.js frontend
- In-memory SQLite for tests (no external DB needed)
- Alembic migrations
- No multi-location inventory, supplier POs, loyalty, forecasting, or e-commerce integration yet
- No barcode scale integration, serial/batch tracking, KDS, gift cards, or accounting integration yet
- Makefile and docker-compose exist but no CI/CD pipelines visible

## Day 2 Outcome
Architecture design documented. No code changes. 0 PRs. Ready for Day 3 (CI/CD pipeline).