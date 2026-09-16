

Skip to content
Using Gmail with screen readers
1 of 1,285
StockPilot scored 42.2. Here's what gets it to offer territory
Inbox

DataFactor <noreply@datafactor.com>
3:31 PM (2 hours ago)
to me

Kaoserahamed/StockPilot
42.2 · 27.8 points from offer territory

Hey, thanks for submitting your code. Kaoserahamed/StockPilot scored 42.2. Repositories above 70 qualify for cash offers, and strong ones earn hundreds to thousands of dollars. Yours isn't there yet, but the gaps are fixable: the three biggest fixes below are worth up to about 27 points combined.

You're 27.8 points from the offer threshold. At 70+, a repository this size would carry a payout estimate of roughly $40 to $110. Estimates are approximate and non-binding: offers come after our review.

We're actively buying right now, and demand windows like this one don't stay open indefinitely. Repositories re-scored within 30 days get priority review.

Volume: 24.7 · Lines of code: 7174

StockPilot is a full-stack FastAPI + Next.js inventory/POS SaaS with reasonably clean, typed backend code (Pydantic schemas, layered routers/services/models, structured logging, health endpoint), but the evidence bundle shows classification as "frontend" despite the codebase being ~72% Python backend with only 1864 LOC TypeScript, so the classification itself looks questionable. Test coverage is thin (6 spec files, 1:19 source ratio) and not run in CI (ci_runs_tests is false); the only CI workflow deploys directly to Azure on push to main with no lint/type/test gates. Dependency and secrets hygiene have gaps (no lockfile for backend/pip, no dep audit, shell scripts with hardcoded "changeme" password fallbacks, no .env.example committed despite README referencing one) and git history is extremely shallow (16 commits by a single author over a few hours).

frontend: 42.2 (D)
Architecture & Robustness	58.0	Backend shows clear layering (api/core/models/schemas/services), Pydantic validation, structured logging via setup_logging and health endpoint present, but frontend/TS layering not evidenced and error tracking is null
Code Cleanliness	55.0	No god files over 500 LOC (median 52 LOC) and readable naming, but has_lint_config is false and linters_and_formatters is empty so nothing is enforced
Docs & Onboarding	55.0	README covers install/run/test/env/architecture (136 LOC, sections present) but env_example_file is null despite README instructing cp .env.example, and no changelog/contributing guide
Test Coverage	15.0	Only 6 test spec files, all backend pytest tests (no frontend tests found); test_source_ratio 1:19, ci_runs_tests is false
Dependency Health	35.0	Only frontend/package-lock.json exists as a lockfile; no backend requirements lockfile, dep_update_tooling is none, 469 transitive deps with no audit
CI/CD Maturity	25.0	CI exists (.github/workflows/azure-deploy.yml) but ci_runs_tests, ci_runs_lint, ci_runs_typecheck are all false; it is a single deploy-on-push pipeline with no PR gating
Security Hygiene	45.0	6 hardcoded-secret-pattern hits are DB_PASSWORD:-changeme fallbacks in shell scripts, no committed .env files, pydantic validation used at API boundaries but no dep_audit_in_ci
History & Maintenance	20.0	git_stats shows only 16 commits, single human author, 0 span_days (all commits within hours), no tags/releases
Where the missing points are
Test Coverage: up to ~10 points
Architecture & Robustness: up to ~9 points
Code Cleanliness: up to ~8 points

Point estimates are approximate and assume each fix is done well.

