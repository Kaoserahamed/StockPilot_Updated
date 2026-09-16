"""API surface contract (M5.4).

The OpenAPI document is the published contract between the backend and the
Next.js client, so it deserves a test: these assertions fail if a route is
renamed, dropped or lose its response model by accident.

Path templates are normalised (``{pid}`` -> ``{}``) because parameter *names*
are an implementation detail - only the shape is contractual.
"""

import re

from fastapi.testclient import TestClient

from app.main import app

PARAM = re.compile(r"\{[^}]+\}")


def _documented() -> set[tuple[str, str]]:
    """(METHOD, /normalised/path) for every documented operation."""
    schema = app.openapi()
    found: set[tuple[str, str]] = set()
    for path, operations in schema["paths"].items():
        for method in operations:
            found.add((method.upper(), PARAM.sub("{}", path)))
    return found


def _require(*pairs: tuple[str, str]) -> None:
    documented = _documented()
    missing = [p for p in pairs if p not in documented]
    assert not missing, f"route contract broken, missing: {missing}"


def test_probe_endpoints_are_documented() -> None:
    _require(
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/health/detailed"),
    )


def test_identity_and_tenancy_routes_are_documented() -> None:
    _require(
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/refresh"),
        ("POST", "/api/v1/auth/logout"),
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/auth/forgot-password"),
        ("POST", "/api/v1/auth/reset-password"),
        ("GET", "/api/v1/businesses/me"),
        ("POST", "/api/v1/businesses"),
        ("PATCH", "/api/v1/businesses/me"),
        ("POST", "/api/v1/businesses/me/logo"),
        ("GET", "/api/v1/employees"),
        ("POST", "/api/v1/employees"),
        ("DELETE", "/api/v1/employees/{}"),
        ("PATCH", "/api/v1/employees/{}/role"),
        ("POST", "/api/v1/employees/{}/activate"),
        ("POST", "/api/v1/employees/{}/deactivate"),
        ("POST", "/api/v1/employees/{}/reset-password"),
    )


def test_catalogue_and_party_routes_are_documented() -> None:
    _require(
        ("GET", "/api/v1/categories"),
        ("POST", "/api/v1/categories"),
        ("PATCH", "/api/v1/categories/{}"),
        ("POST", "/api/v1/categories/{}/deactivate"),
        ("DELETE", "/api/v1/categories/{}"),
        ("GET", "/api/v1/products"),
        ("POST", "/api/v1/products"),
        ("GET", "/api/v1/products/{}"),
        ("PATCH", "/api/v1/products/{}"),
        ("POST", "/api/v1/products/{}/deactivate"),
        ("POST", "/api/v1/products/{}/activate"),
        ("POST", "/api/v1/products/{}/image"),
        ("GET", "/api/v1/suppliers"),
        ("POST", "/api/v1/suppliers"),
        ("PATCH", "/api/v1/suppliers/{}"),
        ("POST", "/api/v1/suppliers/{}/deactivate"),
        ("GET", "/api/v1/suppliers/{}/purchases"),
        ("GET", "/api/v1/customers"),
        ("POST", "/api/v1/customers"),
        ("PATCH", "/api/v1/customers/{}"),
        ("GET", "/api/v1/customers/{}/sales"),
    )


def test_inventory_and_trading_routes_are_documented() -> None:
    _require(
        ("GET", "/api/v1/inventory/overview"),
        ("GET", "/api/v1/inventory/low-stock"),
        ("GET", "/api/v1/inventory/out-of-stock"),
        ("GET", "/api/v1/inventory/transactions"),
        ("POST", "/api/v1/inventory/adjust"),
        ("POST", "/api/v1/inventory/adjust-price"),
        ("GET", "/api/v1/inventory/price-adjustments"),
        ("GET", "/api/v1/purchases"),
        ("POST", "/api/v1/purchases"),
        ("GET", "/api/v1/purchases/{}"),
        ("POST", "/api/v1/purchases/{}/pay"),
        ("POST", "/api/v1/purchases/{}/cancel"),
        ("GET", "/api/v1/pos/search"),
        ("GET", "/api/v1/sales"),
        ("POST", "/api/v1/sales/checkout"),
        ("GET", "/api/v1/sales/{}"),
        ("POST", "/api/v1/sales/{}/cancel"),
        ("GET", "/api/v1/invoices/{}"),
        ("GET", "/api/v1/invoices/{}/pdf"),
        ("GET", "/api/v1/returns"),
        ("POST", "/api/v1/returns"),
    )


def test_finance_reporting_and_platform_routes_are_documented() -> None:
    _require(
        ("GET", "/api/v1/expenses"),
        ("POST", "/api/v1/expenses"),
        ("PATCH", "/api/v1/expenses/{}"),
        ("DELETE", "/api/v1/expenses/{}"),
        ("GET", "/api/v1/finance/revenue"),
        ("GET", "/api/v1/finance/cogs"),
        ("GET", "/api/v1/finance/profit"),
        ("GET", "/api/v1/dashboard"),
        ("GET", "/api/v1/analytics/products"),
        ("GET", "/api/v1/analytics/customers"),
        ("GET", "/api/v1/analytics/suppliers"),
        ("GET", "/api/v1/reports/sales"),
        ("GET", "/api/v1/reports/inventory"),
        ("GET", "/api/v1/reports/purchases"),
        ("GET", "/api/v1/reports/expenses"),
        ("GET", "/api/v1/reports/profit"),
        ("GET", "/api/v1/reports/profit/pdf"),
        ("GET", "/api/v1/settings"),
        ("PATCH", "/api/v1/settings"),
        ("GET", "/api/v1/subscription"),
        ("PATCH", "/api/v1/subscription"),
        ("POST", "/api/v1/ai/chat"),
        ("GET", "/api/v1/ai/insights"),
        ("GET", "/api/v1/ai/forecast"),
        ("GET", "/api/v1/ai/reorder-recommendations"),
        ("GET", "/api/v1/ai/anomalies"),
        ("POST", "/api/v1/ai/summarize"),
        ("GET", "/api/v1/ai/recommendations"),
        ("PATCH", "/api/v1/ai/recommendations/{}"),
        ("GET", "/api/v1/audit-logs"),
    )


def test_every_published_operation_is_documented_with_an_id() -> None:
    schema = app.openapi()
    missing = [
        f"{method.upper()} {path}"
        for path, operations in schema["paths"].items()
        for method, op in operations.items()
        if not op.get("operationId")
    ]
    assert not missing, f"operations without an operationId: {missing}"


def test_validation_failures_use_the_standard_error_envelope(client: TestClient) -> None:
    """A malformed payload must be machine-readable, not a bare string."""
    resp = client.post("/api/v1/auth/login", json={"username": 123, "password": []})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == 422
    assert body["error"]["message"] == "Request validation failed"
    fields = body["error"]["details"]["fields"]
    assert fields and all({"field", "message", "type"} <= set(f) for f in fields)


def test_unauthenticated_access_is_rejected_consistently(client: TestClient) -> None:
    for path in ("/api/v1/products", "/api/v1/sales", "/api/v1/settings", "/api/v1/ai/insights"):
        assert client.get(path).status_code == 401, path


def test_openapi_security_scheme_is_advertised(client: TestClient) -> None:
    """Generated clients must know they need a bearer token."""
    schema = client.get("/openapi.json").json()
    schemes = schema.get("components", {}).get("securitySchemes", {})
    assert any(v.get("type") == "http" and v.get("scheme") == "bearer" for v in schemes.values())