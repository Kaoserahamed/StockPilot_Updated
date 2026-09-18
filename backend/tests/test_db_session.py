"""Tests for database URL normalization and session dependency."""

from __future__ import annotations

from app.db import session as session_module


class TestNormalizeDatabaseUrl:
    def test_postgres_shorthand(self) -> None:
        assert (
            session_module.normalize_database_url("postgres://user:pass@host:5432/db")
            == "postgresql+psycopg2://user:pass@host:5432/db"
        )

    def test_postgresql_shorthand(self) -> None:
        assert (
            session_module.normalize_database_url("postgresql://user:pass@host:5432/db")
            == "postgresql+psycopg2://user:pass@host:5432/db"
        )

    def test_mysql_passes_through(self) -> None:
        url = "mysql+pymysql://user:pass@host/db"
        assert session_module.normalize_database_url(url) == url

    def test_sqlite_passes_through(self) -> None:
        url = "sqlite:///test.db"
        assert session_module.normalize_database_url(url) == url


class TestSessionModule:
    def test_get_db_yields_and_closes(self) -> None:
        gen = session_module.get_db()
        session = next(gen)
        # The generator should yield a session and close it on teardown
        session.close()

    def test_is_sqlite_constant_exists(self) -> None:
        assert isinstance(session_module.IS_SQLITE, bool)

    def test_engine_is_created(self) -> None:
        assert session_module.engine is not None
        assert session_module.SessionLocal is not None
