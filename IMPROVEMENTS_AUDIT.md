# Improvements.md - Code-Implementation Audit

**Audited:** 2026-09-18
**Source:** `Improvements.md` (the "How to raise your score" section)
**Scope:** only the suggestions that require a change to files in this repository.
Git-history suggestions (*keep developing over time*, *small focused commits*,
*spread commits across days*, *tag a release*, *add a deploy job*) are **out of
scope** per the request - they are process items, not code.

**Method:** every claim below was verified by reading the committed files
(`git ls-files`, `git --no-pager log`, config parsing). No tests or application
were executed, as requested.

**Result:** 8 of the 11 in-scope sub-suggestions are fully implemented and
professionally written. **3 are not met and 2 are partial deviations** - listed
in section 2. Nothing here blocks a commit; items 1-5 of section 4 are the ones
worth fixing before the next scoring pass.

---

## 1. What was checked and passes

| # | Suggestion (Improvements.md) | Status | Evidence |
|---|---|---|---|
| 1 | Commit `backend/requirements.txt` + `requirements-dev.txt` at the paths CI installs from | PASS | Both tracked (`git ls-files`); `.github/workflows/ci.yml:91` runs `pip install -r requirements.txt -r requirements-dev.txt` |
| 2 | Pin exact versions in both files | PASS | Every line is `name==version`; enforced by `backend/tests/test_dependency_manifests.py:71-86` (rejects `~=`, `>=`, `<=`, `*`) |
| 3 | Add a backend lockfile for reproducible installs | PARTIAL | `backend/requirements.lock.txt` + generator exist, and a CI job proves a fresh clone installs from it - see **Gap 4** for the naming/tooling caveat |
| 4 | Remove the hardcoded `DEFAULT_PASSWORD = 'secret123'` literal | PASS | `backend/tests/factories.py:22-37` now reads `TEST_DEFAULT_PASSWORD` or generates `secrets.token_urlsafe(16)` |
| 5 | Comment that `PGPASSWORD` is only read from `DB_PASSWORD`, never defaulted | PASS | All three scripts carry the SECURITY comment plus `: "${DB_PASSWORD:? ...}"` (abort-if-unset): `scripts/backup-db.sh`, `scripts/db-maintenance.sh`, `scripts/restore-db.sh` |
| 6 | `[tool.coverage.report] fail_under = 80` in the backend config | PASS | `backend/pyproject.toml:77-78`, mirrored in root `pyproject.toml:44-45` |
| 7 | `--cov-fail-under=80` on the CI test command | PASS | `.github/workflows/ci.yml:94`; asserted by `backend/tests/test_quality_gates.py:40-67` |
| 8 | Frontend coverage thresholds + run the coverage command in CI | PARTIAL | `frontend/vitest.config.ts:33-42` defines `thresholds`; `ci.yml:154` runs `npm run test:coverage` - see **Gap 3** (floors below the suggested 70/70) |
| 9 | JSON formatter in `logging_config.py`, gated by `JSON_LOGS` | PARTIAL | `python-json-logger` JSON handler and `settings.json_logs` wiring in `app/main.py:39` work - but the module's comments contradict its code, see **Gap 2** |
| 10 | Pin `python-json-logger` in `backend/requirements.txt` | PASS | `python-json-logger==4.2.0` (requirements.txt:46), also in the lockfile (line 66) |
| 11 | `backend/tests/test_logging_config.py` asserting a JSON-parseable line | PASS | 7 tests incl. `test_json_output_is_parseable` (parametrized), text fallback, single-handler reload, `app` correlation field |

Supporting artefacts referenced by the same suggestions are correct too: no
committed `.env` file anywhere, the root `Dockerfile` installs from
`backend/requirements.lock.txt`, `.devcontainer/` exists, and `git tag` shows
`v0.1.0` on CI-green `main`.

---

## 2. Gaps - suggestions not met, or met only partially

### Gap 1 (medium) - Literal credentials still remain in test fixtures

**Suggestion:** *"Run `grep -rn PASSWORD backend/tests scripts` to confirm no
remaining literal credential strings before next commit."*

The flagged `factories.py` literal is gone, but two fixtures still hand-write the
same value:

| File | Line | Code |
|---|---|---|
| `backend/tests/test_employees_rbac.py` | 81 | `"password": "secret123",` |
| `frontend/tests/services.test.ts` | 19 | `await authService.register({ ... password: 'secret123' });` |
| `frontend/tests/services.test.ts` | 23, 26 | `authService.login('owner@shop.com', 'secret123')` and `password: 'secret123',` |

