# Launch Checklist

## Product

- [ ] Landing page loads.
- [ ] Hero animation is smooth.
- [ ] Login works.
- [ ] Dashboard loads after auth.
- [ ] Generate leads works with configured providers.
- [ ] Leads Hub search works.
- [ ] Verify single email works.
- [ ] Verify batch emails works.
- [ ] File upload verification enforces size limits.
- [ ] CSV export downloads.
- [ ] Deliverability checker returns score and recommendations.

## Security

- [ ] `DEBUG=False`.
- [ ] `SECRET_KEY` configured.
- [ ] `ALLOWED_HOSTS` restricted.
- [ ] `CORS_ALLOWED_ORIGINS` exact.
- [ ] HTTPS enabled.
- [ ] Secure cookies enabled.
- [ ] Redis not exposed publicly.
- [ ] PostgreSQL not exposed publicly.
- [ ] No `.env`, logs, credentials, or bytecode committed.

## Engineering

- [ ] Backend tests pass.
- [ ] Frontend tests pass.
- [ ] Backend lint passes.
- [ ] Frontend lint passes.
- [ ] Frontend build passes.
- [ ] Docker Compose config validates.
- [ ] CI workflows pass.

## Documentation

- [ ] README is current.
- [ ] Developer onboarding is current.
- [ ] Security docs are current.
- [ ] Figma specs are current.
- [ ] Records/evidence are current.
