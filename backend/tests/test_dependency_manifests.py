"""Contract tests for the dependency manifests and the generated lockfiles.

Reproducible installs are a promise this repository makes in the README, in
CONTRIBUTING.md, in the Dockerfiles and in CI: a fresh clone must resolve the
same dependency tree everywhere. These tests fail the suite when a manifest
drifts away from that promise - an unpinned requirement, a lockfile that is not
plain UTF-8 text, a direct pin that is missing from the lock, or a lock line
that would need the network/VCS to install.

Three committed artifacts are checked together:

* ``backend/requirements.txt`` - the pinned direct runtime deps (what pip,
  Docker and CI install)
* ``backend/requirements.lock`` / ``requirements-dev.lock`` - the pip-resolved
  transitive closures produced by ``scripts/generate_lockfile.py``
* ``backend/uv.lock`` - the uv-resolved closure, which also carries a sha256
  hash for every package it locks

Everything is read from disk: nothing is downloaded and nothing is executed.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

RUNTIME_REQUIREMENTS = BACKEND_ROOT / "requirements.txt"
DEV_REQUIREMENTS = BACKEND_ROOT / "requirements-dev.txt"
LOCKFILE = BACKEND_ROOT / "requirements.lock"
DEV_LOCKFILE = BACKEND_ROOT / "requirements-dev.lock"
ROOT_REQUIREMENTS = REPO_ROOT / "requirements.txt"
LOCK_GENERATOR = BACKEND_ROOT / "scripts" / "generate_lockfile.py"
UV_LOCKFILE = BACKEND_ROOT / "uv.lock"
BACKEND_PYPROJECT = BACKEND_ROOT / "pyproject.toml"

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
    for path in (
        RUNTIME_REQUIREMENTS,
        DEV_REQUIREMENTS,
        LOCKFILE,
        DEV_LOCKFILE,
        UV_LOCKFILE,
        ROOT_REQUIREMENTS,
        BACKEND_PYPROJECT,
    ):
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


LOCKFILES = [LOCKFILE, DEV_LOCKFILE]
LOCKFILE_IDS = ["runtime-lock", "dev-lock"]

#: Lockfile tooling looks for a canonical ``*.lock`` name, not ``*.lock.txt``.
LOCKFILE_NAME_RE = re.compile(r"^requirements(-dev)?\.lock$")


def test_lockfiles_use_a_canonical_lock_filename() -> None:
    for path in LOCKFILES:
        assert LOCKFILE_NAME_RE.match(path.name), f"{path.name} is not a canonical *.lock filename"


@pytest.mark.parametrize("path", LOCKFILES, ids=LOCKFILE_IDS)
def test_lockfile_is_plain_utf8_text(path: Path) -> None:
    raw = path.read_bytes()
    assert not raw.startswith((b"\xff\xfe", b"\xfe\xff")), "lockfile must not be UTF-16"
    assert b"\x00" not in raw, "lockfile must not contain NUL bytes"
    assert b"\r\n" not in raw, "lockfile must use LF line endings"
    text = raw.decode("utf-8")
    assert text.startswith("#"), "lockfile should start with its generated header"
    assert "DO NOT EDIT BY HAND" in text


@pytest.mark.parametrize("path", LOCKFILES, ids=LOCKFILE_IDS)
def test_lockfile_pins_a_closure_that_installs_from_the_repository_alone(path: Path) -> None:
    lines = requirement_lines(path)
    assert len(lines) >= 20, "the lockfile should cover the full transitive closure"
    for line in lines:
        assert "==" in line, f"unpinned entry in the lockfile: {line!r}"
        for forbidden in (" @ ", "git+", "file:", "-e ", "://"):
            assert forbidden not in line, f"lockfile entry needs an external source: {line!r}"


@pytest.mark.parametrize("path", LOCKFILES, ids=LOCKFILE_IDS)
def test_lockfile_has_no_duplicate_entries(path: Path) -> None:
    seen: set[str] = set()
    for line in requirement_lines(path):
        name, _ = pin_parts(line)
        assert name not in seen, f"duplicate package in {path.name}: {name}"
        seen.add(name)


def test_lockfile_covers_every_runtime_pin() -> None:
    """The runtime lock resolves the runtime closure exactly."""
    locked = dict(pin_parts(line) for line in requirement_lines(LOCKFILE))
    for line in requirement_lines(RUNTIME_REQUIREMENTS):
        name, version = pin_parts(line)
        assert name in locked, f"{name} is pinned in requirements.txt but missing from the lockfile"
        assert locked[name] == version, (
            f"{name}=={version} in requirements.txt does not match the lockfile ({locked[name]})"
        )


def test_dev_lockfile_covers_every_pin_in_both_manifests() -> None:
    """The dev lock resolves runtime + tooling, so a fresh clone installs one tree."""
    locked = dict(pin_parts(line) for line in requirement_lines(DEV_LOCKFILE))
    for manifest in (RUNTIME_REQUIREMENTS, DEV_REQUIREMENTS):
        for line in requirement_lines(manifest):
            name, version = pin_parts(line)
            assert name in locked, (
                f"{name} is pinned in {manifest.name} but absent from the dev lock"
            )
            assert locked[name] == version, (
                f"{name}=={version} in {manifest.name} does not match the dev lock ({locked[name]})"
            )
    # The dev lock is a superset of the runtime lock.
    runtime = {pin_parts(line)[0] for line in requirement_lines(LOCKFILE)}
    assert runtime <= set(locked), "the dev lock must also carry the runtime closure"


def test_dev_tooling_stays_out_of_the_runtime_manifest() -> None:
    runtime = {pin_parts(line)[0] for line in requirement_lines(RUNTIME_REQUIREMENTS)}
    dev = {pin_parts(line)[0] for line in requirement_lines(DEV_REQUIREMENTS)}
    tools = (
        "pytest",
        "pytest-cov",
        "ruff",
        "mypy",
        "pip-audit",
        "pre-commit",
        "pip-tools",
        "uv",
    )
    for tool in tools:
        assert tool not in runtime, f"{tool} belongs in requirements-dev.txt, not requirements.txt"
    assert {"pytest", "ruff", "mypy", "pip-tools", "uv"} <= dev


def test_lockfile_is_regenerable_by_a_committed_script() -> None:
    assert LOCK_GENERATOR.is_file(), "the documented generator must be committed"
    source = LOCK_GENERATOR.read_text(encoding="utf-8")
    assert "requirements.lock" in source
    assert "requirements-dev.lock" in source, "the generator must be able to lock the dev closure"
    assert "--dev" in source
    assert "--dry-run" in source, "the generator must resolve without touching the environment"


# --------------------------------------------------------------------------- #
# uv.lock - the uv-resolved closure (hash-pinned)
# --------------------------------------------------------------------------- #

UV_ROOT_PACKAGE = "stockpilot-backend"


def uv_lock_data() -> dict:
    return tomllib.loads(UV_LOCKFILE.read_text(encoding="utf-8"))


def uv_packages() -> dict[str, str]:
    """Return ``{normalised name: version}`` for every locked package."""
    return {
        package["name"].lower().replace("_", "-"): package["version"]
        for package in uv_lock_data()["package"]
    }


def test_uv_lockfile_is_plain_utf8_text() -> None:
    raw = UV_LOCKFILE.read_bytes()
    assert b"\x00" not in raw, "uv.lock must not contain NUL bytes"
    assert b"\r\n" not in raw, "uv.lock must use LF line endings"
    text = raw.decode("utf-8")
    assert text.startswith("version = "), "uv.lock should start with its format version"
    assert 'requires-python = ">=3.11"' in text


def test_uv_lockfile_covers_every_runtime_pin() -> None:
    """uv and pip must agree on every direct runtime pin."""
    locked = uv_packages()
    for line in requirement_lines(RUNTIME_REQUIREMENTS):
        name, version = pin_parts(line)
        assert name in locked, f"{name} is pinned in requirements.txt but absent from uv.lock"
        assert locked[name] == version, (
            f"{name}=={version} in requirements.txt does not match uv.lock ({locked[name]})"
        )


def test_pyproject_dependency_table_matches_the_runtime_manifest() -> None:
    """``[project].dependencies`` and requirements.txt must stay in lockstep."""
    project = tomllib.loads(BACKEND_PYPROJECT.read_text(encoding="utf-8"))["project"]
    declared = {}
    for requirement in project["dependencies"]:
        name, _, version = requirement.partition("==")
        declared[name.split("[", 1)[0].lower().replace("_", "-")] = version
    assert declared, "the pyproject dependency table must pin at least one runtime dep"
    assert declared == dict(pin_parts(line) for line in requirement_lines(RUNTIME_REQUIREMENTS)), (
        "backend/pyproject.toml [project].dependencies and backend/requirements.txt disagree"
    )


def test_uv_lockfile_pins_a_hash_for_every_package() -> None:
    """A lock that does not pin hashes cannot prove what it installs."""
    unhashed: list[str] = []
    for package in uv_lock_data()["package"]:
        if package.get("source", {}).get("virtual"):
            continue  # the project itself: nothing is downloaded for it
        artifacts = [*package.get("wheels", [])]
        if package.get("sdist"):
            artifacts.append(package["sdist"])
        if not artifacts or any("hash" not in artifact for artifact in artifacts):
            unhashed.append(package["name"])
    assert not unhashed, f"uv.lock entries without a pinned hash: {unhashed}"


def test_uv_lockfile_marks_the_project_as_virtual() -> None:
    """uv must not try to build/install the API as a library in CI."""
    config = tomllib.loads(BACKEND_PYPROJECT.read_text(encoding="utf-8"))["tool"]["uv"]
    assert config["package"] is False
    sources = [
        package.get("source", {})
        for package in uv_lock_data()["package"]
        if package["name"] == UV_ROOT_PACKAGE
    ]
    assert sources, "uv.lock should carry the project entry"
    assert sources[0].get("virtual") == ".", "the project entry must be virtual"


def test_uv_drift_check_is_wired_into_ci() -> None:
    """CI must fail when uv.lock is stale relative to pyproject.toml."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv lock --check" in workflow, "CI must run `uv lock --check`"
