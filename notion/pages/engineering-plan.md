# Engineering Plan

## Objective

Keep the codebase secure, testable, observable, and easy for a developer to run locally.

## Workstreams

| Workstream | Target | Evidence |
| --- | --- | --- |
| Security | Authenticated private API and no tracked secrets | `records/security-audit.md` |
| Backend Quality | pytest coverage near 80% | `backend/leads/tests/` |
| Frontend Quality | Vitest and ESLint coverage near 80% | `leadgen-frontend/src/` |
| CI | Non-deploy workflows for checks | `.github/workflows/` |
| Onboarding | Developer setup and architecture docs | `docs/developer-onboarding.md` |

## Definition of Done

- Dependencies install cleanly in supported runtimes.
- `pytest` passes locally and in CI.
- Frontend tests and lint pass locally and in CI.
- No credentials, caches, logs, or dumps are tracked.
- README links to docs, records, Notion, and Figma folders.
