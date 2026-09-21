# Santé Guinée — Security Architecture Program

**Document type:** Security Architecture (design only)  
**Classification:** Internal — Confidential  
**Audience:** Product leadership, engineering, DevOps, pilot clinic operators, future auditors  
**Status:** Architecture baseline — **no implementation in this workstream yet**  
**Related frozen workstream:** Offline V1 Clinic Node (bug-fix only unless pilot-reported)  
**Stack in scope:** FastAPI backend, PostgreSQL, Docker, Railway (API), Vercel (SPA), Offline Clinic Node (LAN appliance)

---

## 0. Purpose and principles

### 0.1 Purpose

Define a production-grade security program for Santé Guinée suitable for **sensitive medical data** (PHI / données de santé) across:

1. **Cloud production** — Vercel frontend + Railway API + managed PostgreSQL  
2. **Offline Clinic Node** — local mini-PC appliance (Postgres + API + SPA + HTTPS proxy)  
3. **Synchronization / licensing / updates** between cloud and nodes (where enabled)  
4. **People, process, and physical** controls around Guinean clinic operations  

This document is **architecture only**. It does not change code, infrastructure, or configurations.

### 0.2 Security principles

| Principle | Meaning for Santé Guinée |
|-----------|--------------------------|
| **Confidentiality** | Medical data accessible only to authorized clinic roles for legitimate care |
| **Integrity** | Clinical records cannot be silently altered; changes are attributable |
| **Availability** | Care continues during outages; ransomware and disk failure do not end the clinic day |
| **Least privilege** | Roles get minimum permissions; platform ≠ clinic_admin ≠ nurse |
| **Defense in depth** | Edge TLS + app authz + DB controls + host hardening + backups |
| **Care continuity** | Security controls must not block emergency clinical care when license/ops degrade |
| **Auditability** | Who did what, to which patient/clinic, when, from where |
| **Zero trust on WAN** | Internet-facing surfaces assume hostile clients; LAN nodes assume physical risk |
| **Separation of planes** | Cloud production packaging ≠ Clinic Node appliance packaging |

### 0.3 Trust boundaries (high level)

