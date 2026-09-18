"""Production configuration guard: SECRET_KEY / CORS / credentials hygiene."""

from __future__ import annotations

import importlib
import os


def _load_settings(monkeypatch, **env: str):  # type: ignore[no-untyped-def]
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.core.config as config_module

    return importlib.reload(config_module)


def test_production_rejects_placeholder_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import pytest

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError, match="SECRET_KEY is too weak"):
        _load_settings(
            monkeypatch,
            DATABASE_URL="sqlite://",
            SECRET_KEY="dev-secret-key-not-for-production",
            ENVIRONMENT="production",
        )


def test_production_accepts_strong_random_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import secrets

    module = _load_settings(
        monkeypatch,
        DATABASE_URL="sqlite://",
        SECRET_KEY=secrets.token_urlsafe(48),
        ENVIRONMENT="production",
    )
    assert len(module.settings.secret_key) >= 32


def test_test_env_keeps_short_fixture_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    module = _load_settings(
        monkeypatch,
        DATABASE_URL="sqlite://",
        SECRET_KEY="test-secret-key-not-for-production",
        ENVIRONMENT="test",
    )
    assert module.settings.secret_key.startswith("test-secret-key")


def test_cors_wildcard_with_credentials_is_rejected(client) -> None:  # type: ignore[no-untyped-def]
    """A wildcard origin must never be combined with allow_credentials.

    Regression test for the CORS misconfiguration class: browsers reject it
    and it hides real origin-allowlist bugs in production.
    """
    from starlette.middleware.cors import CORSMiddleware

    from app.main import app

    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "CORSMiddleware must be registered"
    options = cors[0].kwargs
    if options.get("allow_origins") == ["*"]:
        assert options.get("allow_credentials") is not True
    # The API itself must stay reachable regardless of CORS settings.
    resp = client.get("/health")
    assert resp.status_code == 200


def test_no_tracked_upload_binaries() -> None:
    """Runtime user content must never be committed (only .gitkeep files)."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent
    out = subprocess.run(
        ["git", "ls-files", "uploads", "backend/uploads"],
        capture_output=True,
        text=True,
        cwd=root,
    )
    tracked = [line for line in out.stdout.splitlines() if line.strip()]
    assert all(name.endswith(".gitkeep") or name.endswith(".gitignore") for name in tracked), (
        f"binary user content is tracked: {tracked}"
    )
    assert "SECRET_KEY" not in os.environ.get("PYTEST_CURRENT_TEST", "")
