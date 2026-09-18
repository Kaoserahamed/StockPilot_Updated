"""Tests for centralized exception classes and HTTP error-handling handlers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from app.core.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    _error_response,
    register_exception_handlers,
)


class TestExceptionClasses:
    def test_app_exception_defaults(self) -> None:
        exc = AppException("something broke")
        assert exc.message == "something broke"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_app_exception_with_details(self) -> None:
        exc = AppException("bad", status_code=400, details={"field": "x"})
        assert exc.status_code == 400
        assert exc.details == {"field": "x"}

    def test_not_found_exception_defaults(self) -> None:
        exc = NotFoundException()
        assert exc.status_code == 404
        assert exc.message == "Resource not found"

    def test_not_found_exception_with_id(self) -> None:
        exc = NotFoundException(resource="Product", resource_id="42")
        assert "42" in exc.message
        assert "Product" in exc.message

    def test_conflict_exception_defaults(self) -> None:
        exc = ConflictException()
        assert exc.status_code == 409
        assert exc.message == "Resource conflict"

    def test_conflict_exception_custom(self) -> None:
        exc = ConflictException("Email already registered")
        assert exc.message == "Email already registered"

    def test_forbidden_exception(self) -> None:
        exc = ForbiddenException()
        assert exc.status_code == 403

    def test_forbidden_exception_custom(self) -> None:
        exc = ForbiddenException("Not your data")
        assert exc.message == "Not your data"

    def test_bad_request_exception(self) -> None:
        exc = BadRequestException()
        assert exc.status_code == 422

    def test_bad_request_exception_custom(self) -> None:
        exc = BadRequestException("Missing field")
        assert exc.message == "Missing field"

    def test_rate_limit_exception(self) -> None:
        exc = RateLimitException()
        assert exc.status_code == 429


class TestErrorResponse:
    def test_basic_response(self) -> None:
        resp = _error_response(404, "Not found")
        assert resp.status_code == 404
        assert resp.body == b'{"error":{"code":404,"message":"Not found"}}'

    def test_with_details(self) -> None:
        resp = _error_response(400, "Bad", details={"field": "email"})
        body = resp.body.decode()
        assert "details" in body
        assert "email" in body

    def test_with_request_id(self) -> None:
        resp = _error_response(500, "Error", request_id="req-123")
        body = resp.body.decode()
        assert "req-123" in body


class _SimpleModel(BaseModel):
    name: str


def test_register_exception_handlers_app_exception(client_factory=None) -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-exception")
    def raise_app_exc() -> None:
        raise AppException("custom", status_code=400, details={"k": "v"})

    client = _test_client(app)
    resp = client.get("/app-exception")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["message"] == "custom"
    assert body["error"]["details"] == {"k": "v"}


def test_register_exception_handlers_validation_error() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/validation-error")
    def raise_validation() -> None:
        raise RequestValidationError([])

    client = _test_client(app)
    resp = client.get("/validation-error")
    assert resp.status_code == 422


def test_register_exception_handlers_pydantic_error() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/pydantic-error")
    def raise_pydantic() -> None:
        _SimpleModel.model_validate({})

    client = _test_client(app)
    resp = client.get("/pydantic-error")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["message"] == "Data validation failed"


def test_register_exception_handlers_unhandled_exception() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/unhandled")
    def raise_runtime() -> None:
        raise RuntimeError("boom")

    client = _test_client(app)
    resp = client.get("/unhandled")
    assert resp.status_code == 500
    body = resp.json()
    assert "internal server error" in body["error"]["message"].lower()


def _test_client(app: FastAPI):
    """Create a TestClient that exercises the registered handlers.

    ``raise_server_exceptions=False`` lets the app's own 500 handler run and
    return a structured response instead of letting the exception propagate
    out of the test client.
    """
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)
