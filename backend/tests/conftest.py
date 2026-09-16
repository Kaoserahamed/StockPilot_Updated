"""Shared pytest fixtures for the StockPilot backend test suite.

Design notes
------------
* Every test runs against a **fresh in-memory SQLite database**. The engine is
  created per test and disposed afterwards, so `pytest` needs no PostgreSQL,
  Docker or network access - it runs on a machine that has never seen this
  project before.
* Data is created through the **public HTTP API** (see ``tests/factories.py``)
  rather than by inserting rows directly, so fixtures exercise the same
  validation, tenancy guards and audit writes that real clients hit.
* The application lifespan is deliberately not started: it would create tables
  on the configured database. The dependency override below is what actually
  feeds the app its session, which keeps each test hermetic and fast.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

# The environment must be complete BEFORE the app package is imported, because
# Settings is instantiated at import time and requires DATABASE_URL/SECRET_KEY.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JSON_LOGS", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("GEMINI_API_KEY", "")

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (importing registers every mapper)
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_session() -> Iterator[Session]:
    """An isolated in-memory database session, torn down after each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """A TestClient whose ``get_db`` dependency resolves to the test session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def shop(client: TestClient):
    """A ready-to-use shop: owner, supplier, stocked product and a customer.

    This is the fixture most feature tests should use - it removes the
    repetition of building the same prerequisites in every module.
    """
    from tests import factories

    return factories.seed_shop(client)
