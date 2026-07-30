# Santé Guinée — Security Wave 4 Report

**Wave:** 4 — Clinic Node / Mini-PC / Local Postgres / LAN / Local auth / Local HTTPS / Physical theft / Local encryption / Offline DB / Local backups  
**Status:** COMPLETE  
**Date:** 2026-07-29  
**Branch:** `cursor/security-wave4-clinic-node-ab76`

---

## 1. Implemented protections

| Area | Implementation |
|------|----------------|
| **Clinic Node package** | Restored security scaffolding under `deploy/clinic-node/` (compose, PKI, HTTPS proxy, installer) without unfreezing Offline V1 product features |
| **Local PostgreSQL** | Bridge compose never publishes 5432; host-network binds `listen_addresses=127.0.0.1` |
| **LAN** | Firewall script `harden-host-firewall.sh` (ufw: 80/443 + SSH; deny 5432/8000); host-network lab-only + boot ack |
| **Local authentication / secrets** | `ENVIRONMENT=clinic-node` treated as deployed; unique license/update secrets; Fernet `ATTACHMENT_ENCRYPTION_KEY` required; seed flags forbidden |
| **Local HTTPS** | PKI generator; TLS 1.2/1.3; HSTS; CSP; HTTP→HTTPS; `/uploads/` 403; PKI permission audit |
| **Physical theft / LUKS** | `verify-luks.sh` evidence helper + field checklist |
| **Local encryption** | Attachment Fernet at boot; backup encrypt/decrypt via age/gpg + SHA-256 sidecars |
| **Local backups** | Encrypt-before-offbox scripts; checklist 3-2-1 guidance |

---

## 2. Validation evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Wave 4 clinic-node + boot tests | **39 passed** | `evidence/security/WAVE4_PYTEST_CLINIC_NODE.txt` |
| Full backend pytest | **221 passed** | `evidence/security/WAVE4_PYTEST_FULL.txt` |
| Static clinic-node validation | **PASS** | `evidence/security/WAVE4_CLINIC_NODE_STATIC.txt` |
| Smoke | **WAVE4 SMOKE OK** | `evidence/security/WAVE4_SMOKE.txt` |

Checklist: `docs/CLINIC_NODE_SECURITY_HARDENING_CHECKLIST.md`

---

## 3. Ops notes

- Mini-PC default: **bridge** networking.
- Host-network requires `CLINIC_NODE_ALLOW_HOST_NETWORK=true`.
- After install: firewall + LUKS verify + PKI audit + encrypt backups.
- Never commit `deploy/clinic-node/data/`, `.env`, or `*.pem`.

---

## 4. Remaining risks

| Risk | Notes |
|------|-------|
| CA private key on-node | Prefer offline CA for higher assurance (documented) |
| Offline V1 sync/license product | Frozen — not part of this wave |
| age may be absent on host | Install `age` or use GPG passphrase path |

---

## 5. Verdict

**Security Wave 4 is COMPLETE.** All automated validations pass (221 pytest).
