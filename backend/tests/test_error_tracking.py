"""Error tracking (M5.1/M5.2/M5.5) and observability surface.

These tests prove the crash reporter correlates failures with the request that
produced them, aggregates by fingerprint, and is exposed through the health
probe - all without an external SaaS.
"""

import logging

import pytest
from fastapi.testclient import TestClient

from app.core.error_tracking import ErrorTracker, _fingerprint, get_error_tracker
from tests import factories


@pytest.fixture()
def tracker():
    """A fresh tracker per test; custom sinks are cleared afterwards."""
    t = get_error_tracker()
    t.reset()
    t.clear_sinks()
    t.enabled = True
    yield t
    t.clear_sinks()
    t.reset()
    t.enabled = True


def test_captured_report_carries_route_and_request_id(client: TestClient, tracker) -> None:
    captured = []
    tracker.add_sink(captured.append)

    # Drive a real request through the middleware stack so the ContextVar is set.
    resp = client.get("/health", headers={"X-Request-Id": "trace-0001"})
    assert resp.status_code == 200

    tracker.capture(RuntimeError("boom"))
    assert len(captured) == 1
    report = captured[0]
    assert report.exception_type == "RuntimeError"
    assert report.message == "boom"
    assert report.path == "/health"
    assert report.method == "GET"
    assert report.request_id == "trace-0001"


def test_identical_failures_share_a_fingerprint_and_are_counted(tracker) -> None:
    tracker.capture(ValueError("same"))
    tracker.capture(ValueError("same"))
    assert tracker.status()["total_captured"] == 2
    assert tracker.status()["unique_fingerprints"] == 1

    tracker.capture(ValueError("different"))
    assert tracker.status()["unique_fingerprints"] == 2


def test_fingerprint_is_stable_and_route_sensitive() -> None:
    first = _fingerprint(ValueError("x"), "/api/v1/products")
    second = _fingerprint(ValueError("x"), "/api/v1/products")
    other_route = _fingerprint(ValueError("x"), "/api/v1/sales")
    assert first == second
    assert first != other_route


def test_recent_reports_are_bounded_and_newest_first(tracker) -> None:
    for i in range(60):
        tracker.capture(RuntimeError(f"failure-{i}"))
    reports = tracker.recent_reports(limit=10)
    assert len(reports) == 10
    assert reports[0]["message"] == "failure-59"
    # buffer is capped, so memory cannot grow without bound
    assert len(tracker.recent) <= 50


def test_disabled_tracker_counts_without_emitting(tracker) -> None:
    tracker.enabled = False
    captured = []
    tracker.add_sink(captured.append)
    tracker.capture(RuntimeError("silent"))
    assert captured == []
    assert tracker.status()["total_captured"] == 1


def test_a_failing_sink_never_breaks_the_request(tracker) -> None:
    def exploding_sink(report):
        raise OSError("sink down")

    tracker.add_sink(exploding_sink)
    tracker.capture(RuntimeError("still recorded"))
    assert tracker.status()["total_captured"] == 1


def test_authenticated_failures_carry_tenant_and_actor(client: TestClient, tracker) -> None:
    """``get_current_context`` binds the actor, so reports are tenant-scoped."""
    headers = factories.register_owner(client, email="err-actor@test.com")
    client.get("/api/v1/products", headers=headers)  # resolves the actor

    captured = []
    tracker.add_sink(captured.append)
    tracker.capture(RuntimeError("after auth"))
    assert captured[0].business_id is not None
    assert captured[0].user_id is not None


def test_trackers_are_independent_instances() -> None:
    other = ErrorTracker(environment="test", release="1.0.0-test")
    assert other.enabled is True
    assert other.status()["sentry_installed"] is False
    assert other.status()["release"] == "1.0.0-test"


def test_traceback_helper_formats_full_trace(tracker) -> None:
    try:
        raise ValueError("trace me")
    except ValueError as exc:
        text = tracker.capture_traceback(exc)
    assert "ValueError: trace me" in text
    assert "Traceback" in text


def test_unhandled_exception_returns_500_with_request_id(tracker) -> None:
    """The 500 envelope must stay clean but still be traceable."""
    from app.main import app

    @app.get("/__test__/boom", include_in_schema=False)
    def boom():
        raise RuntimeError("kaboom")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/__test__/boom", headers={"X-Request-Id": "trace-500"})
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == 500
        assert "internal server error" in body["error"]["message"].lower()
        assert body["error"]["request_id"] == "trace-500"
        assert tracker.status()["total_captured"] >= 1
        assert any(r["exception_type"] == "RuntimeError" for r in tracker.recent_reports(50))
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != "/__test__/boom"
        ]


def test_health_exposes_error_tracking_status(client: TestClient) -> None:
    resp = client.get("/health/detailed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error_tracking"]["enabled"] is True
    assert body["error_tracking"]["environment"]
    assert "unique_fingerprints" in body["error_tracking"]
    assert isinstance(body["recent_errors"], list)


def test_liveness_alias_matches_the_canonical_probe(client: TestClient) -> None:
    canonical = client.get("/health")
    alias = client.get("/health/live")
    assert alias.status_code == 200
    assert alias.json() == canonical.json()
    assert canonical.json()["version"]


def test_structured_log_records_carry_correlation_ids(client: TestClient, caplog) -> None:
    """M5.5: request log lines carry the request id and the release stamp."""
    with caplog.at_level(logging.INFO):
        client.get("/health/ready", headers={"X-Request-Id": "log-trace-1"})
    messages = [r.getMessage() for r in caplog.records]
    assert any("/health/ready" in m for m in messages)
    assert any(getattr(r, "request_id", None) == "log-trace-1" for r in caplog.records)
