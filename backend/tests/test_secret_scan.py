"""Tests for ``backend/scripts/scan_secrets.py``, the committed-secret gate.

The first test scans this repository exactly the way CI does, so a credential
that lands in a commit fails the local suite as well.

The negative controls below are real-looking strings that must be detected. The
provider-shaped ones are assembled from fragments at runtime (see the comment
above the fixtures) so the repository itself never contains a scannable token;
the generic literals carry a trailing ``pragma: allowlist secret`` so the
repository scan skips *this* file while the string handed to ``scan_text`` stays
pragma-free.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = REPO_ROOT / "backend" / "scripts" / "scan_secrets.py"


def _load_scanner() -> ModuleType:
    """Import the script by path: it lives outside the ``app`` package."""
    spec = importlib.util.spec_from_file_location("scan_secrets", SCANNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so the module has to
    # be registered before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scan_secrets = _load_scanner()

# The fixtures below are assembled at runtime on purpose. Their values must look
# exactly like real provider tokens for the detection test to mean anything, but
# committing such a literal trips GitHub push protection (and every other
# scanner) on each push, even though nothing here is a usable credential. Split
# fragments keep the assertion honest without committing a scannable string.
FAKE_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
FAKE_GOOGLE_KEY = "AIza" + "SyA0123456789abcdefghijklmnopqrstuv"
FAKE_GITHUB_TOKEN = "ghp_" + "0123456789abcdefghijklmnopqrstuvwxyz"
FAKE_SLACK_TOKEN = "xoxb-" + "1234567890-abcdefghijkl"
FAKE_STRIPE_KEY = "sk_live_" + "0123456789abcdef"
FAKE_PRIVATE_KEY_BLOCK = "-----BEGIN " + "RSA PRIVATE KEY-----"
FAKE_JWT = "eyJhbGciOiJIUzI1NiJ9" + ".eyJzdWIiOiIxIn0" + ".abcdefghijkl"


def test_the_repository_contains_no_credential_literals() -> None:
    findings = scan_secrets.scan_paths(REPO_ROOT)
    report = "\n".join(str(finding) for finding in findings)
    assert findings == [], f"credential-looking literals are committed:\n{report}"


@pytest.mark.parametrize(
    "line",
    [
        f'aws_key = "{FAKE_AWS_KEY}"',
        f'google_key = "{FAKE_GOOGLE_KEY}"',
        f'github_token = "{FAKE_GITHUB_TOKEN}"',
        f'slack_token = "{FAKE_SLACK_TOKEN}"',
        f'stripe_key = "{FAKE_STRIPE_KEY}"',
        FAKE_PRIVATE_KEY_BLOCK,
        f'jwt = "{FAKE_JWT}"',
    ],
    ids=[
        "aws-access-key-id",
        "google-api-key",
        "github-token",
        "slack-token",
        "stripe-live-key",
        "private-key-block",
        "json-web-token",
    ],
)
def test_provider_token_shapes_are_detected(line: str) -> None:
    findings = scan_secrets.scan_text(line)
    assert findings, f"scanner missed a credential: {line!r}"


@pytest.mark.parametrize(
    "line",
    [
        'password = "Sup3rS3cretValue"',  # pragma: allowlist secret
        "DB_PASSWORD=Sup3rS3cretValue1",  # pragma: allowlist secret
        'api_key: "abc123XYZ456"',  # pragma: allowlist secret
        '{"client_secret": "abc123XYZ456"}',  # pragma: allowlist secret
    ],
)
def test_credential_literals_are_detected(line: str) -> None:
    assert scan_secrets.scan_text(line), f"scanner missed a literal: {line!r}"


@pytest.mark.parametrize(
    "line",
    [
        "DB_PASSWORD=${DB_PASSWORD}",
        'export PGPASSWORD="${DB_PASSWORD}"',
        'secret_key = "replace-with-a-strong-random-secret"',
        "SECRET_KEY=change-me-to-a-long-random-secret",
        "PASSWORD=changeme",
        "SECRET_KEY: ci-only-secret-not-used-in-production",
        'api_key = "<your-api-key>"',
        'password = ""',
        "PASSWORD=",
    ],
)
def test_placeholders_are_not_reported(line: str) -> None:
    assert scan_secrets.scan_text(line) == [], f"false positive on a placeholder: {line!r}"


@pytest.mark.parametrize(
    "line",
    [
        'TOKEN_KEY = "stockpilot_token"',
        "SESSION_KEY='ps_session'",
        "const apiKeyName = 'x-api-key';",
        "sqlalchemy.url = driver://user:pass@localhost/dbname",
    ],
)
def test_identifiers_are_not_reported(line: str) -> None:
    # Documents the precision trade-off of ``looks_like_secret``: a storage key
    # or a URL is not a credential, so a digit-free value stays unreported.
    assert scan_secrets.scan_text(line) == [], f"false positive on an identifier: {line!r}"


@pytest.mark.parametrize(
    "line, expected_value",
    [
        ('password = "Abcd12X"', "Abcd12X"),  # pragma: allowlist secret
        ("DB_PASSWORD=Secur34", "Secur34"),  # pragma: allowlist secret
        ('api_key = "abc123X"', "abc123X"),  # pragma: allowlist secret
    ],
)
def test_sub_policy_length_values_are_not_reported(line: str, expected_value: str) -> None:
    # Documents the length floor in ``_SECRET_SHAPED_VALUE``: a 7-char value
    # still has a digit and mixed case, but is below the 8-char production
    # password-policy floor, so it cannot be a usable credential and is not
    # flagged. This is the deliberate trade-off called out in the scanner
    # docstring.
    assert len(expected_value) < 8
    assert not scan_secrets.looks_like_secret(expected_value)
    assert scan_secrets.scan_text(line) == [], f"false positive below length floor: {line!r}"


def test_allowlist_pragma_suppresses_a_finding() -> None:
    line = 'password = "Sup3rS3cretValue"  # pragma: allowlist secret'
    assert scan_secrets.scan_text(line) == []


def test_utf16_encoded_files_are_still_scanned(tmp_path: Path) -> None:
    (tmp_path / "leak.py").write_text("DB_PASSWORD=Sup3rS3cretValue1", encoding="utf-16")
    findings = scan_secrets.scan_paths(tmp_path, [Path("leak.py")])
    assert findings, "a UTF-16 file must not hide a credential"


def test_redaction_keeps_only_a_hint() -> None:
    redacted = scan_secrets.redact("Sup3rS3cretValue")
    assert "Sup3rS3cretValue" not in redacted
    assert redacted.startswith("Su")


def test_cli_exit_codes_drive_the_ci_gate(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("value = 1\n", encoding="utf-8")
    dirty = tmp_path / "dirty.py"
    dirty.write_text('password = "Sup3rS3cretValue"', encoding="utf-8")  # pragma: allowlist secret

    assert scan_secrets.main(["--root", str(tmp_path), "--quiet"]) == 1
    dirty.unlink()
    assert scan_secrets.main(["--root", str(tmp_path), "--quiet"]) == 0
