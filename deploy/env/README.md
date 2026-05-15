# Backend environment files

| File | Committed? | Purpose |
|------|------------|---------|
| `.env.backend.example` | Yes | Template — copy to `.env.backend` on server |
| `.env.backend` | **No** (gitignored) | Real secrets on VPS |

```bash
cp deploy/env/.env.backend.example deploy/env/.env.backend
# Edit SECRET_KEY, Stripe, Jitsi, SMTP on the server only
```
