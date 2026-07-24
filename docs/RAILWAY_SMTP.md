# Railway SMTP configuration

Set these variables on the **Railway** backend service (Variables tab):

| Variable | Example | Required |
|----------|---------|----------|
| `SMTP_HOST` | `smtp.gmail.com` | Yes (or use `RESEND_API_KEY`) |
| `SMTP_PORT` | `587` | Yes for SMTP |
| `SMTP_USERNAME` | `noreply@yourdomain.com` | Yes for SMTP auth |
| `SMTP_PASSWORD` | app password | Yes for SMTP auth |
| `SENDER_EMAIL` | `noreply@yourdomain.com` | Yes |
| `FRONTEND_URL` | `https://plateforme-sante-guinee.vercel.app` | Yes (reset/verify links) |

Legacy aliases also supported: `SMTP_SERVER`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`.

> **Migration note:** Production must not keep `FRONTEND_URL=https://frontend-seven-rust-94.vercel.app`.  
> The backend remaps that legacy host at runtime, but the Railway variable itself should be updated to the canonical URL (see `docs/ZERO_LEGACY_ACCESS_BLOCKERS.md`).  
> If GitHub Actions secrets `RAILWAY_TOKEN` + `RAILWAY_SERVICE_ID` are set, the deploy workflow enforces the canonical `FRONTEND_URL` automatically.

## Alternative: Resend

| Variable | Value |
|----------|--------|
| `RESEND_API_KEY` | `re_...` |
| `SENDER_EMAIL` | verified domain sender |

## Verify deployment

```bash
curl https://web-production-ad6a36.up.railway.app/health/email
curl https://web-production-ad6a36.up.railway.app/auth/email-status
```

Both should show `"configured": true`.

## End-to-end inbox test

1. POST `/auth/forgot-password` with a real inbox email.
2. Check inbox (and spam) for reset link pointing to `FRONTEND_URL/reset-password?token=...`.
3. Register a new patient/doctor — verification email should arrive with `/verify-email?token=...`.

Run full audit:

```bash
python scripts/deploy/full_production_audit.py
```

Report written to `docs/PRODUCTION_AUDIT_REPORT.md`.
