# Santé Guinée — Official Penetration Testing Plan

**Document type:** Penetration Testing Roadmap (Red Team planning)  
**Classification:** Internal — Restricted (do not share outside security / eng leadership)  
**Role of author:** Senior Red Team Security Engineer  
**Stance:** Adversarial — assume the goal is to compromise Santé Guinée and exfiltrate or alter medical data  
**Status:** Planning only — **no exploitation, no code, no fixes, no implementation in this phase**  
**Depends on:** `docs/SECURITY_ARCHITECTURE.md` (approved)  
**Out of scope for this document:** Remediation design details beyond a one-line “expected mitigation” per attack  

---

## 0. Engagement framing

### 0.1 Mission

Identify **every realistic attack** that should be attempted against Santé Guinée across:

- Cloud production (Vercel SPA + Railway FastAPI + PostgreSQL)  
- Offline Clinic Node (LAN mini-PC: nginx TLS + API + Postgres + backups + PKI)  
- Sync / license / update control planes  
- Human and physical clinic operations  

This plan is the **official penetration testing roadmap**. Execution happens only under a later authorized Rules of Engagement (RoE).

### 0.2 Assumed attacker personas

| Persona | Access starting point | Primary goals |
|---------|----------------------|---------------|
| **External internet attacker** | Public SPA + API URLs | Account takeover, API abuse, mass PHI theft |
| **Adjacent LAN attacker** | Clinic Wi-Fi / Ethernet | MITM, node service abuse, credential sniffing |
| **Malicious or coerced insider** | Valid low/high privilege staff account | Chart snooping, fraud, cover-up, exfil |
| **Physical thief** | Stolen mini-PC or backup USB | Offline dump of PHI + secrets |
| **Supply-chain adversary** | PyPI/npm/Docker/GitHub Actions | Backdoor deploy path |
| **Opportunistic ransomware crew** | Phish or RCE → encrypt | Deny care + extort |

### 0.3 Target surfaces (attacker’s map)

```
[Internet]
  └─ Vercel SPA (JWT in sessionStorage, XSS/CSP)
  └─ Railway API (auth, clinical CRUD, uploads, PDFs, platform)
  └─ Postgres (via app; direct if mis-exposed)

[Clinic LAN]
  └─ https://sante-locale / LAN IP (local PKI)
  └─ FastAPI :8000 (if host-network leak)
  └─ Postgres :5432 (if bound/exposed)
  └─ data/backups, data/pki, .env on disk

[Ops plane]
  └─ Sync ingest (token / shared secret)
  └─ License tokens (HMAC)
  └─ Update packages (manifest.sig)
```

### 0.4 Scoring model

| Field | Scale |
|-------|-------|
| **Probability** | Low / Medium / High (likelihood a skilled attacker succeeds *given current known posture*) |
| **Severity** | Low / Medium / High / Critical (impact on confidentiality, integrity, availability of care) |
| **Risk score** | Critical=5, High=4, Medium=3, Low=2, Info=1 for severity; High=3, Medium=2, Low=1 for probability; **Risk = Severity×Probability** (max 15) |

**Ranking rule:** Sort by Risk descending; ties broken by Severity, then healthcare patient-safety impact.

### 0.5 Legend for “Expected mitigation”

One-line **future** control only — **not** an implementation instruction and **not** authorized work in this phase.

### 0.6 Rules of Engagement (to be signed before any live test)

- Prefer **staging** with anonymized data.  
- Production tests only with written approval; no destructive restores; no mass patient export.  
- No ransomware detonation on live clinics.  
- Physical theft tests only on **dedicated lab hardware**.  
- Stop and report immediately on unexpected PHI exposure beyond test accounts.  

---

## 1. Master risk ranking (executive attack backlog)