**Why it matters:** this is the exact pattern `Improvements.md` called out. The
suggestion asks for *no remaining literal credential strings*, and `secret123` is
the same literal the scanner reported. It also proves the repo's own gate cannot
catch it: `backend/scripts/scan_secrets.py:142` only treats a value as
secret-shaped when it is **at least 12 characters**
(`_SECRET_SHAPED_VALUE = ^[A-Za-z0-9_\-./+=:@!]{12,}$`), and `secret123` is 9 - so
`test_the_repository_contains_no_credential_literals` passes while the literal
ships.

**Fix:**
1. In `test_employees_rbac.py`, pass `factories.DEFAULT_PASSWORD` instead of
   `"secret123"` (the `factories` import already exists in that file).
2. In `frontend/tests/services.test.ts`, export a `TEST_PASSWORD` constant from
   `frontend/tests/setup.ts` (or a new `tests/helpers.ts`) and use it at all three
   call sites, so the literal lives in one clearly non-secret place.
3. Optional but recommended: lower `_SECRET_SHAPED_VALUE` to `{8,}` in
   `scan_secrets.py` (8 is already the production password-policy floor) so the
   gate covers this class of value, and add a case to `test_secret_scan.py`.

---

### Gap 2 (low) - `logging_config.py` comments describe a guard that does not exist

**Suggestion:** *"configure Python's logging with a JSON formatter (e.g. via
python-json-logger) gated by the existing JSON_LOGS env var"* - the behaviour is
correct, but the file is not internally consistent.

In `backend/app/core/logging_config.py`:

- Lines 24-27 claim *"The guard below keeps imports cheap and avoids a hard
  `ImportError` if a downstream project strips extras"* - but line 28 is an
  **unconditional** `import pythonjsonlogger.jsonlogger as _jsonlogger`, and line
  30 hardcodes `_HAS_JSON = True`. There is no guard.
- Because `_HAS_JSON` is a constant `True`, the branch at line 63
  (`if json_format and _HAS_JSON:`) is dead; the text fallback is reachable only
  through the `json_format` argument.
- The docstring at lines 45-52 says *"If True **and python-json-logger is
  installed**"* and *"Falls back to **coloured** text otherwise"* - the fallback is
  plain text (line 67); the module contains no colour handling.
- `backend/tests/test_logging_config.py:37-39` still defines a
  `requires_json_logger` skipif marker driven by `_HAS_JSON`, i.e. written for the
  try/except version that was later removed. `test_python_json_logger_is_available`
  asserts a constant is `True` and can never fail.

**Fix (either option is fine - pick one and make the module and its test agree):**
- Restore the intended guard -
  `try: import pythonjsonlogger.jsonlogger as _jsonlogger; _HAS_JSON = True`
  `except ImportError: _jsonlogger = None; _HAS_JSON = False` (keeping the
  `type: ignore` on the import), **or**
- Delete the "guard" comment, drop `_HAS_JSON` / `requires_json_logger`, and
  correct "coloured" to "plain" in the docstring.

---

### Gap 3 (medium) - Frontend coverage floors are below the suggested gate

**Suggestion:** *"Add an equivalent `frontend/vitest.config.ts`
`coverage.thresholds` block (**lines: 70, functions: 70**)..."*

`frontend/vitest.config.ts:38-41` sets:

```ts
lines: 45,
functions: 40,
branches: 70,
statements: 45,
```

The mechanism is present (thresholds plus `npm run test:coverage` in CI), so
`coverage_threshold` in the scoring stats will no longer be `null` - but the
specific floors asked for are not met, and the gate would still pass if line
coverage fell from today's ~47.6% to 45%. `branches: 70` is the only value at or
above the suggested level.

**Fix:** raise `lines` and `functions` to `70` and add the tests needed to clear
them (the untested modules under `lib/`, `hooks/`, `services/`, `components/` are
the obvious targets). If 70 is unreachable in one pass, raise it in steps (60 ->
70); the committed config should converge on the suggested numbers because an
automated scorer reads the numbers, not the rationale comment at
`vitest.config.ts:34-37`.

---

### Gap 4 (medium) - Lockfile naming and tooling differ from the suggestion

**Suggestion:** *"Add a `backend/requirements.lock` or use pip-tools to generate
`backend/requirements.txt` from `backend/requirements.in`."*

Delivered instead: `backend/requirements.lock.txt`, produced by a hand-written
`backend/scripts/generate_lockfile.py` that shells out to
`pip install --dry-run --report` and rewrites the resolved closure.

Two concrete concerns:

1. **Filename.** The suggestion names `backend/requirements.lock`, and
   `Improvements.md` itself reports *"only `frontend/package-lock.json` found in
   `lockfiles_found`"*. The file is valid pip syntax, but lockfile detectors
   commonly match `requirements.lock`, `*.lock`, `poetry.lock` or `Pipfile.lock`;
   the extra `.txt` extension risks the same "no backend lockfile captured"
   finding recurring on the next score.
