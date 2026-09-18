"""Export the FastAPI OpenAPI document to ``docs/api/openapi.yaml``.

The published contract between the backend and the Next.js client is worth
reviewing and diffing in a pull request, so the generated document is committed
instead of only being served at ``/openapi.json``:

    cd backend
    python scripts/export_openapi.py      # writes ../docs/api/openapi.yaml

``tests/test_api_contract.py`` fails when the committed copy drifts from
``app.openapi()``, so run this after touching a route, schema or response model.

Importing ``app.main`` builds ``Settings()``, which needs ``DATABASE_URL`` and
``SECRET_KEY`` to be set to *something* (any value works for this script)::

    DATABASE_URL=sqlite:// SECRET_KEY=doc-export python scripts/export_openapi.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.yaml"


def render_openapi_document() -> str:
    """Return the application's OpenAPI schema as deterministic YAML text.

    Insertion order is preserved (``openapi:`` then ``info:`` then ``paths:``)
    because FastAPI builds the schema dict in the conventional order; ``sort_keys``
    would only move ``components`` to the top and hurt readability.
    """
    # Imported lazily: the backend package is only importable once BACKEND_ROOT
    # is on sys.path, which main() arranges before calling this function.
    from app.main import app

    return yaml.safe_dump(
        app.openapi(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )


def main() -> int:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    text = render_openapi_document()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT} ({len(text):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
