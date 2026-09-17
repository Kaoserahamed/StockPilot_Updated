"""Contract tests for the quality gates this repository advertises.

The README, docs/TESTING.md and CONTRIBUTING.md all promise that linting,
static types, both test suites, coverage floors, dependency audits, a secret
scan and a container build run in CI. These tests fail when one of those gates
quietly disappears from the configuration - exactly the regression a reviewer
or a new contributor notices first.

Read-only: ``tomllib`` plus text parsing of committed configuration files.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
BACKEND_PYPROJECT = REPO_ROOT / "backend" / "pyproject.toml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
VITEST_CONFIG = REPO_ROOT / "frontend" / "vitest.config.ts"
PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
ROOT_DOCKERFILE = REPO_ROOT / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
DEVCONTAINER = REPO_ROOT / ".devcontainer" / "devcontainer.json"
SECRET_SCANNER = REPO_ROOT / "backend" / "scripts" / "scan_secrets.py"
SECRET_SCANNER_TESTS = REPO_ROOT / "backend" / "tests" / "test_secret_scan.py"


def load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def ci_workflow() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_backend_pytest_enforces_a_coverage_floor() -> None:
    config = load_toml(BACKEND_PYPROJECT)["tool"]
    assert config["coverage"]["run"]["source"] == ["app"]
    assert config["coverage"]["report"]["fail_under"] >= 80
    assert config["pytest"]["ini_options"]["testpaths"] == ["tests"]


def test_repo_root_can_run_the_backend_suite() -> None:
    config = load_toml(ROOT_PYPROJECT)["tool"]
    options = config["pytest"]["ini_options"]
    assert options["testpaths"] == ["backend/tests"]
    assert "backend" in options["pythonpath"]
    assert config["coverage"]["report"]["fail_under"] >= 80


def test_ci_gates_lint_types_tests_and_dependency_audits() -> None:
    workflow = ci_workflow()
    for command in (
        "ruff check app tests",
        "ruff format --check app tests",
        "mypy app",
        "--cov-fail-under=80",
        "--cov=app",
        "npm run lint",
        "npm run typecheck",
        "npm run test:coverage",
        "npm run format:check",
        "npm run build",
        "pip-audit -r requirements.txt",
        "npm audit --audit-level=high",
        "requirements.lock.txt",
    ):
        assert command in workflow, f"CI no longer runs: {command}"


def test_ci_runs_every_suite_on_pull_requests_and_main() -> None:
    workflow = ci_workflow()
    assert "pull_request:" in workflow
    assert "branches: [main]" in workflow
    for job in (
        "backend-lint:",
        "backend-test:",
        "backend-audit:",
        "frontend-check:",
        "frontend-audit:",
        "backend-reproducible-install:",
        "backend-secret-scan:",
    ):
        assert job in workflow, f"missing CI job: {job}"


def test_ci_builds_a_container_for_every_dockerfile() -> None:
    workflow = ci_workflow()
    assert "docker/build-push-action@" in workflow
    for dockerfile in ("./Dockerfile", "./backend/Dockerfile", "./frontend/Dockerfile"):
        assert dockerfile in workflow, f"CI does not build {dockerfile}"


def test_tagged_releases_publish_an_image_and_a_github_release() -> None:
    workflow = ci_workflow()
    assert 'tags: ["v*"]' in workflow, "the workflow must run on version tags"
    assert "startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "docker/metadata-action@" in workflow
    assert "softprops/action-gh-release@" in workflow


def test_frontend_declares_scripts_and_coverage_thresholds() -> None:
    scripts = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]
    for script in ("lint", "typecheck", "test", "test:coverage", "build", "format:check"):
        assert script in scripts, f"frontend script missing: {script}"
    config = VITEST_CONFIG.read_text(encoding="utf-8")
    assert "thresholds" in config, "vitest must fail the run below the coverage floor"
    assert "provider: 'v8'" in config


def test_container_artifacts_exist_and_are_hardened() -> None:
    dockerfile = ROOT_DOCKERFILE.read_text(encoding="utf-8")
    assert "requirements.lock.txt" in dockerfile
    assert "USER " in dockerfile, "the image must not run as root"
    assert "HEALTHCHECK" in dockerfile
    assert DOCKERIGNORE.is_file(), "the build context needs a .dockerignore"


def test_devcontainer_bootstraps_the_whole_repository() -> None:
    config = json.loads(DEVCONTAINER.read_text(encoding="utf-8"))
    assert "postCreateCommand" in config
    assert {3000, 8000} <= set(config["forwardPorts"])
    assert (REPO_ROOT / ".devcontainer" / "post-create.sh").is_file()


def test_secret_scanning_is_wired_into_ci_and_the_suite() -> None:
    assert SECRET_SCANNER.is_file()
    assert SECRET_SCANNER_TESTS.is_file()
    assert "scan_secrets.py" in ci_workflow()
