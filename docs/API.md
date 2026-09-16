# StockPilot API Documentation

## Overview

StockPilot is a multi-tenant Inventory & POS SaaS platform. This document provides
complete API reference for integration and development.

- **Base URL**: `https://your-domain.com/api/v1`
- **Protocol**: HTTPS only
- **Format**: JSON
- **Version**: v1

---

## Authentication

All endpoints (except auth) require a Bearer token:

```
Authorization: Bearer <access_token>
X-Business-Id: <business_id>
```

### Token Refresh
Access tokens expire in **15 minutes**. Use the refresh token to get a new pair:

```
POST /api/v1/auth/refresh
{"refresh_token": "<your_refresh_token>"}
```

Response includes a new `access_token` and `refresh_token`.

---

## Rate Limits

| Endpoint Type | Limit |
|---------------|-------|
| Default | 100/minute |
| Auth (login/register) | 5/minute |
| AI endpoints | 10/minute |
| Reports | 20/minute |

---

## Error Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": 422,
    "message": "Request validation failed",
    "details": { "fields": [...] }
  }
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 504 | Request Timeout |

---

## Versioning

The API uses URL-based versioning: `/api/v1/`. Deprecated versions will be
supported for 6 months with warnings in response headers.

---

## Endpoints (mounted under `/api/v1`)

Contract test `backend/tests/test_api_contract.py` fails on rename/drop.
Probes: `GET /health`, `GET /health/live`, `GET /health/ready` (DB probe,
`503` when down), `GET /health/detailed`, `GET /` (metadata).

### Auth & tenancy
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`,
`POST /auth/logout`, `GET /auth/me`, `POST /auth/forgot-password`,
`POST /auth/reset-password`, `GET /businesses/me`, `POST /businesses`,
`PATCH /businesses/me`, `POST /businesses/me/logo`, `GET /employees`,
`POST /employees`, `PATCH /employees/{id}/role`,
`POST /employees/{id}/activate`, `POST /employees/{id}/deactivate`,
`POST /employees/{id}/reset-password`, `DELETE /employees/{id}`.

### Catalogue & parties
`GET|POST /categories`, `PATCH /categories/{id}`,
`POST /categories/{id}/deactivate`, `DELETE /categories/{id}`,
`GET|POST /products`, `GET|PATCH /products/{id}`,
`POST /products/{id}/deactivate`, `POST /products/{id}/activate`,
`POST /products/{id}/image`, `GET|POST /suppliers`,
`PATCH /suppliers/{id}`, `POST /suppliers/{id}/deactivate`,
`GET /suppliers/{id}/purchases`, `GET|POST /customers`,
`PATCH /customers/{id}`, `GET /customers/{id}/sales`.

### Inventory & trading
`GET /inventory/overview`, `GET /inventory/low-stock`,
`GET /inventory/out-of-stock`, `GET /inventory/transactions`,
`POST /inventory/adjust`, `POST /inventory/adjust-price`,
`GET /inventory/price-adjustments`, `GET|POST /purchases`,
`GET /purchases/{id}`, `POST /purchases/{id}/pay`,
`POST /purchases/{id}/cancel`, `GET /pos/search`, `GET /sales`,
`POST /sales/checkout`, `GET /sales/{id}`, `POST /sales/{id}/cancel`,
`GET /invoices/{id}`, `GET /invoices/{id}/pdf`, `GET|POST /returns`.

### Finance, reporting & platform
`GET|POST /expenses`, `PATCH|DELETE /expenses/{id}`,
`GET /finance/revenue`, `GET /finance/cogs`, `GET /finance/profit`,
`GET /dashboard`, `GET /analytics/products`, `GET /analytics/customers`,
`GET /analytics/suppliers`, `GET /reports/sales|inventory|purchases|expenses|profit`
(`format=json/csv/xlsx/pdf`), `GET /reports/profit/pdf`, `GET|PATCH /settings`,
`GET|PATCH /subscription`, `POST /ai/chat`, `GET /ai/insights`,
`GET /ai/forecast`, `GET /ai/reorder-recommendations`, `GET /ai/anomalies`,
`POST /ai/summarize`, `GET /ai/recommendations`,
`PATCH /ai/recommendations/{id}`, `GET /audit-logs`.

---

## Postman Collection

Import `stockpilot-api.postman_collection.json` from this directory into Postman
to get started quickly.

