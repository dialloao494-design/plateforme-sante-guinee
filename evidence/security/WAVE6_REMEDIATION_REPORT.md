# Security Wave 6 — Complete Remediation Report

**Status:** COMPLETE  
**Branch:** `cursor/security-wave6-pentest-ab76`

## Remediation loop

| Finding | Initial posture (main) | Fix applied | Retest |
|---------|------------------------|-------------|--------|
| AUTH-01 Credential spray | No progressive lockout | Wave 0 `record_login_failure` / soft+hard lockout | BLOCKED |
| AUTH-02 Logout client-only | JWT valid after logout | Access jti denylist + refresh revoke on `/auth/logout` | BLOCKED |
| AUTH-03 must_change bypass | Flag stored, not enforced | `get_current_user` gate on non-auth routes | BLOCKED |
| AUTHZ-01 Cross-clinic IDOR | Partial baseline | Wave 1 patient/clinical tenancy checks | BLOCKED |
| AUTHZ-02 Priv-esc | Baseline RBAC gaps for nurse/pev | Wave 0 RBAC matrix expansion | BLOCKED |
| JWT-02 alg=none / forge | HS256 allowlist present | Confirmed reject `alg=none` + wrong key | BLOCKED |
| SESS-01 Concurrent JWT | No token version | `token_version` bump on password change | BLOCKED |
| BAK-01 Plaintext backups | No encrypt gate on main | Wave 5 Fernet backup + restore validation | BLOCKED |
| SYNC-01 / REPLAY-01 | Product sync frozen | Wave 5 HMAC envelopes + ReplayGuard | BLOCKED |
| UPD-01 Malicious update | Weak JWT fallback risk | Wave 5 signed manifests; JWT fallback refused | BLOCKED |
| DOCKER-01 Root container | Dockerfile ran as root | Wave 3 `appuser` + gosu drop; compose no docker.sock | BLOCKED |
| DOS-01 Auth flood | Partial limiter | SlowAPI middleware + lockout | BLOCKED |
| Password policy | 8-char min | Wave 0 ≥12 + complexity + common-password block | Enforced |
| Security headers | Missing middleware | `SecurityHeadersMiddleware` attached in `main.py` | Present |

## Code / package changes (Wave 6)

- Identity: `security.py`, `routers/auth.py`, `models/user.py`, `models/refresh_token.py`, `services/auth_session_service.py`, `services/mfa_service.py`, `core/password_policy.py`, `core/rbac.py`
- API: `core/authorize.py`, `core/input_validation.py`, `core/output_encoding.py`, `core/security_headers.py`, patient/clinical router tenancy
- Infra: `Dockerfile`, `scripts/docker/entrypoint-backend.sh`, `docker-compose*.yml`, `core/deploy_hardening.py`
- Documents: `core/attachment_malware.py` (+ policy/encryption modules)
- Clinic node helpers: `core/clinic_node_security.py`
- Sync/DR/Updates: `core/sync_security.py`, `core/backup_security.py`, `core/update_security.py`, `services/recovery_security_service.py`, `scripts/security/*`
- Harness: `scripts/security/run_penetration_tests.py`, `tests/test_security_wave6_pentest.py`

## Retest evidence

- `WAVE6 SMOKE` / harness: `EXPLOITED=0`, `critical_exploited=[]`
- Pytest: `tests/test_security_wave6_pentest.py`
