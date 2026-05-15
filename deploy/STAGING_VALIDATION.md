# Phase 3 — Staging validation checklist

Run after `deploy/vps/deploy-staging.sh` on the VPS with a real subdomain and HTTPS.

## Automated (on VPS)

```bash
chmod +x deploy/vps/validate-staging.sh scripts/db/*.sh
./deploy/vps/validate-staging.sh
./scripts/db/backup_verify.sh
```

## Manual — connectivity

- [ ] Open `https://staging.YOUR_DOMAIN/` from laptop (Wi‑Fi)
- [ ] Open same URL from phone on **4G/5G** (not Wi‑Fi)
- [ ] Certificate valid (padlock, no mixed content)
- [ ] Login patient + doctor pilot accounts

## Authentication

- [ ] Patient → `/dashboard`
- [ ] Doctor → `/doctor/dashboard`
- [ ] Token persists after browser refresh
- [ ] Logout clears session

## Core flows

- [ ] Book teleconsultation appointment
- [ ] Doctor sees appointment in queue
- [ ] Messaging on `/messages/:appointmentId`
- [ ] Payment flow (Stripe test keys on staging)

## Teleconsultation

- [ ] Join only inside time window (15 min before → grace after)
- [ ] Expired / cancelled appointment → access denied
- [ ] Camera/micro prompt on HTTPS (allow/deny handled gracefully)
- [ ] Jitsi link opens with JWT when `JITSI_APP_SECRET` configured
- [ ] End session → status completed

## Infrastructure

- [ ] `docker compose restart backend` → API recovers &lt; 30s
- [ ] `docker compose restart db` → data still present
- [ ] WebSocket: `wss://DOMAIN/api/ws/health` returns `pong`
- [ ] Backup file created and `gzip -t` passes

## Sign-off

When all items pass, proceed to **Phase 4** (`deploy/vps/deploy-production.sh`).
