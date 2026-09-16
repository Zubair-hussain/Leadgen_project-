# Project Plan

## Objective

Build a credible, production-ready lead generation product that lets an
authenticated user generate, verify, manage, and export owner-scoped leads while
presenting a refined portfolio-quality landing page.

## Measurement Objective

The project is successful when:

- Users can sign in and only access their own leads.
- Lead generation, verification, export, and deliverability checks work end to end.
- The landing page communicates the product clearly and includes the smooth
  `meeting -> booking -> closing -> winning -> signing` animation.
- Backend and frontend quality gates run in CI.
- Security risks identified in the audit are remediated or recorded.

## Scope

In scope:

- Static landing page in `leadgen.html`.
- Frontend application in `leadgen-frontend/`.
- Django API in `backend/`.
- PostgreSQL, Redis, Celery, Docker Compose.
- Firebase-authenticated API requests.
- Documentation, records, design specs, CI, linting, and tests.

Out of scope for this phase:

- Paid billing integration.
- Production deployment secrets.
- CRM integrations beyond export-ready CSV.
- Full visual Figma file generation unless executed through Figma tooling later.

## Target Users

- Freelancers and agencies doing B2B outreach.
- Small sales teams looking for niche/location lead discovery.
- Portfolio reviewers evaluating the project quality.
- Internal developers maintaining the app.

## Business Targets

- Make the project demo-ready for portfolio and client review.
- Reduce security and operational risk before public exposure.
- Keep onboarding clear enough that a new developer can run the project locally.

## Product Targets

- Lead generation supports Reddit, X, Google Maps, and optional Apify mode.
- Verification supports single, batch, file upload, and database audit workflows.
- Deliverability checker provides SPF, DMARC, DKIM, TLS, copy, and unsubscribe guidance.
- Leads Hub supports search, verify, delete, and streamed CSV export.

## Quality Targets

- Backend test coverage target: 80% for app/controller/security layers.
- Frontend test coverage target: 80% where practical.
- CI runs compile, lint, test, coverage, build, and hygiene checks.
- No secrets, logs, bytecode, or local environment files committed.

## Milestones

| Milestone | Outcome |
| --- | --- |
| M1 Security Baseline | Authenticated API, owner-scoped leads, hardened settings |
| M2 Quality Baseline | Tests, coverage config, lint config, CI workflows |
| M3 Product Polish | Landing animation, README, docs, design specs |
| M4 Launch Readiness | Evidence records, risk register, final checklist |

## Definition Of Done

The project is done when:

- Security defaults are closed by default.
- Public health endpoint exposes minimal data.
- Lead data is owner-scoped.
- Export streams CSV safely.
- File upload has size limits.
- SSRF protections exist for crawler fetches.
- Celery path exists for production lead generation.
- README, docs, Notion, Figma, and records folders are present.
- CI workflows are committed.
- Tests and lint commands are documented with current known local constraints.

## Open Decisions

- Final production domain and canonical URLs.
- Firebase project and service account provisioning.
- Whether Apify remains optional or becomes a paid/pro mode.
- Whether the current app should stay React/Vite or finish migration to Next.js.
