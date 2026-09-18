"""Tests for the rate-limiting configuration."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI

from app.core.rate_limit import (
    _HAS_SLOWAPI,
    _get_limit_key,
    rate_limit,
    setup_rate_limiting,
)


def test_has_slowapi_flag() -> None:
    # slowapi is a declared dependency, so the fast-path should be taken.
    assert _HAS_SLOWAPI is True


def test_get_limit_key_prefers_user_id() -> None:
    request = MagicMock()
    request.state.user_id = 42

    key = _get_limit_key(request)

    assert key == "user:42"


def test_get_limit_key_falls_back_to_remote_address() -> None:
    request = MagicMock()
    request.state.user_id = None
    request.client = MagicMock(host="10.0.0.1")

    key = _get_limit_key(request)

    assert key == "10.0.0.1"


def test_setup_rate_limiting_attaches_limiter() -> None:
    app = FastAPI()
    setup_rate_limiting(app)

    assert hasattr(app.state, "limiter")
    # The exception handler for RateLimitExceeded must be registered
    # (registered via add_exception_handler with the exception class as key).
    handler_keys = [k for k in app.exception_handlers if isinstance(k, type)]
    # RateLimitExceeded should be a registered handler key when slowapi is present.
    from slowapi.errors import RateLimitExceeded

    assert RateLimitExceeded in handler_keys


def test_setup_rate_limiting_is_idempotent() -> None:
    app = FastAPI()
    setup_rate_limiting(app)
    setup_rate_limiting(app)  # should not raise
    assert hasattr(app.state, "limiter")


def test_rate_limit_decorator_marks_function() -> None:
    @rate_limit(requests=10, window_seconds=60)
    def my_endpoint() -> str:
        return "ok"

    assert my_endpoint._rate_limit == (10, 60)  # type: ignore[attr-defined]
    assert my_endpoint() == "ok"
