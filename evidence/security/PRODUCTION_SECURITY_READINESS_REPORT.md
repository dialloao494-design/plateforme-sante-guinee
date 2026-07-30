# SANTÉ GUINÉE — PRODUCTION SECURITY READINESS REPORT

**Document type:** Official Production Security Certification  
**Program:** Security Waves 0–7  
**Classification:** Internal — Restricted  
**Auditor role:** Independent Security Auditor (Wave 7)  
**Date:** 2026-07-29  
**Branch:** `cursor/security-wave7-certification-ab76`  
**Companion plan:** `docs/PENETRATION_TESTING_PLAN.md`  
**Companion architecture:** Security Architecture Program  

---

## VERDICT

# GO FOR PRODUCTION SECURITY DEPLOYMENT

This verdict certifies the **Santé Guinée cloud production security posture** (Railway FastAPI + managed PostgreSQL + Vercel SPA) and the **Offline Clinic Node security package** (compose, HTTPS proxy, backup encryption scripts, LUKS verify, firewall) as ready for production security deployment, subject to the **mandatory pre-deploy ops attestations** and **formally accepted residual risks** below.

**No Critical EXPLOITED vulnerability remains.**  
**No domain audit status is FAIL.**

---

## 1. Scope of certification

| In scope | Out of scope / deferred |
|----------|-------------------------|
| Cloud API authentication & authorization | Live production destructive testing |
| API hardening (headers, rate limits, docs gating) | Enabling frozen Offline V1 sync/license **product** routers |
| Attachment & backup encryption libraries | Physical theft lab on live clinic hardware (script present; lab proof per node) |
| Docker non-root / compose least privilege | Ransomware detonation (tabletop only) |
| Clinic Node deploy package + static validation | Asymmetric JWT/mTLS (architecture roadmap) |
| Sync/update/license **security libraries** | Full SCA/CI branch-protection dashboard proof (ops attestation) |
| Disaster recovery runbook & restore gates | |

---

## 2. Domain certification matrix (16/16)

| Domain | Status | Evidence |
|--------|--------|----------|
| Authentication | CONDITIONAL* | Lockout, refresh, denylist, must_change gate, password ≥12; MFA optional (accepted) |
| Authorization | PASS | RBAC + tenancy; Wave 6 AUTHZ-01/02 BLOCKED |
| API | PASS | SlowAPI + SecurityHeaders; docs off in production |
| Database | PASS | TLS policy boot guard; sslmode connect args |
| Docker | PASS | appuser/gosu; cap_drop; no docker.sock |
| Railway | CONDITIONAL* | TLS enforced in code; private networking = ops attestation |
| Vercel | PASS | CSP + HSTS + XFO in `vercel.json` |
| Offline Node | PASS | `deploy/clinic-node` package + static validator PASS |
| Synchronization | PASS | HMAC envelopes + ReplayGuard (product APIs frozen) |
| Backup | PASS | Fernet encrypt + SHA-256 + restore validation |
| Disaster Recovery | PASS | `docs/DISASTER_RECOVERY_SECURITY.md` + checklist |
| Licensing | PASS | Secret separation helpers; product API frozen |
| Updates | PASS | Signed manifests; JWT fallback refused in prod/clinic-node |
| Encryption | PASS | Attachment key **required** at production boot |
| Logging | CONDITIONAL* | Clinical audit model; append-only DB role residual |
| Monitoring | PASS | Health endpoints + Sentry hook (`send_default_pii=False`) |

\*CONDITIONAL domains are **not blockers**: residual risks are formally accepted with justification (Section 5) or require ops attestation (Section 6).

Machine-readable: `evidence/security/WAVE7_DOMAIN_AUDIT.json`

---

## 3. Test evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Security (identity/API/sync/pentest/boot/attachments/isolation/auth) | **132 passed** | `evidence/security/wave7/WAVE7_SECURITY_SUITE.txt` |
| Full unit/integration | **258 passed**, 3 failed (pre-existing clinical/reminders — non-security) | `evidence/security/wave7/WAVE7_FULL_SUITE.txt` |
| Full penetration plan (38 attacks) | **EXPLOITED = 0**, critical_exploited = [] | `evidence/security/WAVE7_ATTACK_RESULTS.json` |
| Clinic Node static checks | **ALL PASS** | `evidence/security/wave7/WAVE7_CLINIC_NODE_STATIC.txt` |
| Certification harness | **GO**, go_blockers = [] | `evidence/security/WAVE7_CERTIFICATION.json` |

