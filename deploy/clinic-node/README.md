# Clinic Node — technician runbook (Phase 0)

**Goal:** install the local clinic server in under 30 minutes with **no complex commands**.

## What you need

1. Mini-PC (NUC or equivalent, ≥16 GB RAM, SSD)  
2. UPS / onduleur  
3. This repository (or USB image) with Docker installed  

## Install (one command)

```bash
./deploy/clinic-node/install/install.sh
```

The installer will:

- create `/data` directories (Postgres, uploads, logs, PKI, backups)
- generate strong secrets
- generate local HTTPS certificates (CA + server)
- start PostgreSQL + FastAPI + SPA + HTTPS proxy
- wait until `/health/ready` succeeds

## After install

1. Open **https://sante-locale** or **https://&lt;LAN-IP&gt;**  
2. On each workstation, trust **`data/pki/ca-trust.crt`** once (OS / browser)  
3. HTTP is redirected to HTTPS automatically  

## Auto-start after reboot

Services use `restart: unless-stopped`.  
Optional systemd unit:

```bash
sudo cp deploy/clinic-node/systemd/clinic-node.service /etc/systemd/system/
# Edit WorkingDirectory to the real repo path
sudo systemctl daemon-reload
sudo systemctl enable --now clinic-node.service
```

## Validate crash / reboot safety

```bash
./deploy/clinic-node/scripts/validate-reboot-safe.sh
```

## Full Phase 0 E2E acceptance (required to close Phase 0)

```bash
./deploy/clinic-node/scripts/validate-e2e-phase0.sh
```

Evidence is written under `evidence/clinic-node/` (and `e2e-phase0/` for full acceptance).

## Network modes

| Mode | When |
|------|------|
| **bridge** (default `compose.yml`) | Normal mini-PC / production LAN |
| **host** (`compose.host.yml`) | Nested CI/cloud VMs where Docker bridge/veth is broken |

Force host mode:

```bash
CLINIC_NODE_NETWORK=host ./deploy/clinic-node/install/install.sh
```

Non-default ports (lab / shared hosts):

```bash
HTTP_PORT=8088 HTTPS_PORT=8443 CLINIC_NODE_NETWORK=host ./deploy/clinic-node/install/install.sh
```

## Phase 0 complete when

- [x] Local Postgres + API + SPA + HTTPS  
- [x] Installer without manual docker/sql  
- [x] Restart policies + optional systemd  
- [x] Reboot-safe validation script  

**Next (Phase 1):** local authentication, sessions, roles.
