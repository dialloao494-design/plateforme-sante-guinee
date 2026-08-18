# Production readiness checklist (Guinea clinic pilot)

Use this list before pointing a real domain and inviting doctors.

## Environment (API)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres in production; SQLite only for local dev. |
| `CORS_ORIGINS` | Comma-separated extra origins (HTTPS). |
| `FRONTEND_URL` | Canonical public UI URL used for CORS and generated links. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Card payments + webhook verification. |
| `ORANGE_MONEY_LIVE`, `ORANGE_MONEY_MERCHANT_ID`, `ORANGE_MONEY_API_KEY` | Enable live Orange Money path (see `services/mobile_money_service.py`). |
| `MTN_MOMO_LIVE`, `MTN_MOMO_SUBSCRIPTION_KEY`, `MTN_MOMO_API_USER`, `MTN_MOMO_API_KEY` | Enable live MTN MoMo path. |
| `SMS_PROVIDER_URL` or `TWILIO_ACCOUNT_SID` | Marks SMS channel as live in `/notifications/channels`. |
| `SMTP_HOST` or `RESEND_API_KEY` | Marks email channel as live. |
| `VAPID_PUBLIC_KEY` / `WEB_PUSH_PUBLIC_KEY` | Marks Web Push as live. |
| `DEBUG` | Must be `false` in production. |

## HTTP surface

- **Liveness:** `GET /health`
- **Readiness (DB):** `GET /health/ready` — use for Kubernetes / Railway health checks.
- **Payments rails:** `GET /payments/rail-config` — documents Stripe vs Mobile Money status.
- **Mobile Money stub:** `POST /payments/mobile-money/initiate` — returns a reference until operator webhooks confirm.

## Frontend (Vite)

- Set `VITE_API_URL` to the HTTPS API base (never localhost in production builds).
- Optional: `VITE_ENABLE_PAYMENT_SIMULATION=true` only for internal demos.

## Data & privacy

- Demo doctor seed runs on every startup; replace with real directory data before public launch or disable seed in code.
- `notification_events` stores in-app history per user; align retention with your legal policy.

## Smoke tests before go-live

1. Patient: register / login → annuaire with geolocation → prendre RDV (`?doctor_id=`) → paiement → notification in **Notifications**.
2. Doctor: login → fiche publique → **Enregistrer la position du cabinet** → patient nearby list shows distance.
3. Admin: `GET /health/ready` returns 200.
