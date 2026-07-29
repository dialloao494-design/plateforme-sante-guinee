# Wave 7 — Pre-Deploy Ops Attestation Checklist

Sign before production traffic. Complements `evidence/security/PRODUCTION_SECURITY_READINESS_REPORT.md`.

| # | Attestation | Owner | Date | Initials |
|---|-------------|-------|------|----------|
| 1 | Railway Postgres private (no public TCP) | | | |
| 2 | `DATABASE_URL` TLS (`sslmode` ≠ disable) | | | |
| 3 | Vercel previews do not use production `VITE_API_URL` | | | |
| 4 | Unique strong secrets set (JWT, attachment, backup, update, license, reminder) | | | |
| 5 | GitHub `main` protected + required reviews | | | |
| 6 | Sentry configured; `/health/ready` monitored | | | |
| 7 | (Per Clinic Node) LUKS verified | | | |
| 8 | (Per Clinic Node) Firewall + HTTPS trust + encrypted backup drill | | | |

**Certification verdict referenced:** GO FOR PRODUCTION SECURITY DEPLOYMENT (Wave 7)
