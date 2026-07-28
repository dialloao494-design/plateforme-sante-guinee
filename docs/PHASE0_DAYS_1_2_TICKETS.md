# Phase 0 — Implementation Tickets (Days 1–2)

**Status:** Approved for execution — start immediately  
**Scope:** Clinic Node foundation only (no Phase 1+ auth/sync yet)  
**Isolation:** All work under `deploy/clinic-node/` + minimal `ENVIRONMENT=clinic-node` support  
**Must not break:** Railway/Vercel production (`plateforme-sante-guinee.vercel.app`)

---

## Day 1 tickets

| ID | Ticket | Acceptance criteria |
|----|--------|---------------------|
| **CN-P0-01** | Clinic Node compose stack | `deploy/clinic-node/compose.yml` brings up `db` (PostgreSQL 16) + `backend` + `frontend` + `proxy` with project name `clinic-node`; data on bind mount `/data` (or `./data`); does not modify root `docker-compose.yml` used by cloud/VPS paths |
| **CN-P0-02** | Env + secrets bootstrap | `deploy/clinic-node/env/clinic-node.env.example` + installer generates strong `JWT_SECRET`, `POSTGRES_PASSWORD`, `NODE_ID`; `ENVIRONMENT=clinic-node` |
| **CN-P0-03** | `ENVIRONMENT=clinic-node` mode | Settings treat clinic-node as deployed (strong secrets, trusted proxy) without cloud-production seed bans blocking local bootstrap; production boot guards for `ENVIRONMENT=production` unchanged |
| **CN-P0-04** | Local HTTPS / PKI | Script generates local CA + server cert for `sante-locale` / localhost / LAN IP into `/data/pki`; nginx terminates TLS; HTTP→HTTPS redirect |
| **CN-P0-05** | Health endpoints wired | `/health` and `/health/ready` succeed through HTTPS proxy after stack is up |

## Day 2 tickets

| ID | Ticket | Acceptance criteria |
|----|--------|---------------------|
| **CN-P0-06** | One-command installer | `deploy/clinic-node/install/install.sh` (UI-friendly prompts or defaults): create dirs, generate secrets/certs, start compose — **no manual docker/sql commands** for the happy path |
| **CN-P0-07** | Automatic startup after reboot | `restart: unless-stopped` on all services + optional systemd unit `clinic-node.service` that runs compose on boot |
| **CN-P0-08** | Reboot-safe validation harness | `deploy/clinic-node/scripts/validate-reboot-safe.sh`: stop/kill simulation → restart → assert Postgres + API ready + HTTPS OK; writes evidence under `evidence/clinic-node/` |
| **CN-P0-09** | Technician 1-page runbook | `deploy/clinic-node/README.md` — plug UPS, run install, open `https://sante-locale` (or IP), trust CA note |
| **CN-P0-10** | Automated tests + evidence | Unit tests: 32 passed. **E2E acceptance: ALL PASSED** — see `evidence/clinic-node/PHASE0_E2E_ACCEPTANCE.md` |

---

## Explicitly out of Days 1–2

- Local login UX overhaul (Phase 1)  
- Module workflow parity (Phase 2)  
- Sync / backups / licenses (Phase 3)  
- Owner dashboard (Phase 4)  
- Railway migration / pilot cutover (Phase 5)  

---

## Phase 0 closure gate

Phase 0 is **complete** only after E2E acceptance:

```bash
./deploy/clinic-node/scripts/validate-e2e-phase0.sh
```

Latest run: **ALL CRITERIA PASSED** (`PHASE0_E2E_ACCEPTANCE_PASSED`).

---

## Execution order today

1. CN-P0-03 → CN-P0-01 → CN-P0-02 → CN-P0-04 → CN-P0-05  
2. CN-P0-06 → CN-P0-07 → CN-P0-08 → CN-P0-09 → CN-P0-10  
3. Full E2E acceptance harness  
4. Daily report with evidence  

---

*Tickets locked for Days 1–2 — Phase 0 E2E acceptance complete.*
