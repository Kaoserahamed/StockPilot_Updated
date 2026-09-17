#!/usr/bin/env python
"""Generate ``requirements.lock.txt`` for the backend.

``requirements.txt`` pins only the direct dependencies. This script resolves the
full dependency closure with pip's dry-run report and writes exact pins for every
transitive package, so a fresh clone installs a byte-for-byte reproducible tree.

Usage (from the ``backend`` directory)::

    python scripts/generate_lockfile.py

Verify a clean install with::

    python -m venv /tmp/verify && /tmp/verify/bin/pip install -r requirements.lock.txt

The output is intentionally free of timestamps so re-running it produces no diff
unless a dependency actually changed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
LOCKFILE = BACKEND_DIR / "requirements.lock.txt"

HEADER = """\
# =============================================================================
# StockPilot backend - GENERATED LOCKFILE. DO NOT EDIT BY HAND.
#
# Contains the exact, fully resolved dependency closure of requirements.txt
# (direct + transitive), for reproducible installs:
#
#     pip install -r requirements.lock.txt
#
# Regenerate after changing requirements.txt:
#
#     cd backend && python scripts/generate_lockfile.py
#
# Development-only tooling is intentionally excluded; it lives in
# requirements-dev.txt.
# =============================================================================
"""


def resolve_pins() -> list[str]:
    """Ask pip to resolve requirements.txt and return sorted ``name==version`` pins."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "pip-report.json"
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--quiet",
            "--report",
            str(report_path),
            "-r",
            str(REQUIREMENTS),
        ]
        # The command is a fixed list built here - no shell, no untrusted input.
        subprocess.run(command, check=True, cwd=BACKEND_DIR)
        report = json.loads(report_path.read_text(encoding="utf-8"))

    pins: set[str] = set()
    for entry in report.get("install", []):
        metadata = entry.get("metadata", {})
        name = metadata.get("name")
        version = metadata.get("version")
        if name and version:
            pins.add(f"{name}=={version}")

    if not pins:
        raise SystemExit("pip resolved no packages - refusing to write an empty lockfile")

    return sorted(pins, key=str.lower)


def main() -> int:
    pins = resolve_pins()
    body = "\n".join(pins)
    LOCKFILE.write_text(f"{HEADER}\n{body}\n", encoding="utf-8")
    print(f"Wrote {LOCKFILE} ({len(pins)} pinned packages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
