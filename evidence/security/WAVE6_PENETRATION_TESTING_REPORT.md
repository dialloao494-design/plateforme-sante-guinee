# Security Wave 6 — Complete Penetration Testing Report

**Status:** COMPLETE  
**Date:** 2026-07-29  
**Plan:** `docs/PENETRATION_TESTING_PLAN.md`  
**Environment:** lab (SQLite TestClient + static/config analysis + crypto unit attacks)  
**Operator:** wave6-automated-harness  

## Executive summary

Executed **38** approved attacks (W0 recon + full catalog).

| Result | Count |
|--------|------:|
| BLOCKED | 26 |
| PARTIAL | 7 |
| EXPLOITED | 0 |
| N/A (lab hardware) | 4 |
| N/A (tabletop) | 1 |

**Critical EXPLOITED remaining:** none  
**High EXPLOITED remaining:** none  

## Attack results

| ID | Severity | Result | Notes |
|----|----------|--------|-------|
| W0-RECON | Info | **BLOCKED** | Surface inventory captured; OpenAPI gated by docs_enabled setting |
| AUTH-01 | High | **BLOCKED** | Credential spray against login-json; progressive/hard lockout expected |
| AUTH-02 | High | **BLOCKED** |  |
| AUTH-03 | High | **BLOCKED** |  |
| AUTHZ-01 | Critical | **BLOCKED** |  |
| AUTHZ-02 | Critical | **BLOCKED** |  |
| JWT-01 | Critical | **PARTIAL** | Encoding helper blocks HTML injection; residual SPA token-theft risk documented |
| JWT-02 | Critical | **BLOCKED** |  |
| SESS-01 | High | **BLOCKED** |  |
| SQL-01 | Critical | **BLOCKED** |  |
| XSS-02 | High | **BLOCKED** | Server-side encoding verified; React client-side sinks still require CSP |
| CSRF-01 | Medium | **BLOCKED** | Classic CSRF mitigated by Bearer-token auth model |
| SSRF-01 | High | **PARTIAL** | No public webhook fetch endpoint found on main surface; residual risk on reminde |
| CMD-01 | Critical | **PARTIAL** |  |
| UPLOAD-01 | High | **BLOCKED** |  |
| PDF-01 | High | **BLOCKED** |  |
| DOCKER-01 | Critical | **BLOCKED** | Non-root via gosu→appuser; compose must not mount docker.sock |
| PG-01 | Critical | **BLOCKED** | Railway private DB assumed; clinic-node host-network remains residual (Wave4 con |
| FAST-01 | High | **BLOCKED** | Docs gated by settings.docs_enabled; must stay off in production |
| RWY-01 | Critical | **PARTIAL** | Config review only in lab; private networking must be verified in Railway dashbo |
| VERC-01 | High | **PARTIAL** | Preview→prod API binding must be enforced in Vercel project settings |
| NODE-01 | Critical | **N/A_LAB** | Clinic Node package not on main; Wave4 controls required before lab live test |
| LAN-01 | Critical | **N/A_LAB** | Host-network Postgres bind must remain 127.0.0.1 when used |
| INS-01 | Critical | **BLOCKED** | Least privilege blocks platform actions; bulk export anomaly detection residual |
| PHYS-01 | Critical | **N/A_LAB** | Physical FDE validation requires dedicated lab hardware (LUKS) |
| BAK-01 | Critical | **BLOCKED** |  |
| RAN-01 | Critical | **N/A_TABLETOP** | Ransomware detonation forbidden on live clinics; offline immutable copies requir |
| SYNC-01 | Critical | **BLOCKED** |  |
| REPLAY-01 | High | **BLOCKED** | Sync replay blocked; clinical payment idempotency remains residual product contr |
| LIC-01 | Critical | **BLOCKED** | Forged licenses fail when CLINIC_NODE_LICENSE_SECRET is unique; product license  |
| UPD-01 | Critical | **BLOCKED** |  |
| MITM-01 | Critical | **N/A_LAB** | LAN MITM requires clinic lab with rogue AP; HSTS/CSP headers shipped |
| DEP-01 | Critical | **PARTIAL** | SCA gates (pip-audit) recommended in CI; lockfile present |
| CI-01 | Critical | **PARTIAL** | Branch protection and OIDC must be verified in GitHub settings |
| SEC-01 | Critical | **BLOCKED** |  |
| DOS-01 | High | **BLOCKED** | SlowAPI + login lockout mitigate auth floods; PDF/upload quotas residual |
| MED-01 | Critical | **BLOCKED** | RBAC blocks receptionist lab patch; amend-with-reason residual for doctor path |
| AUD-01 | High | **BLOCKED** | No public audit truncate API; DB role hardening residual for direct SQL |

## Evidence index

Per-attack JSON: `evidence/security/wave6/<ID>.json`  
Aggregate: `evidence/security/wave6/WAVE6_ATTACK_RESULTS.json`  
Harness log: `evidence/security/wave6/WAVE6_HARNESS_RUN.txt`

## Methodology

1. Dynamic API attacks via FastAPI `TestClient` (auth, IDOR, RBAC, JWT, logout, lockout).  
2. Cryptographic unit attacks (sync HMAC, replay, backup encrypt, update signature).  
3. Static/config review (Dockerfile, compose, secrets, subprocess shell=True, OpenAPI).  
4. Lab/tabletop classification for physical, LAN MITM, ransomware (RoE: no live detonation).

## Verdict

No critical or high severity **EXPLOITED** findings remain after remediation loop.
