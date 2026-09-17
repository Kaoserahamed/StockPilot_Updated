"""Contract tests for the dependency manifests and the generated lockfile.

Reproducible installs are a promise this repository makes in the README, in
CONTRIBUTING.md, in the Dockerfiles and in CI: a fresh clone must resolve the
same dependency tree everywhere. These tests fail the suite when a manifest
drifts away from that promise - an unpinned requirement, a lockfile that is not
plain UTF-8 text, a direct pin that is missing from the lock, or a lock line
that would need the network/VCS to install.

Everything is read from disk: nothing is downloaded and nothing is executed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

RUNTIME_REQUIREMENTS = BACKEND_ROOT / "requirements.txt"
DEV_REQUIREMENTS = BACKEND_ROOT / "requirements-dev.txt"
LOCKFILE = BACKEND_ROOT / "requirements.lock.txt"
ROOT_REQUIREMENTS = REPO_ROOT / "requirements.txt"
LOCK_GENERATOR = BACKEND_ROOT / "scripts" / "generate_lockfile.py"

# ``name==version``, tolerating extras (``uvicorn[standard]``) and inline comments.
PIN_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._\-\[\],]*)==(?P<version>[0-9][^\s;#]*)$")


def _strip(raw_line: str) -> str:
    """Drop comment-only lines and inline comments, then trim whitespace."""
    if raw_line.lstrip().startswith("#"):
        return ""
    return raw_line.split(" #", 1)[0].strip()


def requirement_lines(path: Path) -> list[str]:
    """Requirement entries of a pip manifest, comments removed."""
    return [
        stripped
        for stripped in map(_strip, path.read_text(encoding="utf-8").splitlines())
        if stripped
    ]


def pin_parts(line: str) -> tuple[str, str]:
    """Return the normalised ``(name, version)`` of an exact pin."""
    match = PIN_RE.match(line)
    assert match, f"not an exact pin: {line!r}"
    name = match.group("name").split("[", 1)[0].lower().replace("_", "-")
    return name, match.group("version")


def test_every_manifest_a_fresh_clone_needs_is_committed() -> None:
    for path in (RUNTIME_REQUIREMENTS, DEV_REQUIREMENTS, LOCKFILE, ROOT_REQUIREMENTS):
        assert path.is_file(), f"{path} is missing from the repository"


def test_root_manifest_forwards_to_the_backend_manifest() -> None:
    assert requirement_lines(ROOT_REQUIREMENTS) == ["-r backend/requirements.txt"]


@pytest.mark.parametrize(
    "path",
    [RUNTIME_REQUIREMENTS, DEV_REQUIREMENTS],
    ids=["runtime", "dev"],
)
def test_requirements_are_pinned_exactly(path: Path) -> None:
    lines = requirement_lines(path)
    assert lines, f"{path.name} must pin at least one dependency"
    for line in lines:
        assert PIN_RE.match(line), f"{line!r} in {path.name} is not an exact name==version pin"


@pytest.mark.parametrize(
    "path",
    [RUNTIME_REQUIREMENTS, DEV_REQUIREMENTS],
    ids=["runtime", "dev"],
)
def test_requirements_use_no_loose_specifiers(path: Path) -> None:
    joined = "\n".join(requirement_lines(path))
    for loose in ("~=", ">=", "<=", "*"):
        assert loose not in joined, f"{path.name} uses the loose specifier {loose!r}"


def test_lockfile_is_plain_utf8_text() -> None:
    raw = LOCKFILE.read_bytes()
    assert not raw.startswith((b"\xff\xfe", b"\xfe\xff")), "lockfile must not be UTF-16"
    assert b"\x00" not in raw, "lockfile must not contain NUL bytes"
    assert b"\r\n" not in raw, "lockfile must use LF line endings"
    text = raw.decode("utf-8")
    assert text.startswith("#"), "lockfile should start with its generated header"
    assert "DO NOT EDIT BY HAND" in text


def test_lockfile_pins_a_closure_that_installs_from_the_repository_alone() -> None:
    lines = requirement_lines(LOCKFILE)
    assert len(lines) >= 20, "the lockfile should cover the full transitive closure"
    for line in lines:
        assert "==" in line, f"unpinned entry in the lockfile: {line!r}"
        for forbidden in (" @ ", "git+", "file:", "-e ", "://"):
            assert forbidden not in line, f"lockfile entry needs an external source: {line!r}"


def test_lockfile_has_no_duplicate_entries() -> None:
    seen: set[str] = set()
    for line in requirement_lines(LOCKFILE):
        name, _ = pin_parts(line)
        assert name not in seen, f"duplicate package in the lockfile: {name}"
        seen.add(name)


def test_lockfile_covers_every_runtime_pin() -> None:
    """The lockfile resolves the runtime closure; dev tooling stays separate."""
    locked = dict(pin_parts(line) for line in requirement_lines(LOCKFILE))
    for line in requirement_lines(RUNTIME_REQUIREMENTS):
        name, version = pin_parts(line)
        assert name in locked, f"{name} is pinned in requirements.txt but missing from the lockfile"
        assert locked[name] == version, (
            f"{name}=={version} in requirements.txt does not match the lockfile ({locked[name]})"
        )


def test_dev_tooling_stays_out_of_the_runtime_manifest() -> None:
    runtime = {pin_parts(line)[0] for line in requirement_lines(RUNTIME_REQUIREMENTS)}
    dev = {pin_parts(line)[0] for line in requirement_lines(DEV_REQUIREMENTS)}
    for tool in ("pytest", "pytest-cov", "ruff", "mypy", "pip-audit", "pre-commit"):
        assert tool not in runtime, f"{tool} belongs in requirements-dev.txt, not requirements.txt"
    assert {"pytest", "ruff", "mypy"} <= dev


def test_lockfile_is_regenerable_by_a_committed_script() -> None:
    assert LOCK_GENERATOR.is_file(), "the documented generator must be committed"
    source = LOCK_GENERATOR.read_text(encoding="utf-8")
    assert "requirements.lock.txt" in source
    assert "--dry-run" in source, "the generator must resolve without touching the environment"
