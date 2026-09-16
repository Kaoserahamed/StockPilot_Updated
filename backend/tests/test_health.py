"""Health probes, service metadata and cross-cutting middleware behaviour."""

from fastapi.testclient import TestClient

from tests import factories


def test_liveness_probe_reports_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "stockpilot-api"


def test_readiness_probe_verifies_database_connectivity(client: TestClient) -> None:
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "database": "connected"}


def test_detailed_health_reports_dependency_status(client: TestClient) -> None:
    resp = client.get("/health/detailed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "connected"
    assert body["status"] == "healthy"


def test_root_endpoint_returns_service_metadata(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api"] == "/api/v1"
    assert body["health"] == "/health"
    assert body["version"]


def test_security_headers_are_present_on_responses(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
    assert "camera=()" in resp.headers["Permissions-Policy"]


def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    resp = client.get("/health")
    request_id = resp.headers.get("X-Request-Id")
    assert request_id is not None
    assert len(request_id) == 16


def test_caller_supplied_request_id_is_propagated(client: TestClient) -> None:
    """Reusing the caller's id lets logs be correlated end to end."""
    resp = client.get("/health", headers={"X-Request-Id": "trace-abc-123"})
    assert resp.headers["X-Request-Id"] == "trace-abc-123"


def test_response_time_header_is_numeric(client: TestClient) -> None:
    resp = client.get("/health")
    assert float(resp.headers["X-Response-Time-Ms"]) >= 0


def test_state_changing_requests_are_never_cached(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cache-post@test.com")
    resp = client.post("/api/v1/categories", json={"name": "Cached"}, headers=headers)
    assert resp.status_code == 201
    assert resp.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
    assert resp.headers["Pragma"] == "no-cache"


def test_catalogue_reads_are_privately_cacheable(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cache-get@test.com")
    resp = client.get("/api/v1/products", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=30"


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/definitely-not-a-route").status_code == 404


def test_openapi_schema_is_exposed_outside_production(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json()["info"]["title"]
