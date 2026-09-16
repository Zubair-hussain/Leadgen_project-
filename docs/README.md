# Project Documentation

This folder is the operating handbook for the lead generation project.

- `architecture.md`: system architecture, diagrams, tech stack, deployment topology.
- `infrastructure.md`: containers, networking, build vs run-time config, Docker commands.
- `wireframes.md`: wireframes (SVG) for every primary screen.
- `diagrams/`: source SVGs for architecture, infrastructure, and wireframes.
- `onboarding.md`: local setup and developer workflow.
- `security.md`: security model, secrets, JWT auth flow, CORS, deployment guardrails.
- `testing.md`: how tests, linting, coverage, and CI checks are expected to run.
- `operations.md`: runtime services, Celery, Docker, and incident notes.
- `nextjs-migration-plan.md`: record of the Vite → Next.js migration.

Captured proof of the quality gates lives in [`../evidences/`](../evidences/README.md).

## For reviewers

Start with `architecture.md` for the big picture, `wireframes.md` for the UX,
and `security.md` for the authentication model. `testing.md` shows the quality
gates and current coverage baseline.
