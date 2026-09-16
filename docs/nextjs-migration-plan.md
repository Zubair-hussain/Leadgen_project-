# Frontend Migration: Vite SPA → Next.js

Status: **Done.** The frontend now runs on Next.js 15 (App Router) + React 19,
built as a static export, with the test/lint/coverage/build gates green. This
document records the plan and what was delivered.

## What shipped

- Next.js 15 App Router under `src/app/` (`/`, `/login`, `/dashboard`), with a
  client-side `AuthGate` guard and an `AppChrome` shell (toasts + connection
  status) in the root layout.
- Screens moved to `src/views/` (the `src/pages/` name is reserved by Next's
  Pages Router).
- Env migrated `VITE_*` → `NEXT_PUBLIC_*`; Firebase init guarded to the browser
  so static prerender/export succeeds without build-time secrets.
- Vitest retained via `vitest.config.js` (jsdom + istanbul); 87 tests, coverage
  above the 80/70/80/80 thresholds. New tests cover `useAuthUser` and `AuthGate`.
- ESLint flat config updated (dropped the Vite refresh preset, ignores `.next`/
  `out`). Docker builds the static export and nginx serves it.

## Goals

- Next.js (latest) with the **App Router** and React 19.
- Keep the existing Firebase → Django SimpleJWT auth flow intact.
- Preserve (and where possible raise) the current coverage/lint gates.
- No backend API changes required — the Django API stays the contract.

## Non-goals (for the migration PR)

- Redesigning UI or changing product behavior.
- Server-side rendering of authenticated data (auth is client-token based).
  Start with client components; adopt SSR/RSC incrementally afterward.

## Target structure

```
leadgen-frontend/
  app/
    layout.jsx            # root layout, providers, Tailwind
    page.jsx              # "/" -> redirect to /login or /dashboard
    login/page.jsx        # Login (client component)
    dashboard/page.jsx    # Dashboard shell (client component)
  components/             # ported as-is (features/, layout/, ui/)
  lib/
    api.js                # axios client + JWT interceptors (ported)
    firebase.js           # Firebase init (client-only)
  __tests__/ or *.test.jsx
```

## Phased steps

1. **Scaffold** Next.js alongside the SPA; move Tailwind/PostCSS config over.
2. **Env**: replace `import.meta.env.VITE_API_URL` with
   `process.env.NEXT_PUBLIC_API_URL`; add `.env.example`.
3. **Auth boundary**: mark `firebase.js` and `api.js` as client (`"use client"`),
   keep token storage in the browser. Verify the exchange + refresh flow.
4. **Routing**: convert the tab-state shell into `/dashboard`; add a client-side
   auth guard that redirects unauthenticated users to `/login`.
5. **Port components** with minimal edits (they are already presentational).
6. **Testing**: keep Vitest (works with Next via `@vitejs/plugin-react`) or move
   to the Next test setup; re-establish the 80/70/80/80 coverage thresholds.
7. **Lint**: adopt `eslint-config-next` on top of the current flat config.
8. **Build/CI**: swap the frontend CI job to `next build`; keep lint + test +
   coverage steps.
9. **Dockerfile/nginx**: replace the static nginx serve with the Next runtime
   (or `next export` if fully static) and update `docker-compose.yml`.

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| `import.meta.env` usages break | Grep and replace with `process.env.NEXT_PUBLIC_*` before first build. |
| Firebase/browser-only APIs in RSC | Keep auth + api modules client-only. |
| Coverage tooling differences | Pin Vitest + istanbul first; migrate config, not tests. |
| Hydration mismatches (Framer Motion) | Render animated shells in client components. |

## Definition of done

- `next build` succeeds; app runs at parity with the SPA.
- Login → JWT exchange → owner-scoped API calls work end-to-end.
- Lint clean; coverage meets the existing thresholds.
- CI updated; Docker image serves the Next app.
