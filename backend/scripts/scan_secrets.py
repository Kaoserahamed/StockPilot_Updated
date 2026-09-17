#!/usr/bin/env python
"""Fail the build when a credential-looking literal is committed.

Usage
-----
    python backend/scripts/scan_secrets.py            # scan the tracked tree
    python backend/scripts/scan_secrets.py --quiet    # summary only

Exit status is ``0`` when clean and ``1`` when anything is reported, so the
script works both as a CI gate and as a library (``scan_text``) for tests.

Design
------
* Only files tracked by git are scanned (``git ls-files``), so virtualenvs,
  ``node_modules`` and build output can never produce noise. Outside a git
  checkout the script falls back to walking the tree, skipping the usual cache
  and dependency directories.
* Rules are deliberately high-signal: private-key blocks, provider token
  formats (AWS, Google, GitHub, Slack, Stripe), JSON Web Tokens, and quoted
  literals assigned to password/secret/token/API-key names.
* Values that announce themselves as placeholders are ignored: ``changeme``,
  ``replace-with-...``, ``ci-only-...``, ``test-...``, ``${DB_PASSWORD}``
  expansions, ``<...>``, empty strings and the like.
* A matched value must still look like a secret (a digit, or mixed case, plus
  no whitespace) which keeps storage keys such as ``stockpilot_token`` out of
  the report. The trade-off is deliberate: an all-lowercase, digit-free
  credential is not detected, and neither is a short one.
* A line containing ``pragma: allowlist secret`` is skipped, which is how the
  negative controls in ``backend/tests/test_secret_scan.py`` stay scannable.
* Files with a UTF-16 BOM are decoded rather than skipped, so a credential
  cannot hide behind an unusual encoding.

CI runs this in the ``backend / secret scan`` job (``.github/workflows/ci.yml``)
and the backend suite runs it against the repository, so a leaked credential
fails the build instead of shipping.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWLIST_PRAGMA = "pragma: allowlist secret"

SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "venv",
    }
)

BINARY_SUFFIXES = frozenset(
    {
        ".db",
        ".dll",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".pdf",
        ".png",
        ".so",
        ".sqlite3",
        ".webp",
        ".woff",
        ".woff2",
        ".zip",
    }
)

MAX_FILE_BYTES = 2 * 1024 * 1024

PLACEHOLDER_MARKERS = (
    "<",
    "***",
    "xxxx",
    "changeme",
    "change-me",
    "change_me",
    "ci-only",
    "development-only",
    "dev-only",
    "dummy",
    "example",
    "fake",
    "local-only",
    "not-for-production",
    "not_for_production",
    "placeholder",
    "redacted",
    "replace-with",
    "replace_with",
    "sample",
    "test-",
    "test_",
    "your-",
    "your_",
    "yourdomain",
)

_PRIVATE_KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_AWS_ACCESS_KEY_ID = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
_GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")
_GITHUB_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")
_SLACK_TOKEN = re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")
_STRIPE_LIVE_KEY = re.compile(r"\b[sr]k_live_[A-Za-z0-9]{10,}\b")
_JSON_WEB_TOKEN = re.compile(
    r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"
)

#: ``name = "value"`` / ``"name": "value"`` - quotes optional around the name.
_CREDENTIAL_NAME = r"[A-Za-z0-9_.]*(?:password|passwd|pwd|secret|token|api[_-]?key)[A-Za-z0-9_.]*"
_QUOTED_LITERAL = re.compile(
    rf"(?i)['\"]?(?P<name>{_CREDENTIAL_NAME})['\"]?\s*[:=]\s*"
    rf"(?P<quote>['\"])(?P<value>[^'\"\n]{{6,}})(?P=quote)"
)

#: ``PASSWORD=literal`` / ``SECRET_KEY: literal`` on its own line (dotenv, YAML).
_ENV_ASSIGNMENT = re.compile(
    r"(?i)^\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(?P<value>[^\s#]+)\s*$"
)
_SENSITIVE_NAME = re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key)")
_SECRET_SHAPED_VALUE = re.compile(r"^[A-Za-z0-9_\-./+=:@!]{12,}$")

TOKEN_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key-block", _PRIVATE_KEY_BLOCK),
    ("aws-access-key-id", _AWS_ACCESS_KEY_ID),
    ("google-api-key", _GOOGLE_API_KEY),
    ("github-token", _GITHUB_TOKEN),
    ("slack-token", _SLACK_TOKEN),
    ("stripe-live-key", _STRIPE_LIVE_KEY),
    ("json-web-token", _JSON_WEB_TOKEN),
)


@dataclass(frozen=True)
class Finding:
    """One credential-looking match, redacted for safe logging."""

    path: str
    line_number: int
    rule: str
    excerpt: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line_number}: {self.rule}: {self.excerpt}"


def redact(value: str) -> str:
    """Keep a two-character hint, never the credential itself."""
    value = value.strip()
    if len(value) <= 2:
        return "**"
    return f"{value[:2]}{'*' * min(len(value) - 2, 8)}"


def is_placeholder(value: str) -> bool:
    """True when a value obviously is not a real credential."""
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def looks_like_secret(value: str) -> bool:
    """Heuristic for free-form literals (provider token shapes are exact).

    Requires a digit or mixed case in a whitespace-free, long enough value so
    identifiers such as ``stockpilot_token`` are not reported.
    """
    value = value.strip()
    if is_placeholder(value) or not _SECRET_SHAPED_VALUE.match(value):
        return False
    has_digit = any(char.isdigit() for char in value)
    has_upper = any(char.isupper() for char in value)
    has_lower = any(char.islower() for char in value)
    return has_digit or (has_upper and has_lower)


def scan_text(text: str, origin: str = "<memory>") -> list[Finding]:
    """Return every credential-looking finding in ``text``.

    ``origin`` only labels the report - normally a repository-relative path.
    """
    findings: list[Finding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if ALLOWLIST_PRAGMA in line:
            continue

        for rule, pattern in TOKEN_RULES:
            match = pattern.search(line)
            if match:
                findings.append(Finding(origin, line_number, rule, redact(match.group(0))))

        for match in _QUOTED_LITERAL.finditer(line):
            value = match.group("value")
            if looks_like_secret(value):
                findings.append(
                    Finding(origin, line_number, "quoted-credential-literal", redact(value))
                )

        assignment = _ENV_ASSIGNMENT.match(line)
        if assignment and _SENSITIVE_NAME.search(assignment.group("name")):
            value = assignment.group("value")
            if looks_like_secret(value):
                findings.append(
                    Finding(origin, line_number, "credential-in-env-assignment", redact(value))
                )

    return findings


def _decode(raw: bytes) -> str | None:
    """Decode file bytes, or return ``None`` for binary content."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            return None
    if b"\x00" in raw[:1024]:
        return None
    return raw.decode("utf-8", errors="replace")


def _walk(root: Path) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRECTORIES for part in relative.parts):
            continue
        yield relative


def tracked_files(root: Path) -> list[Path]:
    """Repository-relative paths tracked by git, else a filtered tree walk."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(_walk(root))
    return [Path(name) for name in result.stdout.split("\0") if name]


def scan_paths(root: Path, paths: Iterable[Path] | None = None) -> list[Finding]:
    """Scan ``paths`` (default: every tracked file under ``root``)."""
    findings: list[Finding] = []
    for relative in tracked_files(root) if paths is None else paths:
        path = root / relative
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        text = _decode(path.read_bytes())
        if text is None:
            continue
        findings.extend(scan_text(text, relative.as_posix()))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="tree to scan")
    parser.add_argument("--quiet", action="store_true", help="print the summary only")
    args = parser.parse_args(argv)

    findings = scan_paths(args.root)
    for finding in findings:
        print(finding)

    if findings:
        print(
            f"scan_secrets: {len(findings)} finding(s) - remove the literal, "
            f"or add '{ALLOWLIST_PRAGMA}' to a genuine placeholder.",
            file=sys.stderr,
        )
        return 1

    if not args.quiet:
        print(f"scan_secrets: no credential-looking literals found in {args.root}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
