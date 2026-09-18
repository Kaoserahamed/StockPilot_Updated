## What does this change?

<!-- One or two sentences. Reference the milestone item, e.g. M4.5. -->

## Why?

<!-- The problem or requirement this addresses. -->

## Milestone / requirement reference

- Refers to an `IMPLEMENTATION_PLAN.md` item: `M__.`
- Refers to a functional requirement where applicable: `FR-__`

## Type of change

- [ ] `feat` - new behaviour
- [ ] `fix` - bug fix
- [ ] `test` - tests only
- [ ] `ci` - pipeline / tooling
- [ ] `docs` - documentation
- [ ] `refactor` - no behaviour change
- [ ] `chore` - maintenance

## Verification (paste the real output)

```text
ruff check app tests
ruff format --check app tests
mypy app
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

npm run lint
npm run typecheck
npm run test:coverage
npm run format:check
npm run build
```

## Checklist

- [ ] New or changed behaviour ships with a test that fails without this change
- [ ] One logical change - no unrelated formatting or refactoring bundled in
- [ ] No secrets, `.env` files, databases or build artifacts committed
- [ ] `CHANGELOG.md` updated under `Unreleased`
- [ ] `IMPLEMENTATION_PLAN.md` checkboxes updated
- [ ] Schema change? Migration included, reviewed and reversible

## Screenshots (UI changes only)

<!-- Before / after -->