| Rank | ID | Attack theme | Prob. | Sev. | Risk | Primary target |
|------|----|--------------|-------|------|------|----------------|
| 1 | AUTHZ-01 | Cross-clinic / IDOR patient record access | High | Critical | 15 | API tenancy |
| 2 | AUTHZ-02 | Privilege escalation via role/permission gaps | High | Critical | 15 | RBAC |
| 3 | PHYS-01 | Stolen Mini-PC disk dump (no/weak FDE) | High | Critical | 15 | Clinic Node |
| 4 | BAK-01 | Backup theft (plaintext `.sql.gz`) | High | Critical | 15 | Node / USB |
| 5 | JWT-01 | XSS → JWT theft → full staff session | High | Critical | 15 | Vercel SPA |
| 6 | INS-01 | Insider bulk chart export / snooping | High | Critical | 15 | Clinical API |
| 7 | AUTH-01 | Credential stuffing / password spray on login | High | High | 12 | Auth API |
| 8 | SYNC-01 | Sync ingest forgery / replay with weak token | Med | Critical | 10 | Sync plane |
| 9 | LIC-01 | License forgery via shared HMAC secret | Med | Critical | 10 | Node license |
| 10 | UPD-01 | Malicious signed update if secret stolen | Med | Critical | 10 | Update agent |
| 11 | SEC-01 | Secrets in git, logs, Actions, `.env` world-readable | Med | Critical | 10 | Secrets |
| 12 | MITM-01 | LAN MITM with rogue CA / untrusted HTTPS | Med | Critical | 10 | Clinic LAN |
| 13 | RAN-01 | Ransomware encrypts node + local backups | Med | Critical | 10 | Availability |
| 14 | UPLOAD-01 | Malicious attachment → staff compromise | Med | High | 8 | Uploads |
| 15 | AUTH-02 | Session fixation / long-lived JWT abuse | Med | High | 8 | Sessions |
| 16 | JWT-02 | Algorithm / secret confusion / weak secret | Low | Critical | 5 | JWT |
| 17 | SQL-01 | SQL injection on raw SQL / filters | Low | Critical | 5 | API/DB |
| 18 | DOCKER-01 | Container escape / docker.sock abuse | Low | Critical | 5 | Node Docker |
| 19 | PG-01 | Direct Postgres network access | Low | Critical | 5 | DB |
| 20 | DEP-01 | Malicious dependency / typo-squat | Low | Critical | 5 | Supply chain |
| 21 | CI-01 | GitHub Actions secret theft → prod deploy | Low | Critical | 5 | Supply chain |
| 22 | SSRF-01 | Server-side request forgery via URL fields | Low | High | 4 | API |
| 23 | CMD-01 | OS command injection in backup/update scripts | Low | Critical | 5 | Ops scripts |
| 24 | PDF-01 | Malicious PDF generation / SSRF via renderer | Low | High | 4 | PDF pipeline |
| 25 | CSRF-01 | State-changing CSRF (if cookie auth ever used) | Low | Medium | 2 | SPA/API |
| 26 | XSS-02 | Stored/reflected XSS in clinical UIs | Med | High | 8 | Frontend |
| 27 | FAST-01 | Unauthenticated FastAPI route / docs leak | Med | High | 8 | API surface |
| 28 | RWY-01 | Railway misconfig / public DB / weak env | Low | Critical | 5 | Cloud |
| 29 | VERC-01 | Vercel preview → production API / env leak | Med | High | 8 | Frontend |
| 30 | LAN-01 | Attack exposed :8000/:5432 on host-network | Med | Critical | 10 | Clinic Node |
| 31 | AUD-01 | Audit log tampering / disable | Med | High | 8 | Integrity |
| 32 | MED-01 | Lab/Rx/result medical record tampering | Med | Critical | 10 | Clinical integrity |
| 33 | DOS-01 | Auth/API/DB denial of service | High | High | 12 | Availability |
| 34 | AUTH-03 | Password reset / must_change bypass | Med | High | 8 | Auth |
| 35 | REPLAY-01 | Replay of clinical or sync requests | Med | High | 8 | Sync/API |

*Note: Several items share similar scores; detailed cards below are the authoritative test cases. Execution order for a first engagement: Rank 1–15 first.*

---

## 2. Attack catalog

Each attack includes: Objective · Scenario · Impact · Probability · Severity · Required validation · Expected mitigation (non-implementing).

---

### AUTH-01 — Credential stuffing / password spray

| Field | Content |
|-------|---------|
| **Objective** | Obtain valid staff or patient credentials without malware |
| **Attack scenario** | Enumerate `/api/auth/login` and `/api/auth/login-json`; spray common Guinean/French passwords and leaked corp emails; rotate IPs or slow-rate to evade naive limits |
| **Expected impact** | Account takeover → PHI read/write as that role |
| **Probability** | High |
| **Severity** | High |
| **Required validation** | Confirm lockout/rate-limit thresholds; measure attempts until block; test notification on burst; verify no user enumeration via timing/messages |
| **Expected mitigation** | MFA for staff; progressive lockout; bot detection; breached-password blocking |