```
┌──────────────────────────── TRUST BOUNDARY: Internet ────────────────────────────┐
│  Patients / staff browsers  →  Vercel (SPA)  →  Railway (FastAPI)  →  Postgres     │
│  Attacker surface: auth, APIs, uploads, CORS, secrets, supply chain                │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────── TRUST BOUNDARY: Clinic LAN ──────────────────────────┐
│  Workstations → HTTPS nginx (local PKI) → FastAPI → local Postgres                 │
│  Attacker surface: stolen mini-PC, rogue Wi-Fi, insider USB, ransomware, backups  │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────── TRUST BOUNDARY: Ops / Sync (optional) ────────────────┐
│  Node outbox ↔ Cloud ingest (token/HMAC) · License tokens · Signed updates         │
│  Attacker surface: replay, MITM, forged license, malicious update package          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 0.4 How to read each section

Every section below uses the same structure:

- **Current risks** — based on today’s known posture (JWT sessions, RBAC gaps, local PKI, HMAC secrets, etc.)  
- **Recommended architecture** — target design  
- **Expected protections** — what the design prevents or detects  
- **Validation strategy** — how we prove it works (tests, reviews, drills, pen tests)

---

## 1. Threat model

### 1.1 Assets

| Asset | Sensitivity | Where it lives |
|-------|-------------|----------------|
| Patient demographics & clinical notes | Critical PHI | Postgres (cloud + node) |
| Lab results, prescriptions, imaging reports | Critical PHI | Postgres + generated PDFs |
| Attachments / photos | Critical PHI | `uploads/secure` (+ optional Fernet) |
| Staff credentials & JWTs | High | DB hashes; browser sessionStorage; Authorization headers |
| Billing / cashier records | High (financial + care) | Postgres |
| Audit logs | High (integrity) | `clinical_audit_logs` (+ future SIEM) |
| License / update signing keys | Critical secrets | Env / secret store |
| Backups (`.sql.gz`) | Critical PHI at rest | Node `data/backups`, cloud snapshots |
| PKI private keys (clinic CA/server) | Critical | Node `data/pki/` |

### 1.2 Actors

| Actor | Motivation |
|-------|------------|
| External attacker (internet) | Credential stuffing, API abuse, RCE via deps, data theft |
| Opportunistic ransomware | Encrypt DB/backups/volumes for payment |
| Malicious or coerced insider | Exfiltrate PHI, alter records, cover tracks |
| Compromised workstation | Steal JWT, upload malware, keylog |
| Physical thief of mini-PC | Offline dump of Postgres + backups + keys |
| Supply-chain adversary | Malicious npm/PyPI package or forged update |
| Curious third party on clinic Wi-Fi | Sniff / MITM if TLS weak |

### 1.3 Current risks

- Broad attack surface: public SPA + API; clinic LAN with self-signed trust model  
- Stateless JWT theft equals session theft until expiry  
- RBAC matrix incomplete for some roles (`nurse` / `pev_agent` vs constraints / permission maps) historically observed  
- Offline node concentrates PHI + keys + backups on one physical device  
- Sync/license/update currently rely on shared-secret HMAC patterns (symmetric trust)  

### 1.4 Recommended architecture

Adopt **STRIDE + healthcare misuse cases** as the standing threat model, reviewed quarterly:

| STRIDE | Healthcare focus |
|--------|------------------|
| Spoofing | Stolen staff accounts, forged licenses/updates |
| Tampering | Altered lab results, prescription forgery |
| Repudiation | Missing or incomplete clinical audit trails |
| Information disclosure | PHI export, backup theft, verbose errors |
| Denial of service | Login flooding, DB saturation, ransomware |
| Elevation of privilege | Patient → staff, receptionist → clinic_admin |

Maintain a living **threat register** with owner, severity, residual risk, and control mapping.

### 1.5 Expected protections

Documented threat coverage; no major asset without at least one preventive and one detective control.

### 1.6 Validation strategy

- Annual threat-model workshop (eng + clinic ops)  
- Map each critical asset → controls → test evidence  
- Pen-test scope derived from this threat model (Section 35)

---

## 2. Security architecture (system view)

### 2.1 Current risks

- Security controls are distributed across app code, edge proxies, and env vars without a single control catalog  
- Cloud and Offline Node share application code but have different trust models (not always explicitly documented in one place)  

### 2.2 Recommended architecture

**Layered control planes:**

1. **Identity plane** — authentication, MFA (target), password policy, session lifecycle  
2. **Authorization plane** — RBAC + clinic tenancy + object-level checks  
3. **Application plane** — FastAPI hardening, input validation, upload/PDF controls  
4. **Data plane** — Postgres roles, encryption at rest, backup encryption, PHI minimization  
5. **Edge plane** — TLS, WAF/rate limits, Trusted Host, CORS allowlists  
6. **Runtime plane** — Docker least privilege, Railway/Vercel config, host hardening  
7. **Ops plane** — secrets, updates, sync, licensing, monitoring, IR  

**Deployment isolation rule:** Clinic Node packaging (`deploy/clinic-node/`) must remain separable from cloud Railway/Vercel deploy paths so a node compromise does not imply cloud secret compromise, and vice versa.

### 2.3 Expected protections

Clear ownership of controls; reduced blast radius between cloud and offline; auditable architecture decisions.

### 2.4 Validation strategy

Architecture review gate before each major release; ADR log for security decisions; control matrix spreadsheet linked to this document.

---

## 3. Authentication

### 3.1 Current risks

- Password + JWT Bearer only (no MFA)  
- JWT in browser `sessionStorage` (XSS → token theft)  
- Shared HS256 secret (`SECRET_KEY` / `JWT_SECRET`) for all tokens  
- Clinic-node admin bootstrap passwords must be rotated carefully  

### 3.2 Recommended architecture

| Control | Target design |
|---------|---------------|
| Primary auth | Email + password with server-side bcrypt (or Argon2id upgrade path) |
| MFA | TOTP or WebAuthn for `clinic_admin`, `platform_*`, cashier (phase 1); all clinical staff (phase 2) |
| Token model | Short-lived access JWT (≤15–30 min) + rotating refresh tokens (server-side revocation table) |
| Algorithm | Prefer asymmetric signing (RS256/ES256) for cloud; node may keep HS256 with unique per-node secret |
| Lockout | Progressive delay + account lock after N failures; alert on burst |
| Bootstrap | One-time install secrets; forced `must_change_password` |

### 3.3 Expected protections

Stolen password alone insufficient for privileged roles; stolen access token has short window; refresh can be revoked.

### 3.4 Validation strategy

- Auth unit/integration tests (login, lockout, must_change, refresh revoke)  
- Browser E2E for password change gates  
- Periodic credential-stuffing simulation against staging  

---

## 4. Authorization

### 4.1 Current risks

- Role checks exist (`assert_role`, `require_roles`, `ROLE_PERMISSIONS`) but permission coverage is uneven across modules  
- Object-level authorization (patient belongs to caller’s clinic) must be consistently applied on every path  
- Platform roles must never silently fall through to clinic data without explicit elevation rules  

### 4.2 Recommended architecture

**Two-layer authorization:**

1. **Role gate** — endpoint requires one of an allowlist of roles  
2. **Tenancy gate** — `clinic_id` of resource == caller’s clinic (except explicitly audited platform break-glass)  

Introduce a single `authorize(action, resource)` helper used by all clinical routers; ban ad-hoc role string lists for new endpoints.

Break-glass platform access: time-boxed, dual-control, fully audited.

### 4.3 Expected protections

Cross-clinic PHI leakage blocked; privilege escalation paths reduced; platform actions attributable.

### 4.4 Validation strategy

- Matrix tests: every role × every sensitive endpoint (allow/deny)  
- Negative tests for cross-`clinic_id` IDOR  
- Static check that new routes call authorize helper  

---

## 5. RBAC verification

### 5.1 Current risks

- Historical mismatch: application role set includes `nurse` / `pev_agent` while some Alembic CHECKs lagged  
- `ROLE_PERMISSIONS` may omit roles that exist in `core/roles.py`  
- Soft E2E asserts can hide permission holes  

### 5.2 Recommended architecture

**Single source of truth:**

- One `Role` enum / table driven from `core/roles.py`  
- DB CHECK constraint generated from the same list  
- `ROLE_PERMISSIONS` must include every role (even if empty set is explicit)  
- CI job fails if role sets diverge (app ↔ migration ↔ frontend route guards)  

RBAC certification pack: spreadsheet of role → modules → CRUD → evidence test IDs.

### 5.3 Expected protections

No “ghost roles”; no role that can log in but bypass documented permissions; migrations cannot drift.

### 5.4 Validation strategy

- CI consistency test for roles  
- Full RBAC matrix automated suite on every release  
- Manual review when adding a role  

---

## 6. API security

### 6.1 Current risks

- Public API surface behind JWT; misconfigured CORS or Trusted Host can widen exposure  
- Verbose errors may leak internals if not sanitized  
- Unauthenticated ingest/sync endpoints must never be open without strong tokens  

### 6.2 Recommended architecture

| Control | Design |
|---------|--------|
| TLS | Terminate at Railway / Vercel / clinic nginx; HSTS where applicable |
| CORS | Explicit allowlist of production origins only; no `*` with credentials |
| Trusted hosts | Strict allowlist matching deploy domains |
| Rate limiting | Per-IP + per-account on auth and heavy endpoints |
| Input validation | Pydantic models everywhere; reject unknown fields on sensitive bodies |
| Output | Envelope errors without stack traces in production |
| Idempotency | `X-Client-Request-Id` for clinical creates (sync-safe) |
| Versioning | Stable `/api` contract; deprecate carefully |

### 6.3 Expected protections

Reduced abuse bandwidth; blocked cross-origin token theft via CORS; safer error disclosure.

### 6.4 Validation strategy

- Security regression suite for CORS/TrustedHost  
- Fuzz critical POST bodies  
- Load + rate-limit tests on `/auth/login*`  

---

## 7. FastAPI security

### 7.1 Current risks

- Docs (`/docs`, OpenAPI) disabled in production when configured — must remain so  
- Dependency injection mistakes can skip `Depends(get_current_user)`  
- Middleware order matters (license, proxy headers, CORS)  

### 7.2 Recommended architecture

- Default-deny route pattern: authenticated unless explicitly marked public  
- Lint/CI: fail if router function lacks auth dependency (except allowlisted public paths)  
- Disable OpenAPI in production and clinic-node unless break-glass flag  
- Central exception handlers; no `detail=str(exc)` for unexpected errors  
- Background tasks inherit security context carefully (no PHI in logs)  

### 7.3 Expected protections

Fewer accidental public endpoints; consistent authn/z; reduced information leakage.

### 7.4 Validation strategy

- OpenAPI path inventory vs public allowlist  
- Middleware order review checklist  
- Dependency injection unit tests  

---

## 8. PostgreSQL security

### 8.1 Current risks

- Application typically uses a privileged DB user (broad DML/DDL)  
- Backups are full logical dumps (high value if stolen)  
- Clinic-node Postgres may bind on host network in fallback mode  

### 8.2 Recommended architecture

| Control | Design |
|---------|--------|
| Roles | Separate `app_rw`, `migrator`, `backup_ro` roles |
| Network | Cloud: private networking only; Node: bind to localhost / docker network, never public 5432 |
| TLS to DB | Require SSL for cloud connections |
| Encryption at rest | Cloud provider volume encryption; node full-disk encryption (LUKS) mandatory |
| Least privilege | App role without `SUPERUSER` / without `CREATE` in production after migrate |
| Extensions | Allowlist only |
| Row awareness | Enforce `clinic_id` in queries; consider RLS for defense in depth on critical tables |

### 8.3 Expected protections

Stolen app credentials cannot administer DB; network scanners cannot reach Postgres; disk theft without FDE fails.

### 8.4 Validation strategy

- `pg_hba` / network policy review  
- Role privilege audit query in CI against staging  
- Attempt external connect to 5432 must fail  

---

## 9. Docker security

### 9.1 Current risks

- Containers may run as root by default in images  
- Host-network mode (CI fallback) expands blast radius  
- Docker socket exposure would be catastrophic if mounted into app containers  

### 9.2 Recommended architecture

- Non-root users in backend/frontend images  
- Read-only root filesystem where feasible; explicit writable volumes for uploads/logs  
- Drop Linux capabilities; no `--privileged`  
- No docker.sock in application containers  
- Prefer bridge networking for production Clinic Node; document host-network as **lab-only**  
- Image scanning in CI (Trivy/Grype) gate on Critical/High  
- Pin base image digests  

### 9.3 Expected protections

Container escape hardness; reduced lateral movement; supply-chain visibility on images.

### 9.4 Validation strategy

- CIS Docker benchmark on mini-PC  
- CI image scan reports archived  
- Compose review: no privileged / sock mounts  

---

## 10. Railway security

### 10.1 Current risks

- Shared platform responsibility; mis-set env vars or public networking mistakes  
- Deploy tokens in GitHub Actions if over-scoped  

### 10.2 Recommended architecture

- Private DB / internal networking for Postgres  
- Secrets only in Railway variables (not in git)  
- Least-privilege Railway/GitHub deploy tokens; rotate on staff changes  
- Production `ENVIRONMENT=production`, docs disabled, strong `JWT_SECRET`/`SECRET_KEY`  
- Restrict outbound egress if platform supports (limit SSRF/exfil)  
- Separate staging vs production projects  

### 10.3 Expected protections

Credential leakage limited; staging data not mixed with production; deploy path auditable.

### 10.4 Validation strategy

- Railway config checklist per release  
- Secret scanning on repo + Actions logs policy  
- Staging isolation proof (different DB + secrets)  

---

## 11. Vercel security

### 11.1 Current risks

- SPA holds JWTs; XSS is high impact  
- Preview deployments may point at wrong API if env misconfigured  
- Legacy frontend hostnames historically caused confusion (canonical URL discipline required)  

### 11.2 Recommended architecture

- Strict Content-Security-Policy (default-src, connect-src to API only)  
- Security headers: CSP, HSTS (via Vercel), X-Content-Type-Options, Referrer-Policy, Frame-Ancestors none  
- Production project only for PHI workflows; previews use staging API never production  
- No secrets in `VITE_*` except public config  
- Canonical frontend URL enforcement; block legacy hosts  

### 11.3 Expected protections

XSS blast radius reduced; clickjacking blocked; preview cannot poison production data.

### 11.4 Validation strategy

- Header scan (securityheaders / Mozilla Observatory)  
- CSP report-only then enforce  
- Preview env audit  

---

## 12. Offline Clinic Node security

### 12.1 Current risks

- Concentrated PHI + keys + backups on one device  
- Local CA must be trusted on workstations (social-engineering risk if users install wrong CA)  
- Sync/license/update secrets on the node  
- Host-network fallback used in constrained environments  

### 12.2 Recommended architecture

**Node security profile (mandatory for production pilots):**

1. Dedicated mini-PC + UPS; no shared personal use  
2. Full-disk encryption (LUKS) + strong boot password  
3. Bridge Docker networking; firewall allow only 80/443 (and SSH from admin VLAN)  
4. Unique per-node `JWT_SECRET`, license secret, update secret, sync token  
5. Local PKI with documented CA trust procedure; never email private keys  
6. Admin workstation separate from clinical kiosks where possible  
7. Offline-first care continuity policy documented (license expired ≠ block care)  
8. Physical lock / cable lock / restricted server room or cabinet  

### 12.3 Expected protections

Stolen powered-off disk unreadable; LAN exposure minimized; node compromise does not yield cloud master secrets if secrets are unique.

### 12.4 Validation strategy

- Field hardening checklist signed by installer  
- Port scan from clinic Wi-Fi  
- Verify FDE before go-live  
- Simulate license expiry → clinical path still works; admin sync blocked  

---

## 13. Local server (mini-PC OS) security

### 13.1 Current risks

- Unpatched OS, default SSH, shared sudo, USB autorun  

### 13.2 Recommended architecture

- Ubuntu LTS (or equivalent) minimal install  
- Unattended security updates for OS packages  
- SSH: key-only, non-default user, fail2ban, allowlist admin IPs if WAN SSH exists (prefer no WAN SSH)  
- Disable unused services; no GUI on server if possible  
- USB storage policy: deny by default or mount noexec  
- Separate admin account vs service accounts  

### 13.3 Expected protections

Reduced remote takeover; ransomware less able to auto-execute from USB.

### 13.4 Validation strategy

- CIS Level 1 benchmark  
- SSH config audit  
- Patch currency report monthly  

---

## 14. Secrets management

### 14.1 Current risks

- Secrets primarily in `.env` / platform env vars  
- Multiple secrets may fall back to the same `JWT_SECRET` (license/update)  
- Admin credential files on disk during install  

### 14.2 Recommended architecture

| Environment | Secret store |
|-------------|--------------|
| Railway | Platform secrets + optional Vault/Doppler later |
| Vercel | Project env (non-secret public only in `VITE_*`) |
| Clinic Node | Root-owned `.env` mode 600; consider `sops`/age-encrypted secrets at rest |
| CI | Short-lived OIDC where possible; no long-lived PATs in logs |

**Rules:** unique secrets per environment and per node; no secret reuse across license/update/JWT if avoidable; rotation runbooks; never commit `.env` / `data/`.

### 14.3 Expected protections

Reduced blast radius of a single leak; faster rotation; clearer ownership.

### 14.4 Validation strategy

- `gitleaks` / `trufflehog` in CI  
- Secret inventory spreadsheet  
- Rotation drill annually  

---

## 15. Encryption

### 15.1 Current risks

- TLS in transit at edges; DB volume encryption depends on provider/host  
- Attachment encryption optional via `ATTACHMENT_ENCRYPTION_KEY`  
- Backups may be plaintext gzip SQL  

### 15.2 Recommended architecture

| Data state | Control |
|------------|---------|
| In transit | TLS 1.2+ everywhere (cloud + LAN HTTPS) |
| At rest (disk) | Cloud CMEK/provider encryption; node LUKS |
| At rest (attachments) | Fernet/AES-GCM mandatory for PHI files |
| At rest (backups) | Encrypt dumps (age/GPG) before off-box copy |
| Application secrets | Never store plaintext passwords (bcrypt/Argon2id) |

Key hierarchy: separate DEKs for attachments vs backup encryption vs token signing.

### 15.3 Expected protections

Intercepted traffic useless; stolen disks/backups useless without keys.

### 15.4 Validation strategy

- TLS scan (ssl labs / testssl)  
- Verify LUKS and backup ciphertext samples  
- Key-access audit  

---

## 16. TLS

### 16.1 Current risks

- Cloud TLS handled by platform  
- Clinic Node uses locally generated certificates; browsers warn until CA trusted  
- HTTP→HTTPS redirect must be reliable  

### 16.2 Recommended architecture

- Cloud: platform certificates + HSTS  
- Node: private CA; install `ca-trust.crt` via documented IT procedure; prefer short-lived server certs with renewal script  
- Disable TLS 1.0/1.1; strong ciphers only  
- Consider mTLS later for sync channel between node and cloud  

### 16.3 Expected protections

Confidentiality on LAN and WAN; reduced downgrade attacks.

### 16.4 Validation strategy

- `testssl.sh` against cloud and node HTTPS ports  
- Confirm redirect and HSTS  
- Workstation trust procedure dry-run  

---

## 17. Certificate management

### 17.1 Current risks

- Local CA private key on the node (`data/pki/`) — theft = MITM capability on that LAN trust domain  
- Manual trust on each workstation  

### 17.2 Recommended architecture

- Protect CA key with filesystem permissions + FDE; offline CA ideal (generate on admin laptop, import only server cert to node) for higher assurance  
- Inventory of trusted workstations  
- Expiry monitoring for server certs  
- Revocation process if CA compromised (re-issue CA, re-trust fleet)  
- Never share CA key via WhatsApp/email  

### 17.3 Expected protections

Controlled trust; recoverable compromise story.

### 17.4 Validation strategy

- PKI runbook tabletop  
- File permission audit on `data/pki`  
- Cert expiry calendar  

---

## 18. Session management

### 18.1 Current risks

- Stateless JWT; logout is client-side unless token denylist exists  
- Long-lived tokens increase theft impact  

### 18.2 Recommended architecture

- Access token TTL short; refresh token rotating, hashed at rest, bindable to device fingerprint (soft)  
- Server-side logout revokes refresh + optional jti denylist for access  
- Idle timeout for clinical workstations (SPA)  
- Concurrent session policy for privileged roles (optional limit)  

### 18.3 Expected protections

Faster containment after theft; true logout.

### 18.4 Validation strategy

- Logout/revoke integration tests  
- TTL configuration review  
- Stolen-token simulation in staging  

---

## 19. Password policy

### 19.1 Current risks

- Server-side strength validation exists; staff may share passwords  
- Temp passwords on reset must force change (already a product pattern)  

### 19.2 Recommended architecture

- Minimum length ≥12; complexity or passphrase rules; block common passwords (denylist)  
- bcrypt cost factor reviewed (≥12) or migrate Argon2id  
- `must_change_password` mandatory for bootstrap, reset, and provisioning  
- No password in URLs or logs  
- Clinic-node: no email reset — admin-assisted reset only (already directionally true)  

### 19.3 Expected protections

Harder guessing; reduced shared-account risk when combined with MFA.

### 19.4 Validation strategy

- Password validator unit tests  
- Provisioning E2E for must_change  
- Periodic weak-hash audit (ensure bcrypt only)  

---

## 20. Audit logs

### 20.1 Current risks

- `clinical_audit_logs` used on many clinical paths but coverage may not be 100%  
- Ops sync has separate audit tables on Offline V1  
- Logs may lack immutable storage / SIEM forwarding  

### 20.2 Recommended architecture

**Mandatory audited events:** login success/failure, logout, password change, staff create/role change, patient create/view/export, lab validate, prescription dispense, payment, record amend/delete, backup/restore, license activate, sync push, update apply, break-glass access.

Properties: who, what, clinic_id, resource ids, IP, user-agent, timestamp, outcome.  
**No PHI payloads in logs** (IDs only).  
Ship to append-only store (cloud) / WORM volume (node); alert on gaps.

### 20.3 Expected protections

Forensics, repudiation resistance, insider deterrence.

### 20.4 Validation strategy

- Coverage map: endpoint → audit event  
- Tamper attempt on log table detected in staging  
- Quarterly log review drill  

---

## 21. Backup security

### 21.1 Current risks

- Node backups under `data/backups` as gzip SQL — high-value PHI if copied  
- Off-box copy discipline may be manual  

### 21.2 Recommended architecture

- Encrypt backups before leaving the server  
- Integrity: SHA-256 + verification after write  
- Retention + secure deletion of expired backups  
- Access: admin-only filesystem ACLs  
- 3-2-1 rule: 3 copies, 2 media, 1 off-site/offline  
- Never store backups on the same ransomware-reachable share without immutability  

### 21.3 Expected protections

Backup theft ≠ PHI disclosure; ransomware cannot encrypt all copies.

### 21.4 Validation strategy

- Restore drill monthly (already part of ops maturity)  
- Encryption proof (cannot gunzip without key)  
- Access control review  

---

## 22. Disaster recovery security

### 22.1 Current risks

- Restore is powerful and destructive; must be gated  
- DR without authz/audit becomes an insider attack vector  

### 22.2 Recommended architecture

- Restore requires dual control (two admins) or break-glass + ticket  
- Pre-restore snapshot always  
- Document RPO/RTO for cloud and node separately  
- DR runbooks include credential rotation after restore (assume compromise)  
- Test restores into isolated networks only  

### 22.3 Expected protections

Malicious restore prevented; recovery does not silently weaken security.

### 22.4 Validation strategy

- Tabletop + technical DR drill quarterly  
- Dual-control process audit  

---

## 23. Synchronization security

### 23.1 Current risks

- Sync ingest authenticated by shared `X-Sync-Token` / HMAC patterns  
- Outbox payloads must avoid unnecessary PHI or must be encrypted in transit end-to-end  
- Replay and duplicate delivery risks  

### 23.2 Recommended architecture

- mTLS or signed JWT service identity between node and cloud  
- Idempotency via `event_id` / `client_request_id` (already directionally present)  
- Encrypt sync payloads if channel is not exclusively private  
- Rate-limit ingest; reject unsigned/mis-bound clinic_id  
- Conflict resolution audited; no silent overwrite of clinical facts without policy  

### 23.3 Expected protections

Forged sync events rejected; duplicates harmless; conflicts attributable.

### 23.4 Validation strategy

- Replay attack tests  
- Wrong-token / wrong-clinic_id negatives  
- Conflict audit trail review  

---

## 24. Licensing security

### 24.1 Current risks

- HMAC-signed licenses with shared secret; secret theft allows forging  
- Care-safe expiry policy must not be confused with “no enforcement”  

### 24.2 Recommended architecture

- Prefer asymmetric license signing (cloud private key; node embeds public key)  
- Bind clinic_id + node_id + validity window  
- Grace period with warnings; expiry blocks **admin/sync/update**, not emergency care  
- Revocation list for stolen nodes (when online)  
- Secure issuance workflow (Owner-only)  

### 24.3 Expected protections

Unforgeable licenses without cloud private key; stolen node can be revoked when connectivity exists.

### 24.4 Validation strategy

- Forged license rejection tests  
- Node mismatch tests  
- Expiry behavior matrix (care vs admin)  

---

## 25. Update security

### 25.1 Current risks

- HMAC-signed manifests (symmetric); rollback exists conceptually  
- Malicious local package with stolen secret could apply  

### 25.2 Recommended architecture

- Asymmetric signatures (Ed25519) over manifest + image digests  
- Verify before load; refuse unsigned  
- Mandatory pre-update encrypted backup  
- Health gate + automatic rollback  
- Signed SBOM attached to release  
- Admin-only update apply; audited  

### 25.3 Expected protections

Supply-chain update attacks blocked without private signing key; failed updates recoverable.

### 25.4 Validation strategy

- Bad signature package must fail  
- Rollback drill  
- Release signing ceremony checklist  

---

## 26. Supply-chain security

### 26.1 Current risks

- PyPI + npm dependencies; Docker base images  
- GitHub Actions deploy pipeline  

### 26.2 Recommended architecture

- Lockfiles committed; dependabot/renovate with human review  
- Pin image digests  
- CI: `pip-audit` / `npm audit` / Trivy with severity gates  
- Verify GitHub Actions against known SHAs  
- Protect `main` with reviews + required checks  
- Disable risky install scripts where possible  

### 26.3 Expected protections

Faster detection of compromised packages; reproducible builds.

### 26.4 Validation strategy

- Weekly audit job artifacts  
- Branch protection settings review  
- Incident tabletop: malicious dependency  

---

## 27. Dependency management

### 27.1 Current risks

- Transitive vulnerabilities accumulate  

### 27.2 Recommended architecture

- Inventory of direct deps with owners  
- SLA: Critical fixes ≤7 days; High ≤30 days  
- Separate runtime vs dev dependencies  
- Avoid abandoned packages for crypto/auth  

### 27.3 Expected protections

Managed vulnerability backlog; fewer emergency patches.

### 27.4 Validation strategy

- Vulnerability burn-down metrics  
- License compliance scan  

---

## 28. File upload security

### 28.1 Current risks

- Attachments are sensitive; malware in uploads can target staff workstations on download  
- Public `/uploads` must remain blocked (already a design goal)  

### 28.2 Recommended architecture

- Authz on every download  
- Store outside web root (`uploads/secure`) with random keys  
- Allowlist MIME + extension; sniff content; size limits  
- Virus scan (ClamAV) asynchronously before download where feasible  
- Encrypt at rest  
- Access audit log (`attachment_access_log` pattern)  
- Never serve with user-controlled Content-Type unsafely  

### 28.3 Expected protections

No anonymous file fetch; reduced malware delivery; attributable access.

### 28.4 Validation strategy

- Path traversal / IDOR tests  
- Malicious file upload suite  
- Confirm `/uploads/*` → 404/403 at app and nginx  

---

## 29. PDF security

### 29.1 Current risks

- Generated clinical/billing PDFs contain PHI  
- Libraries historically sensitive to unsafe input / font issues  

### 29.2 Recommended architecture

- Generate PDFs server-side only from authorized data  
- No HTML→PDF from untrusted user HTML without sanitization  
- Temporary PDF files on encrypted volume; short-lived URLs or stream with auth  
- Watermark with clinic + user + timestamp for exported reports  
- Disable dangerous PDF features if using external renderers  

### 29.3 Expected protections

Fewer unauthorized PDF exfiltrations; safer generation pipeline.

### 29.4 Validation strategy

- Authz tests on PDF endpoints  
- Fuzz PDF inputs  
- Retention policy for generated files  

---

## 30. Medical data confidentiality

### 30.1 Current risks

- Multi-clinic tenancy errors = cross-patient/cross-clinic disclosure  
- Ops dashboards must remain PHI-free (Owner heartbeat model)  
- Exports and demos must not leak production PHI  

### 30.2 Recommended architecture

- Data classification: Public / Internal / PHI / PHI-Sensitive (HIV, etc. if applicable)  
- Minimization: APIs return only fields needed for the role  
- Masking in non-production (anonymized staging)  
- DLP mindset: block bulk export except audited roles  
- Separate demo cleanup tooling from production data paths  
- Privacy by design in sync payloads  

### 30.3 Expected protections

Reduced unnecessary PHI exposure; safer staging; clearer legal posture.

### 30.4 Validation strategy

- PHI field inventory  
- Staging data anonymization proof  
- Owner dashboard automated PHI-key scans (continue)  

---

## 31. OWASP Top 10 mapping

| OWASP | Current risk themes | Target controls |
|-------|---------------------|-----------------|
| A01 Broken Access Control | IDOR / RBAC gaps | Tenancy + RBAC matrix + CI |
| A02 Cryptographic failures | JWT HS256, backup plaintext | TLS, FDE, encrypted backups, stronger token crypto |
| A03 Injection | SQL via ORM mostly mitigated; still validate raw SQL paths | Parameterized only; ban string-built SQL |
| A04 Insecure design | Threat model incomplete historically | This architecture + reviews |
| A05 Security misconfiguration | Docs, CORS, host networking | Hardened baselines + scans |
| A06 Vulnerable components | Deps/images | Audit gates |
| A07 Auth failures | No MFA; JWT theft | MFA + short TTL + refresh revoke |
| A08 Software/data integrity | Update/license HMAC | Asymmetric signatures + SBOM |
| A09 Logging failures | Partial audit coverage | Mandatory event catalog + SIEM |
| A10 SSRF | Outbound URL fetches if any | Allowlist egress |

### Validation strategy

Annual OWASP-oriented assessment; map findings to backlog with SLAs.

---

## 32. Healthcare-specific attack scenarios

| Scenario | Attack path | Target controls |
|----------|-------------|-----------------|
| Prescription fraud | Alter Rx or dispense without order | RBAC + audit + inventory reconciliation |
| Lab result tampering | Change validated result | Immutable validate event + amend workflow with audit |
| Chart snooping | Staff views celebrity/neighbor record | Access audit + anomaly alerts |
| Insurance/billing fraud | Fake charges | Segregation cashier vs clinician + reports |
| Fake teleconsult | Impersonation | Strong auth + session binding (future) |
| Record deletion cover-up | Delete + wipe logs | Soft-delete + immutable logs |
| Cross-clinic curiosity | Platform/admin misuse | Break-glass + dual control |

### Validation strategy

Abuse-case test pack per release; chart access anomaly rules in monitoring.

---

## 33. Ransomware resilience

### 33.1 Current risks

- Single mini-PC can be encrypted including attached backup folders  
- Cloud account compromise could delete resources  

### 33.2 Recommended architecture

- Immutable / offline weekly backup (USB stored offsite, rotated)  
- Cloud snapshots with deletion protection / separate backup account  
- Least privilege OS users; no always-on domain admin  
- EDR on mini-PC if available  
- Documented rebuild-from-backup time objective  
- Separate credentials for backup storage  

### 33.3 Expected protections

Clinic can restore care within agreed RTO without paying ransom.

### 33.4 Validation strategy

- Quarterly ransomware tabletop  
- Restore from offline medium drill  
- Verify backups not reachable by app user account  

---

## 34. Insider threats

### 34.1 Current risks

- Privileged clinic_admin can reset passwords, export data, apply updates  
- Shared accounts defeat attribution  

### 34.2 Recommended architecture

- Named accounts only; no shared “nurse” logins  
- Dual control for: restore, bulk export, role elevation, license issue  
- Joiner-mover-leaver process within 24h  
- Monitor bulk reads / atypical hours  
- Clear sanctions policy communicated to staff  

### 34.3 Expected protections

Attribution; reduced silent exfiltration; faster offboarding.

### 34.4 Validation strategy

- Access reviews monthly  
- Offboarding checklist audit  
- Bulk-download alert tests  

---

## 35. Physical theft of the clinic server

### 35.1 Current risks

- Theft of mini-PC yields disks with Postgres data directory, backups, PKI, `.env` if not encrypted  

### 35.2 Recommended architecture

**Assume theft is possible.** Controls:

1. LUKS full-disk encryption (mandatory)  
2. No plaintext secrets on unlocked idle systems — auto-lock; short idle sudo  
3. Encrypted backups only off-box  
4. Asset tag + cable lock + restricted room  
5. Theft playbook: revoke node license, rotate cloud sync credentials, re-issue local CA if server cert CA was on device, notify leadership  
6. Spare cold device imaged for restore  

### 35.3 Expected protections

Thief gets ciphertext; clinic reconstitutes from offline backup; cloud trust material rotated.

### 35.4 Validation strategy

- Power-off disk extraction simulation (should fail without passphrase)  
- Theft tabletop with clocked response  

---

## 36. Security monitoring

### 36.1 Current risks

- Application logs exist; centralized alerting may be incomplete  
- Node may be offline → delayed detection  

### 36.2 Recommended architecture

| Signal | Action |
|--------|--------|
| Auth failures burst | Alert admin |
| Privilege elevation | Alert + ticket |
| Backup failure / missing daily backup | Alert |
| License invalid/expired | Warn clinic_admin |
| Sync dead-letter growth | Alert |
| Health endpoint down | Page on-call |
| Dependency Critical CVE | Security ticket |

Cloud: ship logs to managed logging.  
Node: local log retention + periodic heartbeat of **ops-only** metrics (no PHI) when online.

### 36.3 Expected protections

Hours-to-detect instead of weeks; backup gaps noticed same day.

### 36.4 Validation strategy

- Alert fire drills  
- Heartbeat loss test  
- Dashboard review weekly  

---

## 37. Incident response

### 37.1 Current risks

- Without a playbook, clinics improvise under stress  

### 37.2 Recommended architecture

**IR phases:** Prepare → Detect → Contain → Eradicate → Recover → Lessons.

**Severity levels:** SEV1 (PHI breach / ransomware) → SEV4 (minor).

**Playbooks (minimum):** account compromise, ransomware, stolen node, suspected data exfil, bad update, cloud outage.

**Contacts:** clinic lead, eng on-call, legal/privacy advisor, hosting support.

**Evidence handling:** preserve logs/backups; do not wipe before snapshot.

### 37.3 Expected protections

Faster containment; consistent communications; regulatory readiness.

### 37.4 Validation strategy

- Semi-annual tabletop  
- Post-incident reports required for SEV1–2  

---

## 38. Business continuity

### 38.1 Current risks

- Security incidents and outages both stop care if BC not planned  

### 38.2 Recommended architecture

- Paper fallback registers for SEV1 outages (aligned with field reality)  
- Offline Node designed to continue LAN care without internet  
- Cloud RPO/RTO documented  
- Cross-training two admins per clinic  
- UPS sizing for clean shutdown  

### 38.3 Expected protections

Patient care continues under degraded modes; data eventually reconciled.

### 38.4 Validation strategy

- BC drill combining paper + system restore  
- UPS power-loss test  

---

## 39. Penetration testing strategy

### 39.1 Current risks

- Automated unit/E2E ≠ adversarial testing  

### 39.2 Recommended architecture

| Cadence | Scope |
|---------|-------|
| Continuous | SAST, dependency scan, container scan, secret scan |
| Each major release | Internal authz/IDOR regression pack |
| Semi-annual | External pen test: Vercel + Railway API |
| Annual | Clinic Node physical+LAN assessment (on staging hardware) |
| After major auth change | Focused retest |

Rules of engagement: staging preferred; production only with written approval and PHI handling rules.  
Findings triage SLAs mirror dependency SLAs.

### 39.3 Expected protections

Independent verification of architecture claims.

### 39.4 Validation strategy

- Track open Critical/High to zero before calling a release “security-certified”  
- Retest verification evidence archived  

---

## 40. Program roadmap (architecture sequencing — not implementation)

Suggested order when the Security Hardening workstream is authorized to implement:

1. **Foundations** — secrets uniqueness, FDE mandate, backup encryption, RBAC single source of truth  
2. **Identity** — short-lived tokens + refresh revoke + MFA for admins  
3. **Tenancy hard guarantees** — systematic IDOR suite + authorize helper  
4. **Node physical & PKI** — offline CA pattern, theft playbook  
5. **Integrity** — asymmetric license/update signatures  
6. **Monitoring & IR** — alerts + playbooks + drills  
7. **External pen test** — certify production-grade claim  

Offline V1 remains **frozen** except pilot bug fixes during this program unless leadership explicitly unfreezes a security-blocking defect.

---

## 41. Acceptance criteria for “production-grade security”

Santé Guinée may claim production-grade security for medical data when:

1. Threat model reviewed and approved  
2. RBAC + tenancy matrix fully green in CI  
3. MFA enforced for privileged roles  
4. Backups encrypted + restore drill evidenced  
5. Clinic Node FDE + theft playbook evidenced  
6. Update/license signatures asymmetric (or formally accepted residual risk)  
7. Monitoring alerts proven  
8. IR/BC tabletops completed  
9. External pen test Critical/High closed or accepted with expiry  
10. This architecture document updated to match deployed reality  

Until then, this document is the **target architecture**, not a certification of current state.

---

## 42. Document control

| Field | Value |
|-------|-------|
| Title | Santé Guinée — Security Architecture Program |
| Version | 1.0 |
| Date | 2026-07-29 |
| Author role | Senior Healthcare Cybersecurity Architect (design engagement) |
| Implementation status | **Not started** — architecture only |
| Next step | Leadership review → prioritize roadmap items → separate implementation tickets |

---

*End of Security Architecture document. No application code, infrastructure changes, or refactors are authorized by this document alone.*
