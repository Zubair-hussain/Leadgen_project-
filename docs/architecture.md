# System Architecture

LeadGen AI is a two-tier web application: a Next.js frontend and a Django REST
API, backed by PostgreSQL, Redis, and a Celery worker, with third-party data and
auth providers. This document is the reviewer-facing overview of how the pieces
fit together.

![System architecture](diagrams/architecture.svg)

## 1. Context diagram

```mermaid
flowchart LR
    user([Sales user])

    subgraph client[Client]
      spa[Next.js App Router<br/>React 19 static export]
    end

    subgraph platform[LeadGen Platform]
      api[Django REST API]
      worker[Celery worker]
      db[(PostgreSQL)]
      cache[(Redis<br/>broker + cache)]
    end

    subgraph external[External providers]
      fb[Firebase Auth]
      serp[SerpAPI]
      apify[Apify]
      smtp[SMTP / Gmail]
      dns[DNS / MX]
    end

    user --> spa
    spa -->|HTTPS JSON<br/>Bearer JWT| api
    spa -->|Google sign-in| fb
    api -->|verify ID token| fb
    api --> db
    api --> cache
    worker --> db
    worker --> cache
    api -. enqueue .-> worker
    worker --> serp
    worker --> apify
    api --> dns
    api --> smtp
```

## 2. Container / component view

```mermaid
flowchart TB
    subgraph FE[Frontend - leadgen-frontend/src]
      route[app/ routes + AuthGate guard]
      login[views/Login]
      dash[views/Dashboard shell]
      route --> login & dash
      gen[Generator panel]
      leads[Leads Hub table]
      ver[Verifier panel]
      sender[Sender / Deliverability panel]
      apiClient[api.js<br/>axios + JWT interceptors]
      login --> apiClient
      dash --> gen & leads & ver & sender
      gen & leads & ver & sender --> apiClient
    end

    subgraph BE[Backend - backend/leads]
      urls[urls.py routes]
      auth[authentication.py<br/>Fallthrough JWT + Firebase]
      views[views.py<br/>APIViews]
      services[services.py<br/>LeadGenerator, EmailVerifier,<br/>DeliverabilityPolicyChecker]
      models[models.py<br/>Lead]
      tasks[tasks.py<br/>Celery]
      urls --> auth --> views
      views --> services
      views --> models
      views -. async .-> tasks
    end

    apiClient -->|/api/*| urls
```

## 3. Request lifecycle (lead generation)

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as GenerateLeadsView
    participant SVC as LeadGenerator
    participant EXT as SerpAPI / Apify
    participant DB as PostgreSQL

    FE->>API: POST /api/generate/ (Bearer JWT)
    API->>API: throttle + validate payload
    alt Synchronous (LEADGEN_SYNC_REQUESTS)
        API->>SVC: generate_leads(...)
        SVC->>EXT: query sources
        EXT-->>SVC: raw candidates
        SVC->>DB: get_or_create (dedup by owner+email)
        SVC-->>API: normalized leads
        API-->>FE: 200 { leads, csv_base64 }
    else Asynchronous (Celery)
        API->>API: generate_leads_task.delay(...)
        API-->>FE: 202 { task_id }
    end
```

## 4. Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15 (App Router, static export), React 19, Tailwind CSS, Framer Motion, Axios |
| Auth | Firebase Google sign-in + Django SimpleJWT |
| API | Django 5.2, Django REST Framework 3.16 |
| Async | Celery + Redis broker, `django-celery-beat` |
| Data | PostgreSQL (prod), SQLite (tests) |
| Providers | SerpAPI, Apify, DNS/MX, SMTP (Gmail) |
| Quality | pytest + coverage, pylint, Vitest + istanbul, ESLint |
| CI/CD | GitHub Actions (CI + repository hygiene) |
| Runtime | Docker Compose (api, worker, db, redis, frontend) |

## 5. Deployment topology

![Infrastructure and deployment](diagrams/infrastructure.svg)

```mermaid
flowchart LR
    lb[HTTPS reverse proxy] --> fec[frontend container<br/>nginx static]
    lb --> apic[api container<br/>gunicorn]
    apic --> dbc[(postgres)]
    apic --> rc[(redis)]
    wc[worker container<br/>celery] --> dbc
    wc --> rc
    apic -. tasks .-> rc
```

- `db` and `redis` are **not** published to the host by default.
- The frontend is built to static assets and served by nginx (`nginx.conf`).
- The API runs behind an HTTPS-terminating proxy; secure cookies + HSTS apply.

## 6. Key architectural decisions

- **Owner-scoped data model.** Every `Lead` has an `owner`; all reads/writes
  filter by the authenticated user, preventing cross-tenant access.
- **Dual bearer auth.** A tolerant JWT authenticator defers to Firebase instead
  of failing, so one `Authorization` header supports both schemes during the
  Firebase→JWT transition. See [security.md](security.md).
- **Sync/async toggle.** `LEADGEN_SYNC_REQUESTS` lets long provider calls run in
  Celery in production while staying synchronous in tests/local dev.
- **Streamed CSV export.** Exports stream row-by-row rather than buffering the
  whole file in memory.

See also: [wireframes.md](wireframes.md), [nextjs-migration-plan.md](nextjs-migration-plan.md).
