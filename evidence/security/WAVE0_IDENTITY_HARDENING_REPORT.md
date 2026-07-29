# Santé Guinée — Security Wave 0 Report

**Wave:** 0 — Authentication & Identity Hardening  
**Status:** COMPLETE  
**Date:** 2026-07-29  
**Scope:** Authentication, Authorization (RBAC completeness), JWT, Sessions, Password security, Login security, Token security  

---

## 1. Implemented protections

| Area | Implementation |
|------|----------------|
| **JWT** | Short-lived access tokens (default **30 min**); claims include `jti`, `iat`, `tv` (token version); `SECRET_KEY` **or** `JWT_SECRET` accepted |
| **Refresh tokens** | Opaque rotating refresh tokens hashed at rest (`refresh_tokens`); family revoke on reuse; `/auth/refresh`, `/auth/logout` |
| **Access denylist** | Logout / password-change denylists access `jti` until expiry |
| **Token versioning** | Password change / admin reset bumps `token_version` and revokes all refresh tokens |
| **Login lockout** | Progressive soft throttle after 3 failures; hard lock after 5 (configurable); `Retry-After` |
| **Password policy** | Min **12** chars, upper+lower+digit, common-password denylist; bcrypt rounds default **12** |
| **must_change_password** | Enforced server-side (API blocked except `/auth/me`, change-password, logout, refresh, MFA setup); set on staff provisioning & admin password reset; frontend redirects |
| **RBAC** | `ROLE_PERMISSIONS` now includes **nurse**, **pev_agent**, **patient**; clinic ops roles updated |
| **MFA (TOTP)** | Optional enrollment (`/auth/mfa/setup|confirm|disable`); challenge on login when enabled; `MFA_REQUIRED_ROLES` ready (default empty for clinic UX) |
| **Frontend session** | Stores refresh token; silent refresh on 401; server logout; forced password-change gate |

---

## 2. Validation evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Wave 0 identity unit/integration | **43 passed** | `evidence/security/WAVE0_PYTEST_AUTH.txt` |
| Full backend pytest | **214 passed** | `evidence/security/WAVE0_PYTEST_FULL.txt` |
| Security validation script | See `scripts/deploy/validate_security_wave0.py` | run locally / CI |

### Security checks covered by tests

- Login issues refresh + short TTL + jti/iat/tv  
- Refresh rotation + reuse detection  
- Logout denylist  
- must_change_password API gate  
- Password change revokes old access token  
- Account lockout / soft throttle  
- Token version mismatch rejected  
- MFA challenge when enabled  
- Staff provisioning sets must_change_password  
- RBAC matrix covers all roles  
- Password policy unit tests  

---

## 3. Backward compatibility

- Existing short passwords still **login** (policy applies to new/changed passwords only)  
- Clients that ignore `refresh_token` continue to work until access TTL expires  
- MFA not enforced by default (`MFA_REQUIRED_ROLES` empty) — no clinic staff lockout  
- Access token default reduced 60→30 minutes (override with `ACCESS_TOKEN_EXPIRE_MINUTES`)  

---

## 4. Remaining risks (accepted for later waves)

| Risk | Severity | Notes |
|------|----------|-------|
| MFA not enforced for privileged roles by default | High | Set `MFA_REQUIRED_ROLES=platform_owner,platform_admin,clinic_admin,cashier` when ops ready |
| JWT still HS256 (not RS256/ES256) | Medium | Architecture prefers asymmetric for cloud — Wave N |
| Access token still in sessionStorage (XSS) | High | Mitigated by short TTL + refresh revoke; CSP/XSS wave next |
| No device binding on refresh | Medium | Soft fingerprint optional later |
| Tenancy/IDOR systematic authorize helper | Critical (Wave 1+) | Out of Wave 0 identity scope |
| Public doctor self-registration still open | Medium | Product decision; not closed in Wave 0 |

---

## 5. Ops checklist before production deploy

1. Set strong unique `SECRET_KEY` (and matching `JWT_SECRET` if used)  
2. Confirm `ACCESS_TOKEN_EXPIRE_MINUTES=30` (or 15)  
3. Run migrations / startup `ensure_security_wave0_identity_schema`  
4. Optionally enable `MFA_REQUIRED_ROLES` for platform admins after staff training  
5. Communicate password min-length 12 to clinic admins provisioning staff  

---

## 6. Verdict

**Security Wave 0 is COMPLETE.** All automated validations for this wave pass. Remaining risks are documented for subsequent hardening waves.
