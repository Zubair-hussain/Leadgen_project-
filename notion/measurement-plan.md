# Measurement Plan

## North Star

Verified leads generated per authenticated user session.

## Success Metrics

| Area | Metric | Target |
| --- | --- | --- |
| Auth | Unauthenticated access to protected endpoints | 0 allowed |
| Data isolation | Cross-user lead leakage | 0 incidents |
| Lead generation | Successful generation request | 95%+ when providers configured |
| Verification | Single email verification response | < 3 seconds typical |
| Export | CSV export memory profile | Streaming response |
| Landing page | Hero animation visible in README and page | Yes |
| CI | Required checks configured | Backend + frontend + hygiene |
| Coverage | App-layer coverage target | 80% |

## Quality Gates

Backend:

```bash
python -m compileall -q .
pytest
pylint leadgen leads
python manage.py check --deploy
```

Frontend:

```bash
npm run lint
npm test
npm run build
```

## Instrumentation To Add Later

- Request latency by endpoint.
- Lead provider success/failure counts.
- Celery job duration and failure reason.
- Export count and duration.
- Verification pass/fail count by domain.
- Frontend route-level errors.

## Evidence

Store verification notes in `records/`.
