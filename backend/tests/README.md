# Backend test guide (`backend/tests/`)

Canonical command (also what CI runs):

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

- **Isolation:** `conftest.py` builds a fresh in-memory SQLite database per
  test (StaticPool), then overrides the `get_db` dependency, so the suite
  needs no PostgreSQL, Docker, network or Gemini key.
- **Builders:** `factories.py` creates owners, staff, catalogue, parties and
  trading documents through the real HTTP API — never by poking the ORM
  directly — so tests exercise validation, tenancy guards and audit writes.
- **Adding a test:** copy the nearest `test_*.py`, use the `client` and
  `shop` fixtures, and keep one behaviour per test function.
- **Coverage:** `--cov=app --cov-report=term-missing` (configured in
  `pyproject.toml [tool.coverage.*]`); CI uploads `coverage.xml`.