2. **Tooling.** `pip-tools` is not in `backend/requirements-dev.txt`, so the
   documented regeneration path is bespoke rather than the conventional one, and
   `backend/requirements-dev.txt` still pins only *direct* dev tooling, so the dev
   dependency closure is not locked at all.

**Fix (small, keeps everything already built):**
- Produce a canonical `backend/requirements.lock` via `pip-compile` (or from the
  existing closure) and keep `requirements.lock.txt` only if you want to.
- Add `pip-tools==<pin>` to `backend/requirements-dev.txt`.
- Optionally add `backend/requirements-dev.lock` so the CI test environment is
  reproducible as well as the runtime.
- Update `backend/tests/test_dependency_manifests.py:25` and
  `backend/tests/test_quality_gates.py:70` to the chosen filename so the tests
  keep guarding the real file.

---

### Gap 5 (low/medium) - The compose image does not install from the lockfile

**Suggestion:** *"Commit a lockfile for every package manager so installs are
reproducible."*

`backend/Dockerfile:11-12` does:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
```

Only the **root** `Dockerfile:28-32` uses `requirements.lock.txt`. Every compose
file (`docker-compose.yml:22`, `docker-compose.dev.yml:23-25`,
`docker-compose.prod.yml:24-26`) builds from `./backend`, so the image that
actually runs in dev/staging/production resolves transitive dependencies from the
network at build time - the exact reproducibility the lockfile was added to
guarantee.

There is a matching hole in the guard: `backend/tests/test_quality_gates.py:115-119`
asserts `"requirements.lock.txt" in dockerfile` only for the **root** Dockerfile,
so a regression in `backend/Dockerfile` would not fail the suite.

**Fix:**
1. `backend/Dockerfile` -> `COPY requirements.txt requirements.lock.txt ./` and
   `pip install --no-cache-dir --prefix=/install -r requirements.lock.txt`.
2. Extend `test_container_artifacts_exist_and_are_hardened` to read
   `backend/Dockerfile` as well and assert it installs from the lockfile.

---

### Gap 6 (low) - Documentation still shows the un-gated test command

**Suggestion:** *"Make the test command explicit in the README and CI."*

README, CONTRIBUTING and CI are all correct and explicit
(`README.md:26-43,215,228`; `CONTRIBUTING.md:77,86`; `ci.yml:94,154`). Three
secondary files were not updated with the enforced flag and now disagree with the
primary docs:

| File | Line | Shows | Should show |
|---|---|---|---|
| `.github/PULL_REQUEST_TEMPLATE.md` | 30 | `pytest --cov=app --cov-report=term-missing` | add `--cov-fail-under=80` |
| `backend/README.md` | 20 | `pytest --cov=app --cov-report=term-missing` | add `--cov-fail-under=80` |
| `backend/tests/README.md` | 8 | `pytest --cov=app --cov-report=term-missing` | add `--cov-fail-under=80` |

The PR template's verification block also omits `npm run test:coverage`, even
though `CONTRIBUTING.md:129` requires it.

---

## 3. Informational (no action strictly required)

- **No separate deploy job.** `ci.yml` has a tag-triggered `release` job that
  publishes to GHCR and opens a GitHub Release instead. That is a deliberate,
  documented choice (`ci.yml:8-9`, `docs/operations/runbook.md`), but a scorer
  looking for a deploy job will still record "no separate deploy job". A
  manual-approval `deploy` job (or a `deploy` environment on `release`) would
  address the signal without changing the process.
- **Test-only password-looking strings remain** in `backend/tests/test_auth.py`
  (`"whatever1"`, `"wrong-password"`, `"brand-new-pass"`) and two are already
  allowlisted (`FIRST_RESET_PASSWORD`, `SECOND_RESET_PASSWORD`). All are
  intentionally non-secret, but the inconsistency (some allowlisted, some not) is
  worth normalising while fixing Gap 1.
- `backend/scripts/scan_secrets.py` is a solid, well-documented gate; its only
  weakness is the 12-character floor described in Gap 1.

---

## 4. Priority order

| Priority | Item | Effort |
|---|---|---|
| 1 | Gap 3 - raise frontend coverage floors to the suggested 70/70 (needs new tests) | medium |
| 2 | Gap 1 - remove the remaining `secret123` literals | small |
| 3 | Gap 4 - add a canonical `backend/*.lock` + `pip-tools` pin | small |
| 4 | Gap 5 - make `backend/Dockerfile` install from the lockfile | small |
| 5 | Gap 2 - align `logging_config.py` comments with its code | small |
| 6 | Gap 6 - sync the three secondary docs | trivial |
| 7 | Informational items | optional |