---

### AUTH-02 — Long-lived JWT / logout is client-only

| Field | Content |
|-------|---------|
| **Objective** | Reuse a stolen Bearer token after “logout” or shift change |
| **Attack scenario** | Capture `Authorization: Bearer` from DevTools/proxy; call logout in UI; replay token against clinical APIs until expiry |
| **Expected impact** | Persistent unauthorized access; attribution failure |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Prove tokens remain valid post-logout; measure TTL; test refresh (if any) revocation |
| **Expected mitigation** | Short TTL + server-side refresh revocation / denylist |

---

### AUTH-03 — Password reset / must_change_password bypass

| Field | Content |
|-------|---------|
| **Objective** | Keep using temporary credentials or skip forced password change |
| **Attack scenario** | After admin reset, call clinical APIs directly with temp JWT; skip `/account/password` UI; attempt to unset `must_change_password` via profile/update endpoints |
| **Expected impact** | Shared temp passwords remain forever; insider persistence |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Middleware/gate must reject clinical writes until password changed; negative tests on all privileged routes |
| **Expected mitigation** | Hard server-side gate on all non-auth routes when flag set |

---

### AUTHZ-01 — Cross-clinic IDOR / tenancy bypass

| Field | Content |
|-------|---------|
| **Objective** | Read or modify another clinic’s patients, labs, bills |
| **Attack scenario** | As clinic A staff, substitute `patient_id`, `consultation_id`, `lab_order_id`, attachment IDs from clinic B in GET/PATCH/DELETE; fuzz numeric IDs; try platform endpoints with clinic_admin token |
| **Expected impact** | **Critical PHI breach** across organizations |
| **Probability** | High *(tenancy bugs are the #1 healthcare API failure mode)* |
| **Severity** | Critical |
| **Required validation** | Full matrix: every object ID endpoint × foreign clinic IDs → must be 403/404; include PDF and attachment downloads |
| **Expected mitigation** | Mandatory tenancy check helper on every resource load |

---

### AUTHZ-02 — Privilege escalation / RBAC gap exploitation

| Field | Content |
|-------|---------|
| **Objective** | Act as receptionist/nurse/cashier beyond allowed actions; or patient → staff |
| **Attack scenario** | Map all roles; call staff-create, lab validate, dispense, pay, platform setup, clinic-node ops, hospitalization admin; exploit roles missing from permission maps or DB CHECK drift (`nurse`/`pev_agent` class issues) |
| **Expected impact** | Fraud, unauthorized clinical decisions, platform takeover |
| **Probability** | High |
| **Severity** | Critical |
| **Required validation** | Complete role×endpoint allow/deny matrix automated; include “forgotten” routes |
| **Expected mitigation** | Single RBAC source of truth + CI drift detection |

---

### JWT-01 — XSS leading to JWT exfiltration

| Field | Content |
|-------|---------|
| **Objective** | Steal Bearer token from `sessionStorage` via script injection |
| **Attack scenario** | Inject script into reflected/stored fields (names, notes, PDF-linked HTML if any); or exploit third-party script on Vercel; exfil token to attacker server; replay API |
| **Expected impact** | Full impersonation of victim staff; mass PHI access |
| **Probability** | High *(SPA token storage + any XSS = game over)* |
| **Severity** | Critical |
| **Required validation** | XSS scan of all user-influenced renders; CSP effectiveness; token storage review |
| **Expected mitigation** | Strict CSP; sanitize outputs; prefer httpOnly secure cookies with CSRF defenses *or* hardened token handling + XSS elimination |

---

### JWT-02 — JWT cryptographic / algorithm abuse

| Field | Content |
|-------|---------|
| **Objective** | Forge tokens without valid credentials |
| **Attack scenario** | Test `alg=none`, key confusion, weak/guessable `SECRET_KEY`/`JWT_SECRET`, leaked secrets from env examples; forge `role=platform_admin` claims |
| **Expected impact** | Instant platform compromise |
| **Probability** | Low–Medium (depends on secret strength) |
| **Severity** | Critical |
| **Required validation** | jose/jwt attack suite; secret entropy review; reject `none` |
| **Expected mitigation** | Strong unique secrets; asymmetric JWT for cloud; hard alg allowlist |

---

### SESS-01 — Session fixation / concurrent session abuse

| Field | Content |
|-------|---------|
| **Objective** | Bind victim to attacker-controlled session or ride parallel sessions |
| **Attack scenario** | If any cookie session exists, fixate; otherwise abuse multiple parallel JWTs from one account across clinics/devices without invalidation |
| **Expected impact** | Stealth persistence after password change (if tokens not revoked) |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Password change must invalidate prior tokens; concurrent session policy tests |
| **Expected mitigation** | Token family revocation on password change |

---

### SQL-01 — SQL injection

| Field | Content |
|-------|---------|
| **Objective** | Extract or modify DB via injected SQL |
| **Attack scenario** | Fuzz query params, search boxes, filters, raw `text()` migrations leftovers, export endpoints, migration scripts inputs; time-based and boolean blind SQLi |
| **Expected impact** | Full DB compromise including all PHI |
| **Probability** | Low *(SQLAlchemy dominant)* but **Critical if any raw path exists** |
| **Severity** | Critical |
| **Required validation** | Automated SQLi scanner + manual review of every `text(` / f-string SQL |
| **Expected mitigation** | Parameterized queries only; WAF optional secondary |

---

### XSS-02 — Stored / reflected XSS in clinical UI

| Field | Content |
|-------|---------|
| **Objective** | Execute JS in another user’s browser |
| **Attack scenario** | Plant payloads in patient names, clinical notes, pharmacy notes, error messages; open as doctor/admin |
| **Expected impact** | Token theft, fake UI actions (dispense/pay), defacement |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Manual XSS test pack per form field; DOM sinks audit |
| **Expected mitigation** | Context-aware encoding; CSP; React dangerous HTML ban |

---

### CSRF-01 — Cross-site request forgery

| Field | Content |
|-------|---------|
| **Objective** | Cause authenticated browser to perform state changes |
| **Attack scenario** | If auth moves to cookies, host malicious page that POSTs to API; currently Bearer-from-storage reduces classic CSRF — re-test if auth model changes |
| **Expected impact** | Unwanted clinical/financial actions |
| **Probability** | Low *(today)* / High *(if cookie auth)* |
| **Severity** | Medium–High |
| **Required validation** | Confirm Authorization header requirement; re-test after any cookie auth |
| **Expected mitigation** | SameSite cookies + CSRF tokens if cookie sessions introduced |

---

### SSRF-01 — Server-side request forgery

| Field | Content |
|-------|---------|
| **Objective** | Coerce API to fetch internal URLs (metadata, localhost, cloud IMDS) |
| **Attack scenario** | Inject `http://169.254.169.254/`, `http://127.0.0.1:5432`, file URLs into webhook/reminder/teleconsult/export URL fields; sync `CLOUD_SYNC_URL` manipulation on node |
| **Expected impact** | Cloud credential theft; internal port scan; sync redirection |
| **Probability** | Low–Medium |
| **Severity** | High |
| **Required validation** | Inventory all outbound HTTP clients; block link-local and private ranges |
| **Expected mitigation** | URL allowlists; egress controls |

---

### CMD-01 — Command injection in ops scripts / backup paths

| Field | Content |
|-------|---------|
| **Objective** | Execute OS commands on node or CI runner |
| **Attack scenario** | Feed metacharacters into backup path, update package paths, migration filenames, clinic names used in shell; abuse API that shells out to `pg_dump`/`docker` |
| **Expected impact** | Root/host compromise; ransomware foothold |
| **Probability** | Low–Medium on node ops surfaces |
| **Severity** | Critical |
| **Required validation** | Code review of all `subprocess`/`bash -lc`; fuzz path parameters |
| **Expected mitigation** | Argv arrays only; no shell; path allowlists |

---

### UPLOAD-01 — Malicious file upload / download chain

| Field | Content |
|-------|---------|
| **Objective** | Store malware or achieve XSS via Content-Type; path traversal to read secrets |
| **Attack scenario** | Upload polyglots, SVG/HTML, double extensions, oversized files, path `../` in filenames; download as other roles; hit legacy `/uploads/` URLs |
| **Expected impact** | Workstation compromise; PHI file theft; stored XSS |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Upload fuzzer; confirm `/uploads` blocked; authz on every download; MIME sniff tests |
| **Expected mitigation** | Allowlist + random object keys + authz + AV scan + encryption |

---

### PDF-01 — PDF generation / delivery attacks

| Field | Content |
|-------|---------|
| **Objective** | Leak PHI PDFs, inject content, or abuse renderer |
| **Attack scenario** | Unauthorized GET on PDF endpoints with guessed IDs; inject HTML/JS into fields rendered into PDF; exhaust disk with mass generation |
| **Expected impact** | PHI disclosure; DoS; possible SSRF if HTML renderer used |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | IDOR on all PDF routes; renderer threat review |
| **Expected mitigation** | Authz + watermark + no untrusted HTML→PDF |

---

### DOCKER-01 — Container escape / privilege abuse

| Field | Content |
|-------|---------|
| **Objective** | Break from backend container to host |
| **Attack scenario** | If privileged/docker.sock/CAP_SYS_ADMIN present, escape; abuse writable docker.sock; kernel exploit from container |
| **Expected impact** | Full mini-PC ownership including all clinics’ data on that node |
| **Probability** | Low *(if hardened)* / High *(if sock mounted)* |
| **Severity** | Critical |
| **Required validation** | Compose audit; capability drop; runtime security scan |
| **Expected mitigation** | Non-root, no sock, dropped caps, read-only FS |

---

### PG-01 — Direct PostgreSQL attacks

| Field | Content |
|-------|---------|
| **Objective** | Connect to Postgres bypassing API |
| **Attack scenario** | Scan LAN/host for `:5432`; try default creds from `.env` leakage; abuse host-network clinic-node binds; SQL as superuser |
| **Expected impact** | Complete PHI dump and destruction |
| **Probability** | Medium on misconfigured nodes; Low on Railway private net |
| **Severity** | Critical |
| **Required validation** | External/LAN port scan; verify bind addresses; credential strength |
| **Expected mitigation** | Localhost/docker-net only; strong passwords; TLS; least-privilege roles |

---

### FAST-01 — FastAPI surface abuse

| Field | Content |
|-------|---------|
| **Objective** | Find unauthenticated or over-informative endpoints |
| **Attack scenario** | Hit `/docs`, `/openapi.json`, `/redoc` in prod; fuzz undocumented routes; abuse mass-assignment on Pydantic models; trigger verbose 500s |
| **Expected impact** | Recon goldmine; accidental data leak; auth bypass on missed Depends |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | OpenAPI inventory vs public allowlist; force error paths |
| **Expected mitigation** | Docs off; default-deny auth; sanitized errors |

---

### RWY-01 — Railway platform attacks

| Field | Content |
|-------|---------|
| **Objective** | Compromise cloud API/DB via platform misconfig |
| **Attack scenario** | Probe public networking; steal leaked Railway tokens from GitHub; abuse staging=prod secret mix; SSRF to internal Railway DNS |
| **Expected impact** | Full cloud PHI breach |
| **Probability** | Low–Medium |
| **Severity** | Critical |
| **Required validation** | Config review; token scope audit; network exposure test |
| **Expected mitigation** | Private DB; least-privilege tokens; env separation |

---

### VERC-01 — Vercel / SPA hosting attacks

| Field | Content |
|-------|---------|
| **Objective** | Abuse frontend hosting to hit production API or leak config |
| **Attack scenario** | Preview deployments with prod `VITE_API_URL`; XSS via compromised dependency; steal env; phishing clone on similar domain |
| **Expected impact** | Credential phishing; API abuse at scale |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Preview env audit; CSP headers; domain allowlist |
| **Expected mitigation** | Previews→staging only; strict CSP; canonical URL controls |

---

### NODE-01 — Offline Clinic Node application attacks

| Field | Content |
|-------|---------|
| **Objective** | Compromise local appliance APIs as LAN attacker |
| **Attack scenario** | From clinic Wi-Fi, attack HTTPS (cert warnings), hit APIs without CA trust using `-k`, brute admin, abuse clinic-node ops routes, disable license checks mentally by finding unsigned paths |
| **Expected impact** | Local PHI breach without internet |
| **Probability** | High *(LAN is softer than internet edge)* |
| **Severity** | Critical |
| **Required validation** | Full API test from “guest Wi-Fi” vantage; ops route authz |
| **Expected mitigation** | Network segmentation; strong auth; firewall; monitoring |

---

### LAN-01 — Host-network / exposed service attacks

| Field | Content |
|-------|---------|
| **Objective** | Reach Postgres/API directly when bridge networking abandoned |
| **Attack scenario** | On host-network deployments, connect to `:5432`/`:8000` bypassing nginx controls |
| **Expected impact** | Bypass TLS and app gateway |
| **Probability** | Medium *(known fallback mode exists)* |
| **Severity** | Critical |
| **Required validation** | Port scan in host-network mode; treat as production anti-pattern |
| **Expected mitigation** | Forbid host-network in production; firewall if unavoidable |

---

### INS-01 — Clinic insider abuse

| Field | Content |
|-------|---------|
| **Objective** | Misuse legitimate access for espionage, fraud, or revenge |
| **Attack scenario** | Receptionist exports patients; cashier voids; doctor alters notes after complaint; admin creates ghost staff; shared login “nurse1” |
| **Expected impact** | Privacy violations; fraud; care integrity loss; legal exposure |
| **Probability** | High |
| **Severity** | Critical |
| **Required validation** | Access audit coverage; bulk-download detection; dual-control gaps |
| **Expected mitigation** | Named accounts; audit; anomaly alerts; least privilege |

---

### PHYS-01 — Lost or stolen Mini-PC

| Field | Content |
|-------|---------|
| **Objective** | Offline extraction of all clinic data and secrets |
| **Attack scenario** | Steal device; remove disk; image; mount; read Docker volumes, `data/postgres`, `data/backups`, `data/pki`, `.env` |
| **Expected impact** | Catastrophic PHI + CA key + JWT secret compromise |
| **Probability** | High *(physical threat in field is real)* |
| **Severity** | Critical |
| **Required validation** | Lab exercise on spare hardware: without FDE passphrase, data must be unreadable |
| **Expected mitigation** | Mandatory LUKS FDE; encrypted backups; theft playbook; unique secrets |

---

### BAK-01 — Backup theft

| Field | Content |
|-------|---------|
| **Objective** | Steal `clinic-node-*.sql.gz` or cloud snapshots |
| **Attack scenario** | Copy from `data/backups`, USB, NAS, mispermissioned share; decrypt if weak/no encryption |
| **Expected impact** | Full historical PHI disclosure |
| **Probability** | High |
| **Severity** | Critical |
| **Required validation** | Confirm backup ciphertext; ACL tests; off-box copy chain |
| **Expected mitigation** | Encrypt-at-rest backups; immutable/offline copies; strict ACLs |

---

### SYNC-01 — Sync manipulation / forgery

| Field | Content |
|-------|---------|
| **Objective** | Inject, alter, or suppress synchronized clinical events |
| **Attack scenario** | Replay old `event_id`s; forge ingest with stolen/guessed `X-Sync-Token`; change `clinic_id` in envelope; drop events (DoS integrity); create version conflicts deliberately |
| **Expected impact** | Poisoned cloud/node records; silent data loss |
| **Probability** | Medium |
| **Severity** | Critical |
| **Required validation** | Replay, wrong-token, cross-clinic envelope tests; conflict audit |
| **Expected mitigation** | Strong service auth (mTLS/JWT); idempotency; binding checks |

---

### LIC-01 — License forgery

| Field | Content |
|-------|---------|
| **Objective** | Create valid-looking licenses without authorization |
| **Attack scenario** | If HMAC secret equals `JWT_SECRET` or leaks, forge `clinic_id`/`node_id`/expiry; import via license API; extend expired nodes |
| **Expected impact** | Unauthorized nodes; bypass of admin enforcement |
| **Probability** | Medium |
| **Severity** | Critical *(ops integrity)* / High for care path (care continues by design) |
| **Required validation** | Forged signature must fail; node mismatch must fail |
| **Expected mitigation** | Asymmetric license signing; unique secrets; revocation |

---

### REPLAY-01 — Replay attacks

| Field | Content |
|-------|---------|
| **Objective** | Re-submit captured requests for duplicate clinical/financial effect |
| **Attack scenario** | Replay payment, dispense, patient create, sync push without idempotency keys |
| **Expected impact** | Duplicate charges, stock errors, duplicate patients |
| **Probability** | Medium |
| **Severity** | High |
| **Required validation** | Replay identical requests; expect safe no-ops with same client request id |
| **Expected mitigation** | Idempotency keys on all creates/payments |

---

### MITM-01 — Man-in-the-middle on clinic LAN

| Field | Content |
|-------|---------|
| **Objective** | Intercept staff credentials and PHI in transit |
| **Attack scenario** | ARP spoof; present attacker cert if users click through warnings; rogue AP “Clinique-WiFi”; intercept HTTP if redirect fails |
| **Expected impact** | Credential + PHI interception |
| **Probability** | Medium |
| **Severity** | Critical |
| **Required validation** | Confirm HSTS/redirect; train against cert bypass; test rogue AP |
| **Expected mitigation** | Proper CA trust; no click-through; network controls; optional mTLS |

---

### DEP-01 — Malicious dependency

| Field | Content |
|-------|---------|
| **Objective** | Execute attacker code in build or runtime via package ecosystem |
| **Attack scenario** | Typosquat package name; compromise maintainer; malicious postinstall; poisoned transitive dep |
| **Expected impact** | Backdoor in API/SPA; secret exfil from CI |
| **Probability** | Low |
| **Severity** | Critical |
| **Required validation** | Lockfile audit; install with ignore-scripts where possible; SCA tools |
| **Expected mitigation** | Pin versions; SCA gates; vendor critical libs |

---

### CI-01 — Supply-chain / CI-CD compromise

| Field | Content |
|-------|---------|
| **Objective** | Push malicious build to Railway/Vercel |
| **Attack scenario** | Steal GitHub Actions secrets; modify workflow; trojan Dockerfile; replace release artifact |
| **Expected impact** | Trusted malicious production deploy |
| **Probability** | Low |
| **Severity** | Critical |
| **Required validation** | Review workflow permissions; secret scanning; branch protection tests |
| **Expected mitigation** | OIDC, least privilege, required reviews, signed releases |

---

### UPD-01 — Malicious update package

| Field | Content |
|-------|---------|
| **Objective** | Replace Clinic Node software with attacker build |
| **Attack scenario** | Craft `manifest.json` + valid `manifest.sig` if HMAC secret known; or bypass verification; interrupt update to leave mixed versions |
| **Expected impact** | Persistent node backdoor |
| **Probability** | Medium if secrets weak/shared |
| **Severity** | Critical |
| **Required validation** | Unsigned package refused; wrong sig refused; rollback path tested *(test env)* |
| **Expected mitigation** | Asymmetric signatures; digest pinning; audited apply |

---

### SEC-01 — Secrets exposure

| Field | Content |
|-------|---------|
| **Objective** | Obtain JWT/DB/license/update/sync secrets |
| **Attack scenario** | Search git history; CI logs; error messages; world-readable `.env`; screenshots; `ADMIN_CREDENTIALS.txt`; backup of env |
| **Expected impact** | Forgery of all trust material |
| **Probability** | Medium |
| **Severity** | Critical |
| **Required validation** | Secret scanners; filesystem permission audit; history rewrite check |
| **Expected mitigation** | Secret manager; unique secrets; rotation runbooks |

---

### RAN-01 — Ransomware scenario

| Field | Content |
|-------|---------|
| **Objective** | Encrypt clinic systems and backups to halt care and extort |
| **Attack scenario** | Phish admin workstation → lateral to mini-PC; encrypt Docker volumes and `data/backups`; delete snapshots if accessible |
| **Expected impact** | Clinic downtime; potential permanent PHI loss |
| **Probability** | Medium |
| **Severity** | Critical |
| **Required validation** | *(Tabletop + lab only)* Prove offline immutable backup exists and restores |
| **Expected mitigation** | Offline/immutable backups; EDR; least privilege; IR playbook |

---

### DOS-01 — Denial of service

| Field | Content |
|-------|---------|
| **Objective** | Deny clinical access during peak hours |
| **Attack scenario** | Flood login; heavy PDF/report generation; fill disk with uploads/backups; DB connection exhaustion; nginx flood |
| **Expected impact** | Care disruption (patient safety risk) |
| **Probability** | High |
| **Severity** | High |
| **Required validation** | Rate limit efficacy; resource quotas; disk watermarks |
| **Expected mitigation** | Rate limits; WAF; quotas; monitoring |

---

### MED-01 — Medical record tampering

| Field | Content |
|-------|---------|
| **Objective** | Alter diagnosis, lab validation, prescriptions, vitals undetected |
| **Attack scenario** | As compromised doctor/lab account, change validated results; backdate; delete and recreate; race concurrent edits |
| **Expected impact** | Patient harm; legal liability; fraud |
| **Probability** | Medium |
| **Severity** | Critical |
| **Required validation** | Amend workflows leave audit; validated results immutability tests |
| **Expected mitigation** | Immutable validated artifacts; amend-with-reason; dual control for critical changes |

---

### AUD-01 — Audit log tampering

| Field | Content |
|-------|---------|
| **Objective** | Cover tracks after abuse |
| **Attack scenario** | DELETE/UPDATE `clinical_audit_logs` / sync audit via SQL if DB access; flood logs; disable logging paths |
| **Expected impact** | Undetectable insider crime |
| **Probability** | Medium *(with DB access)* |
| **Severity** | High |
| **Required validation** | App role cannot truncate audit tables; integrity checks |
| **Expected mitigation** | Append-only permissions; external log shipping; hash chains |

---

## 3. Environment-specific test tracks

### Track A — External cloud (Vercel + Railway)

Focus: AUTH-*, AUTHZ-*, JWT-*, XSS-*, SQL-*, UPLOAD-*, PDF-*, FAST-*, SSRF-*, DOS-*, VERC-*, RWY-*, DEP-*, CI-*, SEC-*.

### Track B — Offline Clinic Node + LAN

Focus: NODE-*, LAN-*, MITM-*, PHYS-*, BAK-*, SYNC-*, LIC-*, UPD-*, DOCKER-*, PG-*, CMD-*, RAN-*, DOS-*.

### Track C — Insider / clinical integrity

Focus: INS-*, MED-*, AUD-*, AUTHZ-02, REPLAY-01, BAK-01 (insider copy).

### Track D — Physical & disaster

Focus: PHYS-01, BAK-01, RAN-01 (lab hardware only).

---

## 4. Proposed execution waves (roadmap)

| Wave | Name | Attacks (IDs) | Goal |
|------|------|---------------|------|
| **W0** | Recon & mapping | Surface inventory, OpenAPI, port scan, role map | Build accurate attack graph |
| **W1** | Identity & access | AUTH-01..03, AUTHZ-01..02, JWT-01..02, SESS-01 | Prove account/tenancy breakers |
| **W2** | Injection & client | SQL-01, XSS-02, CSRF-01, SSRF-01, CMD-01 | Classic web/app bugs |
| **W3** | Data channels | UPLOAD-01, PDF-01, MED-01, REPLAY-01 | PHI integrity/exfil paths |
| **W4** | Cloud platform | FAST-01, RWY-01, VERC-01, SEC-01, DEP-01, CI-01 | Hosting & supply chain |
| **W5** | Node & LAN | NODE-01, LAN-01, MITM-01, DOCKER-01, PG-01 | Local compromise |
| **W6** | Trust planes | SYNC-01, LIC-01, UPD-01 | Forge the control plane |
| **W7** | Physical/DR lab | PHYS-01, BAK-01, RAN-01 (tabletop+lab) | Theft & ransomware resilience |
| **W8** | Abuse & availability | INS-01, AUD-01, DOS-01 | Insider + uptime |

**Exit criterion per wave:** Each attack marked Pass (exploited), Fail (blocked), or N/A — with evidence artifacts — before claiming that wave complete.

---

## 5. Evidence requirements (when testing is later authorized)

For each attempted attack, store:

1. Timestamp, operator, environment (staging/prod/lab)  
2. Exact request/response or physical steps (redact live PHI)  
3. Screenshots / logs  
4. Result: **Exploited / Partially / Blocked**  
5. Risk confirmation or downgrade  
6. Link to ticket (remediation is a **later** phase — out of scope here)

---

## 6. Explicit non-goals of this phase

- No exploitation against production without RoE  
- No source code changes  
- No “quick fixes”  
- No architecture redesign in this document beyond one-line expected mitigations  
- Offline V1 feature development remains frozen  

---

## 7. Document control

| Field | Value |
|-------|-------|
| Title | Santé Guinée — Official Penetration Testing Plan |
| Version | 1.0 |
| Date | 2026-07-29 |
| Author role | Senior Red Team Security Engineer |
| Companion | `docs/SECURITY_ARCHITECTURE.md` |
| Next authorized phase (future) | Execute Wave W0–W1 under signed RoE on staging |

---

*End of Penetration Testing Plan. Attack planning only — no implementation.*
