# Risk Register

| Risk | Impact | Likelihood | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Provider API keys missing | Generation returns no leads | Medium | `.env.example`, health checks, docs | Engineering |
| Firebase service account not configured | API auth fails | Medium | Onboarding docs, deployment checklist | Engineering |
| External provider billing abuse | Cost spike | Medium | Auth, throttling, Celery, rate limits | Engineering |
| SSRF via crawler URLs | Security incident | Low/Medium | Private IP/localhost blocking, no unsafe redirects | Engineering |
| Low-quality lead results | Poor user trust | Medium | Verification, AI filter, source labeling | Product |
| Overbroad marketing claims | Trust/legal risk | Medium | Conservative README/UI language | Product |
| CI differs from local machine | Friction | Medium | Document local constraints, use clean CI runners | Engineering |
| Large dependency graph | Slow installs/security surface | Medium | Trim unused dependencies | Engineering |

## Review Cadence

Review this register before each release or whenever a new external integration is added.