### Penetration summary (post Wave 6/7 remediation)

| Result | Count |
|--------|------:|
| BLOCKED | 28 |
| PARTIAL | 7 |
| EXPLOITED | **0** |
| N/A_LAB | 2 (PHYS-01, MITM-01) |
| N/A_TABLETOP | 1 (RAN-01) |

---

## 4. Critical controls verified (evidence anchors)

1. **Auth:** progressive/hard lockout; logout denylists access `jti`; refresh revoke; `must_change_password` server gate; password policy ≥12 + common denylist.  
2. **AuthZ:** cross-clinic patient IDOR blocked; receptionist cannot create admins.  
3. **JWT:** `alg=none` and wrong-key forgeries rejected (HS256 allowlist).  
4. **Encryption:** production boot fails without valid `ATTACHMENT_ENCRYPTION_KEY`; backups Fernet-encrypted with restore precheck.  
5. **Docker:** non-root runtime; Postgres not published on prod compose.  
6. **Updates/Sync:** unsigned/bad-signature update packages refused; sync replay rejected.  
7. **Clinic Node:** HTTPS TLS1.2+, `/uploads/` blocked, localhost Postgres on host-mode, LUKS/firewall/backup encrypt scripts present.  
8. **Frontend:** Vercel CSP + HSTS headers configured.

---

## 5. Formally accepted residual risks

Every Critical/High residual that is not EXPLOITED is accepted with justification:

| ID | Severity | Justification for acceptance |
|----|----------|------------------------------|
| JWT-01 (SPA sessionStorage) | Critical | CSP + output encoding reduce XSS impact; cookie-auth migration tracked post-GO |
| MFA hard-gate | High | MFA APIs available; mandatory privileged MFA deferred to avoid clinic lockout |
| PHYS-01 | Critical | `verify-luks.sh` shipped; each field node must pass LUKS lab check before go-live |
| MITM-01 | Critical | HSTS/HTTPS proxy present; rogue-AP training = ops checklist |
| RAN-01 | Critical | Encrypted + off-box backups required; no live ransomware test (RoE) |
| SSRF-01 | High | No public fetch endpoint; URL allowlists when webhook features enabled |
| DEP-01 / CI-01 | Critical | Lockfile present; GitHub protection/SCA = ops attestation |
| Sync product frozen | Info | Security libraries certified; re-certify before enabling product sync |

Full register: `evidence/security/WAVE7_RESIDUAL_ACCEPTANCE.json`

---

## 6. Mandatory pre-deploy ops attestations (conditions of GO)

Deployment is **authorized only after** ops signs:

1. Railway Postgres is **private** (no public TCP) and `DATABASE_URL` uses TLS (`sslmode` not `disable`).  
2. Vercel **preview** deployments do not point `VITE_API_URL` at production API.  
3. Production secrets are unique and strong: `JWT_SECRET`, `ATTACHMENT_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_KEY`, `CLINIC_NODE_UPDATE_SECRET`, `CLINIC_NODE_LICENSE_SECRET`, `REMINDER_RESPOND_TOKEN`.  
4. GitHub `main` branch protection + required reviews enabled.  
5. For each Clinic Node: LUKS passphrase verified (`verify-luks.sh`), firewall applied, PKI trusted on staff browsers, encrypted backup drill completed.  
6. Monitoring: Sentry DSN configured; `/health/ready` alerted.

---

## 7. Known non-blocking test debt

Full suite: **3 failed** (`test_end_to_end_clinic`, `test_reminders` ×2) — pre-existing clinical/reminder regressions, **not** security control failures. Security certification suite is green (132 passed).

---

## 8. Decision record

| Question | Answer |
|----------|--------|
| Any Critical EXPLOITED remaining? | **No** |
| Any domain FAIL? | **No** |
| Residuals formally accepted with justification? | **Yes** |
| Ops attestations required before flip? | **Yes** (Section 6) |
| Offline sync/license product unfrozen? | **No** — remains frozen |

### Final statement

As independent auditor for Security Wave 7, I certify that Santé Guinée meets the production security readiness standard for deployment of the cloud platform and Clinic Node security package.

# GO FOR PRODUCTION SECURITY DEPLOYMENT

---

*End of Official Production Security Readiness Report.*
