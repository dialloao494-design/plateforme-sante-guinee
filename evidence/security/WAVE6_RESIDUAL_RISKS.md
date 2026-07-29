# Security Wave 6 — Residual Risks

**Status:** ACCEPTED FOR TRACKING  
After remediation, **no Critical/High EXPLOITED** findings remain. Residual items are PARTIAL mitigations or lab-only validations.

## PARTIAL (controls present, residual attack surface)

| ID | Severity | Residual risk | Recommended follow-up |
|----|----------|---------------|------------------------|
| JWT-01 | Critical | Encoding helper blocks HTML injection; residual SPA token-theft risk documented | Continue hardening per SECURITY_ARCHITECTURE |
| SSRF-01 | High | No public webhook fetch endpoint found on main surface; residual risk on reminder/teleconsult URL fields | Continue hardening per SECURITY_ARCHITECTURE |
| CMD-01 | Critical | {'shell_true_files': ['scripts/security/run_penetration_tests.py']} | Continue hardening per SECURITY_ARCHITECTURE |
| RWY-01 | Critical | Config review only in lab; private networking must be verified in Railway dashboard | Continue hardening per SECURITY_ARCHITECTURE |
| VERC-01 | High | Preview→prod API binding must be enforced in Vercel project settings | Continue hardening per SECURITY_ARCHITECTURE |
| DEP-01 | Critical | SCA gates (pip-audit) recommended in CI; lockfile present | Continue hardening per SECURITY_ARCHITECTURE |
| CI-01 | Critical | Branch protection and OIDC must be verified in GitHub settings | Continue hardening per SECURITY_ARCHITECTURE |

## N/A — requires lab hardware / signed RoE live test

| ID | Severity | Why deferred |
|----|----------|--------------|
| NODE-01 | Critical | Clinic Node package not on main; Wave4 controls required before lab live test |
| LAN-01 | Critical | Host-network Postgres bind must remain 127.0.0.1 when used |
| PHYS-01 | Critical | Physical FDE validation requires dedicated lab hardware (LUKS) |
| RAN-01 | Critical | Ransomware detonation forbidden on live clinics; offline immutable copies required |
| MITM-01 | Critical | LAN MITM requires clinic lab with rogue AP; HSTS/CSP headers shipped |

## Explicit residual themes

1. **JWT-01 / XSS-02** — SPA still stores Bearer tokens in `sessionStorage`; XSS remains high-impact. Prefer httpOnly cookies + CSRF **or** strict CSP + continued XSS elimination.  
2. **SSRF-01** — No public fetch endpoint found; reminder/teleconsult URL fields need allowlists when enabled.  
3. **PG-01 / NODE-01 / LAN-01** — Clinic Node package not fully on main; Wave 4 host-network/Postgres bind controls must be enforced before field deploy.  
4. **PHYS-01 / MITM-01 / RAN-01** — Require dedicated lab hardware / tabletop; FDE (LUKS), HSTS trust training, offline immutable backups.  
5. **DEP-01 / CI-01 / RWY-01 / VERC-01** — Platform settings (branch protection, preview envs, private DB) need continuous ops verification.  
6. **MED-01 / INS-01 / AUD-01 / REPLAY-01 (clinical)** — RBAC blocks obvious abuse; amend-with-reason, bulk-export anomaly detection, append-only DB roles, and payment idempotency remain product backlog.  
7. **Sync/License product APIs** — Security libraries ready; Offline V1 product routers remain frozen.

## Acceptance

Wave 6 exit criterion met: every approved attack executed with evidence; no critical vulnerability remains in **EXPLOITED** state.
