# Phase 0 — E2E Acceptance (COMPLETE)

**Status:** ALL acceptance criteria PASSED  
**Run:** `evidence/clinic-node/e2e-phase0/20260728T133741Z/`  
**Date (UTC):** 2026-07-28  

## Acceptance checklist

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Fresh installation on a clean machine | PASS | `01-fresh-install.log` |
| 2 | PostgreSQL starts automatically | PASS | `02-postgres-ready.txt` |
| 3 | FastAPI starts automatically | PASS | `02-compose-ps-after-install.txt` |
| 4 | Frontend accessible over HTTPS | PASS | `04-frontend-https-headers.txt`, `04-tls-cert-info.txt` |
| 5 | API can read and write PostgreSQL | PASS | `05-health-ready-read.json`, `05-api-db-readwrite.txt` |
| 6 | Full machine reboot simulated | PASS | `06-reboot-stop.log` |
| 7 | Everything starts automatically after reboot | PASS | `07-reboot-auto-start.log`, `07-compose-ps-after-reboot.txt` |
| 8 | No manual intervention required | PASS | single `compose up -d` boot path |
| 9 | Health endpoint returns READY | PASS | `09-health-ready-final.json` = `{"status":"ready","database":"ok"}` |

Additional: probe row survived reboot (`09-data-survived-reboot.txt`).

## How to re-run

```bash
CLINIC_NODE_NETWORK=host HTTP_PORT=8088 HTTPS_PORT=8443 \
  ./deploy/clinic-node/scripts/validate-e2e-phase0.sh
```

On a mini-PC with working Docker bridge, omit `CLINIC_NODE_NETWORK=host` and use ports 80/443.

## Production isolation

Validated stack is Compose project `clinic-node` under `deploy/clinic-node/`.  
Cloud production (`https://plateforme-sante-guinee.vercel.app`) was not modified.
