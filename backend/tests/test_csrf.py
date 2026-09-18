"""Tests for the CSRF middleware (double-submit cookie pattern)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    PROTECTED_METHODS,
    CSRFMiddleware,
    _generate_csrf_token,
)


def test_csrf_cookie_and_header_constants() -> None:
    assert CSRF_COOKIE_NAME == "csrf_token"
    assert CSRF_HEADER_NAME == "X-CSRF-Token"


def test_protected_methods_set() -> None:
    assert {"POST", "PUT", "PATCH", "DELETE"} == PROTECTED_METHODS


def test_generate_csrf_token_is_url_safe_and_unique() -> None:
    token = _generate_csrf_token()
    assert len(token) >= 32
    assert token != _generate_csrf_token()


def _make_request(
    method: str = "GET",
    cookies: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    request = MagicMock()
    request.method = method
    request.url.path = "/api/v1/items"
    request.cookies = cookies or {}
    request.headers = headers or {}
    return request


def _make_response() -> MagicMock:
    response = MagicMock()
    response.set_cookie = MagicMock()
    return response


@pytest.mark.asyncio
async def test_get_request_without_cookie_sets_csrf_cookie() -> None:
    request = _make_request(method="GET", cookies={})
    response = _make_response()

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=response)

    result = await middleware.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)
    response.set_cookie.assert_called_once()
    assert CSRF_COOKIE_NAME in response.set_cookie.call_args[0]
    assert result is response


@pytest.mark.asyncio
async def test_get_request_with_existing_cookie_does_not_reset() -> None:
    request = _make_request(method="GET", cookies={CSRF_COOKIE_NAME: "existing-token"})
    response = _make_response()

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=response)

    await middleware.dispatch(request, call_next)

    response.set_cookie.assert_not_called()


@pytest.mark.asyncio
async def test_post_request_missing_tokens_is_forbidden() -> None:
    request = _make_request(method="POST", cookies={}, headers={CSRF_HEADER_NAME: ""})

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403
    assert b"CSRF token missing" in result.body
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_post_request_with_cookie_but_no_header_is_forbidden() -> None:
    request = _make_request(
        method="POST",
        cookies={CSRF_COOKIE_NAME: "cookie-token"},
        headers={},
    )

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403


@pytest.mark.asyncio
async def test_post_request_with_mismatched_tokens_is_forbidden() -> None:
    request = _make_request(
        method="POST",
        cookies={CSRF_COOKIE_NAME: "cookie-token"},
        headers={CSRF_HEADER_NAME: "header-token"},
    )

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403
    assert b"CSRF token invalid" in result.body


@pytest.mark.asyncio
async def test_post_request_with_matching_tokens_allows_request() -> None:
    request = _make_request(
        method="POST",
        cookies={CSRF_COOKIE_NAME: "valid-token"},
        headers={CSRF_HEADER_NAME: "valid-token"},
    )
    response = _make_response()

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=response)

    result = await middleware.dispatch(request, call_next)

    call_next.assert_awaited_once_with(request)
    assert result is response


@pytest.mark.asyncio
async def test_put_method_requires_csrf() -> None:
    request = _make_request(method="PUT", cookies={}, headers={})

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403


@pytest.mark.asyncio
async def test_patch_method_requires_csrf() -> None:
    request = _make_request(method="PATCH", cookies={}, headers={})

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403


@pytest.mark.asyncio
async def test_delete_method_requires_csrf() -> None:
    request = _make_request(method="DELETE", cookies={}, headers={})

    middleware = CSRFMiddleware(app=MagicMock())
    call_next = AsyncMock(return_value=_make_response())

    result = await middleware.dispatch(request, call_next)

    assert result.status_code == 403