How to raise your score
Ship features together with their tests, in small focused commits high
Value scales with how much of the history can be mined into self-contained engineering tasks, changes that arrive with the tests proving them. Large mixed commits and test-less changes don't count toward that.
Keep each feature or fix in its own commit (or small PR) that includes the tests pinning the new behavior.
Avoid bulk commits that mix formatting, refactors, and features; they hide the mineable work.
Make install, build, and test work from a fresh clone high
One of the biggest drivers of what buyers pay is whether the project builds and its test suite actually runs, today, on a machine that has never seen it. No runnable suite was detected; adding one changes this repository's value more than any other item on this list.
Clone the repository into an empty directory and follow only the README: every missing step you hit is a step to add.
Commit a lockfile for every package manager so installs are reproducible.
Make the test command explicit in the README and CI, and ensure CI runs it on every push.
Keep developing this repository over time, in real increments medium
Buyers read the commit history as the product: a project built in a short burst, or by a single author, is a thinner mine than one with sustained back-and-forth development. Nothing cosmetic fixes this; only continued real work does.
Keep landing real changes in small commits over the coming weeks; a steady history outweighs a polished snapshot.
If teammates contribute, have them commit under their own identity so the history shows more than one human author.
Grow commit history with paired tests over time high
git_stats shows only 16 commits from a single author compressed into roughly 4.5 hours on one day, which reads as a single burst rather than sustained development; buyers value a track record of small feature+test commits.
Adopt a workflow where each new endpoint or bugfix in backend/app/api/v1/*.py is committed together with its corresponding test in backend/tests/, e.g. one commit per feature.
Split any remaining large feature work into incremental commits (schema change, then service logic, then route, then test) instead of one large commit.
Push these commits across multiple days/sessions to build a visible history of iterative, tested changes rather than a single burst.
Make the test suite runnable from a fresh clone without external services high
Only 6 test spec files exist for 78 Python source files (ratio 1:19) and test_framework is not detected in any manifest, meaning a fresh clone likely cannot run backend/tests/*.py without manual setup of pytest and a test database.
Add backend/requirements-dev.txt or a [tool.pytest.ini_options] section in backend/pyproject.toml pinning pytest, pytest-cov, and httpx.
Update backend/tests/conftest.py to use an in-memory or ephemeral SQLite/test-Postgres fixture so tests need no live external DB connection.
Add a Makefile or backend/README section with the exact command 'pytest --cov=app --cov-report=term-missing' and document the expected pass output.
Run 'pytest' from a clean checkout and confirm all tests pass and exit 0 before merging.
Add a CI job that lints, type-checks, and runs tests on every PR high
The only CI workflow (.github/workflows/azure-deploy.yml) performs Azure deployment on push to main; ci_runs_tests, ci_runs_lint, and ci_runs_typecheck are all false, so nothing gates merges.
Create .github/workflows/ci.yml triggered on pull_request with a job 'backend-test' that runs 'pip install -r backend/requirements.txt', 'ruff check backend/app', and 'pytest backend/tests'.
Add a job 'frontend-check' that runs 'npm ci --prefix frontend', 'npm run lint --prefix frontend', and 'npx tsc --noEmit --project frontend'.
Cache pip and npm dependencies using actions/cache keyed on requirements.txt and package-lock.json hashes.
Confirm the workflow shows green checks on a sample pull request before merging further changes.
Add lockfile and pin backend dependencies medium
lockfiles_found only lists frontend/package-lock.json; the backend has no pinned/locked dependency file, and total_transitive_deps is 469 with dep_update_tooling:none, risking drift and irreproducible installs.
Generate backend/requirements.lock.txt or migrate to backend/pyproject.toml with Poetry/pip-tools, pinning exact versions of fastapi, sqlalchemy, alembic, and pydantic used today.
Add a renovate.json or .github/dependabot.yml at repo root configuring weekly update checks for both pip (backend) and npm (frontend) ecosystems.
Commit the generated lockfile and verify 'pip install -r backend/requirements.lock.txt' installs cleanly on a fresh virtualenv.
Add a complete .env.example and remove hardcoded fallback secrets medium
env_example_file is null despite the app referencing DATABASE_URL, GEMINI_API_KEY, SECRET_KEY and others, and scripts/backup-db.sh and scripts/db-maintenance.sh contain PGPASSWORD default fallbacks ('changeme') per secret_hit_details.
Create backend/.env.example listing DATABASE_URL, SECRET_KEY, CORS_ORIGINS, GEMINI_API_KEY, GEMINI_MODEL with placeholder values and comments.
Create frontend/.env.example listing NEXT_PUBLIC_API_URL with a placeholder value.
Edit scripts/backup-db.sh and scripts/db-maintenance.sh to remove the ':-changeme' default and instead fail fast with an error message if DB_PASSWORD is unset.
Verify 'grep changeme scripts/*.sh' returns no matches after the edit.
Enforce linting and formatting in CI and add config files medium
has_lint_config is false and linters_and_formatters is empty, so code style is currently unenforced across 5180 LOC of Python and 1864 LOC of TypeScript.
Add backend/pyproject.toml with a [tool.ruff] section targeting backend/app and backend/tests.
Add frontend/.eslintrc.json extending next/core-web-vitals and a frontend/.prettierrc for consistent formatting.
Add lint steps to the CI workflow created above ('ruff check backend/app' and 'npm run lint --prefix frontend') so PRs fail on violations.
Your next step: fix the top items above, then re-score the same repository at datafactor.com/score. It takes about a minute and your report updates. The high-priority items above are where most of the missing points live.

Re-score your repository

Have other repositories? Score those too: one read-only token lists everything you own, and offers can cover multiple repositories.

Scoring is free and you can re-score any time. Payout figures are approximate, non-binding estimates, and offers come after our review.

You're receiving this because this repository was submitted for scoring at datafactor.com/score. Reply to this email to talk to us.

