# Notion Import Workspace

This folder is structured like a Notion workspace export/import kit. Use the
files in `pages/` as Notion pages, and import the CSV files in `databases/` as
Notion databases.

## Import Order

1. Create a new Notion workspace page named `LeadGen AI`.
2. Add [Dashboard](pages/dashboard.md) as the main page content.
3. Import each CSV from `databases/` as a database.
4. Add the remaining pages from `pages/` under the dashboard.
5. Keep the original planning docs below as detailed reference pages.

## Notion Pages

- [Dashboard](pages/dashboard.md)
- [Product Requirements](pages/product-requirements.md)
- [Engineering Plan](pages/engineering-plan.md)
- [Design Handoff](pages/design-handoff.md)

## Notion Databases

- [Objectives](databases/objectives.csv)
- [Delivery Tasks](databases/tasks.csv)
- [Risk Register](databases/risks.csv)
- [Launch Checklist](databases/launch-checklist.csv)

## Reference Pages

- [Project Plan](project-plan.md): objectives, scope, targets, milestones, definition of done.
- [Measurement Plan](measurement-plan.md): success metrics, quality gates, instrumentation.
- [Roadmap](roadmap.md): phased delivery plan.
- [Risk Register](risk-register.md): product, security, delivery, and operational risks.
- [Launch Checklist](launch-checklist.md): final acceptance checklist.

## Workspace Views To Create In Notion

- Objectives by status.
- Tasks by owner.
- Risks by impact.
- Launch checklist grouped by area.
- Evidence board linked to `records/`.
