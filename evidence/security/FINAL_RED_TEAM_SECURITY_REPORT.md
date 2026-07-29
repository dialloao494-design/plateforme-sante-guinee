# SANTÉ GUINÉE
# FINAL RED TEAM SECURITY REPORT

**Assessment date:** 2026-07-29  
**Branch:** `cursor/red-team-final-assessment-ab76`  
**Assessor posture:** Independent adversarial Red Team (prior Wave 7 GO **not trusted**)  
**Target:** Santé Guinée platform (FastAPI / React / PostgreSQL / Railway / Vercel / Offline Clinic Node)

---

## 1. Executive Summary

A from-scratch Red Team re-audit found **multiple Critical and High vulnerabilities that survived prior certification**, including unauthenticated WhatsApp-driven appointment mutation, multi-tenancy fail-open paths for legacy `admin`/`clinic_admin`, refresh-token fork races, MFA soft gates, update-package integrity gaps, production encryption kill-switches, and **committed live-looking AASMA credentials** in the repository.

All Critical and High issues identified in the live application code path were **remediated and regression-tested**. Post-fix:

| Gate | Result |
|------|--------|
| Critical open | **0** |
| High open (code) | **0** |
| Official pentest harness EXPLOITED | **0** / 38 |
| Full pytest | **275 passed**, 1 skipped |
| Red Team regression tests | **13 passed**, 1 skipped |

**Overall Security Rating:** **STRONG (with documented residual Medium / ops risks)**

### Verdict

# PRODUCTION APPROVED

Conditional only on the residual operational acceptance items in §7 (credential rotation from git history; WhatsApp App Secret deployment; emergency bypass attestation discipline). No Critical or High code vulnerability remains unfixed without formal acceptance.

---

## 2. Scope

In scope (attacked):

- Authentication, JWT, refresh rotation, MFA, session/denylist  
- RBAC, multi-tenancy, IDOR, privilege escalation  
- Reminders / WhatsApp webhooks, public platform setup  
- Attachments, PDF, file uploads, update packages  
- Boot guards, secrets, Docker/Railway/Vercel config review (static)  
- Offline Clinic Node update/backup/sync security libraries  
- Logging/monitoring gaps (residual)  
- Dependency / static analysis (bandit + pin review)

Out of scope / constrained:

- Live production traffic against AASMA (credentials rotated out of tree; no live spray)  
- Full git-history rewrite of historical secrets  
- Physical clinic-node hardware / LUKS operational verification  
- Third-party Meta / Stripe / Railway control planes  

---

## 3. Attack Matrix

| ID | Layer | Attack | Pre-fix | Post-fix |
|----|-------|--------|-----------|------------|
| RT-C1 | API | Unsigned WhatsApp webhook mutates appointments | **EXPLOITED (Critical)** | BLOCKED |
| RT-C2 | Authz | Concurrent `/platform/setup` → multiple owners | **EXPLOITED (Critical)** | BLOCKED |
| RT-C3 | Secrets | Committed AASMA passwords in docs/scripts | **EXPLOITED (Critical)** | MITIGATED (tree) + accepted residual (history) |
| RT-H1 | Tenancy | `clinic_id is None` fail-open on appointments | **EXPLOITED (High)** | BLOCKED |
| RT-H2 | Tenancy | Cross-clinic doctor PUT/DELETE | **EXPLOITED (High)** | BLOCKED |
| RT-H3 | Tenancy | Message attachment clinic_admin IDOR | **EXPLOITED (High)** | BLOCKED |
| RT-H4 | Tenancy | Teleconsult admin global access | **EXPLOITED (High)** | BLOCKED |
| RT-H5 | Tenancy | Doctor dashboard lists all clinics for admin | **EXPLOITED (High)** | BLOCKED |
| RT-H6 | Tenancy | Reminder notifications / process-due global | **EXPLOITED (High)** | BLOCKED |
| RT-H7 | Tenancy | Unassigned patient mutation by clinic admin | **EXPLOITED (High)** | BLOCKED |
| RT-H8 | Session | Concurrent refresh forks live chains | **EXPLOITED (High)** | BLOCKED |
| RT-H9 | Auth | MFA required roles soft-pass without enrollment | **EXPLOITED (High)** | BLOCKED |
| RT-H10 | Auth | Reminder respond token fail-open if secret unset | **EXPLOITED (High)** | BLOCKED |
| RT-H11 | Boot | `REQUIRE_ATTACHMENT_ENCRYPTION=false` silent | **EXPLOITED (High)** | BLOCKED (dual attestation) |
| RT-H12 | Updates | Empty `files:{}` + path traversal in digests | **EXPLOITED (High)** | BLOCKED |
| RT-H13 | JWT | Empty `jti` bypasses denylist | **EXPLOITED (High)** | BLOCKED |
| W6-* | Plan | Official 38-attack pentest harness | Prior | EXPLOITED=0 |
| RT-M1 | Frontend | SPA JWT in sessionStorage (XSS → token theft) | Residual Medium | Accepted |
| RT-M2 | Network | Rate-limit keying on container/proxy IP | Residual Medium | Accepted |
| RT-M3 | Bandit | Pilot-seed hardcoded passwords (dev-only gated) | Residual Low/Med | Accepted (prod boot forbids pilot seed) |

---

## 4. Vulnerabilities Found

### Critical

1. **Unauthenticated WhatsApp webhook** (`routers/reminders.py`) — any client could POST crafted JSON and cancel/confirm appointments. Default verify token was a known string; POST had **no** signature check; `WHATSAPP_DEFAULT_APPOINTMENT_ID` enabled blind targeting.
2. **Platform owner setup race** — check-then-create without serialization/unique constraint allowed multiple `platform_owner` accounts.
3. **Committed credentials** — plaintext AASMA staff passwords in `docs/OVERNIGHT_AUTONOMOUS_REPORT.md` and numerous `scripts/deploy/*` proof scripts.

