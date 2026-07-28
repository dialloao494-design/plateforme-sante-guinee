# Day 1 Report — Clinic Node Phase 0

**Date:** 2026-07-28  
**Branch:** `cursor/clinic-node-phase0-ab76`  
**Production impact:** none (isolated under `deploy/clinic-node/`)

## Tickets completed

| ID | Status | Evidence |
|----|--------|----------|
| CN-P0-01 Compose stack | Done | `deploy/clinic-node/compose.yml` + `compose.host.yml` |
| CN-P0-02 Env/secrets bootstrap | Done | installer generates `.env` with strong secrets |
| CN-P0-03 `ENVIRONMENT=clinic-node` | Done | `core/settings.py` + unit tests |
| CN-P0-04 Local HTTPS/PKI | Done | `scripts/generate-pki.sh` |
| CN-P0-05 Health via HTTPS | Done | `/health/ready` → `{"status":"ready","database":"ok"}` |
| CN-P0-06 Installer | Done | `install/install.sh` |
| CN-P0-07 Auto-restart | Done | `restart: unless-stopped` + systemd unit |
| CN-P0-08 Reboot-safe harness | Done | `evidence/clinic-node/reboot-safe-*.md` ALL PASSED |
| CN-P0-09 Runbook | Done | `deploy/clinic-node/README.md` |
| CN-P0-10 Tests | Done | 32 unit tests passed |

## Tests executed

1. `pytest tests/test_clinic_node_settings.py tests/test_production_boot_guard.py tests/test_deploy_config.py` → **32 passed**
2. Installer bring-up (host network fallback) → Postgres + FastAPI + SPA + HTTPS proxy
3. Reboot-safe validation → backend kill, full stop/start, db restart → **ALL PASSED**

## Results

- Local PostgreSQL healthy  
- Local FastAPI healthy behind HTTPS  
- SPA served on HTTPS (`HTTP/1.1 200`)  
- Crash recovery validated  

## Remaining bugs / notes

- Docker **bridge** networking is broken in this nested agent VM (veth/forward). Installer supports **`CLINIC_NODE_NETWORK=host`** fallback. Mini-PC production should use default **bridge** `compose.yml`.  
- Phase 1 (local auth/users) not started yet — scheduled Days 3–4.

## Risks

- Host-network mode binds Postgres `:5432` and API `:8000` on the machine — document port conflicts for shared hosts.  
- Need pilot clinic `clinic_id` designation before Phase 5 migration.

## Plan for Day 2 / next

- Polish installer happy-path defaults for mini-PC (bridge first, auto-fallback).  
- CA trust helper script for Windows/Linux workstations.  
- Begin **Phase 1** tickets: local auth, sessions, role bootstrap at install.

## Production isolation check

- Canonical frontend untouched: `https://plateforme-sante-guinee.vercel.app`  
- No changes to Railway/Vercel deploy workflows required for this branch to stay isolated until merge window.