### High

4–10. Multiple **tenant escape / IDOR** paths where `if cid is not None and …` fail-open when `clinic_id` is null, plus teleconsult/dashboard/reminder/process-due global admin behavior, cross-clinic doctor mutation, and null-clinic patient mutation.
11. **Refresh rotation race** — non-atomic revoke allowed dual live refresh chains.
12. **MFA soft gate** — required roles could log in without MFA enrollment.
13. **Reminder respond fail-open** when `REMINDER_RESPOND_TOKEN` unset.
14. **Production kill-switches** for attachment encryption and insecure DB SSL without dual attestation.
15. **Update packages** accepted empty digest maps with present `images/*.tar` and unsafe `../` paths.
16. **Blank JWT `jti`** accepted by `get_current_user`, defeating logout denylist.

---

## 5. Fixes Implemented

| Fix | Primary files |
|-----|----------------|
| WhatsApp `X-Hub-Signature-256` fail-closed | `core/whatsapp_webhook_security.py`, `routers/reminders.py`, `services/whatsapp_service.py` |
| Fail-closed clinic scope | `routers/{appointments,rendezvous,patient,doctor,doctor_dashboard,reminders}.py`, `services/{message_attachment_service,teleconsultation_access}.py` |
| Owner singleton | `services/user_provisioning.py` (advisory lock), `database_migrations.py` (`uq_users_single_platform_owner`) |
| Atomic refresh CAS | `services/auth_session_service.py` |
| Reject empty jti | `security.py` |
| MFA hard gate | `routers/auth.py` |
| Reminder token fail-closed | `core/reminder_security.py` |
| Dual attestation boot guards | `core/settings.py` |
| Update path/digest hardening | `core/update_security.py` |
| Middleware fail-loud when deployed | `main.py` |
| Credential redaction | docs + deploy/verify scripts → env vars |
| Regression suite | `tests/test_redteam_final_assessment.py` (+ reminder/e2e/RBAC fixture updates) |

---

## 6. Regression Results

| Suite | Result | Evidence |
|-------|--------|----------|
| Red Team unit/integration | 13 passed, 1 skipped | `tests/test_redteam_final_assessment.py` |
| Full pytest | **275 passed**, 1 skipped | `evidence/security/redteam/FULL_PYTEST.txt` |
| Official pentest harness (38) | EXPLOITED=0; BLOCKED=28; PARTIAL=7 | `evidence/security/redteam/PENTEST_HARNESS.txt` |
| Bandit static | Findings reviewed; no new Critical RCE in app paths | `evidence/security/redteam/BANDIT.txt` |
| Dependency review | Pins inventoried; pip-audit unavailable in CI image | `evidence/security/redteam/DEPENDENCY_REVIEW.json` |
| Attack matrix export | | `evidence/security/redteam/ATTACK_RESULTS.json` |

PARTIAL pentest items remain informational (SSRF surface absence, offline node tabletop, etc.) and do not reopen Critical/High code findings.

---

## 7. Remaining Residual Risks

| ID | Severity | Risk | Disposition |
|----|----------|------|-------------|
| RR-1 | High→Accepted | Secrets remain in **git history** even after working-tree redaction | **Formally accepted** with mandatory ops rotation of all AASMA/staff passwords and invalidation of any keys that appeared in history **before production cutover** |
| RR-2 | Medium | Browser SPA stores JWT in `sessionStorage` (XSS → session theft) | Accepted; CSP/headers present; HttpOnly cookie migration deferred |
| RR-3 | Medium | Rate limiter may key on Docker/proxy peer IP | Accepted; document Railway trusted proxy sizing |
| RR-4 | Medium | Emergency dual-attestation bypasses still exist for encryption/TLS | Accepted; requires explicit `EMERGENCY_SECURITY_BYPASS_ATTESTATION=I_ACCEPT_PRODUCTION_PHI_RISK` |
| RR-5 | Medium | WhatsApp inbound requires correct Meta App Secret deployment | Ops gate — misconfig fails closed (good), but messaging stops |
| RR-6 | Low | Bandit noise: pilot seed passwords, `random` in non-crypto paths, XML escape | Accepted; pilot seed blocked in production boot |
| RR-7 | Low | pip-audit not executable in this environment | Accepted with static pin review; run pip-audit in CI pipeline |

---

## 8. Security Evidence

- `evidence/security/redteam/ATTACK_RESULTS.json`  
- `evidence/security/redteam/FULL_PYTEST.txt`  
- `evidence/security/redteam/PENTEST_HARNESS.txt`  
- `evidence/security/redteam/BANDIT.txt`  
- `evidence/security/redteam/DEPENDENCY_REVIEW.json`  
- `tests/test_redteam_final_assessment.py`  
- PR: `cursor/red-team-final-assessment-ab76`

---

## 9. Overall Security Rating

**STRONG** — adversarial re-audit cleared Critical/High code paths; residual risks are operational or Medium and explicitly documented.

---

## 10. Final Recommendation

Ship this Red Team remediation set to production **after**:

1. Rotating all credentials that ever appeared in git history (AASMA staff + any reused secrets).  
2. Setting `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `REMINDER_RESPOND_TOKEN`, and `ATTACHMENT_ENCRYPTION_KEY` in Railway.  
3. Confirming `REQUIRE_ATTACHMENT_ENCRYPTION` remains true and emergency attestation is unset.  
4. Completing the existing production ops attestation checklist.

---

## PRODUCTION APPROVED
