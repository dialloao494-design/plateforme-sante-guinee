# Security control audit — 2026-08-18

Scope: session invalidation, permissions and tenant isolation, clinical audit
logging, attachments, and WebSockets. This is code/test evidence, not a
substitute for the operator access review and incident exercise.

## Verdict

The reviewed controls are suitable for the supervised clinic pilot. One
material gap was found and fixed: `/ws/live` previously verified the JWT
signature and expiry but did not consult current account state, token denylist,
role, or session/token versions. A logged-out or disabled user's unexpired token
could therefore open a new live channel. WebSocket authentication now fails
closed against the same revocation state as HTTP and rechecks established
channels on every message and heartbeat (maximum idle revocation delay: 55
seconds).

## Control matrix

| Surface | Enforced control | Adversarial evidence | State |
|---|---|---|---|
| Session invalidation | Access JTI denylist, refresh-family rotation/reuse revocation, `session_version`, `token_version`, disabled-account and forced-password-change gates. | `test_auth_session.py`, `test_security_wave0_identity.py`; WebSocket tests cover HTTP logout, disabled users, and an already-open channel after version change. | Code verified |
| Permissions | Canonical role aliases and permission registry; clinical routes apply permission or role dependencies before service calls. | `test_security_wave1_api.py`, role-button browser matrix, clinical IDOR red-team suite. | Code verified; scheduled human access review remains open |
| Tenant isolation | Clinic resolution and resource-scoped queries return deny/not-found for foreign clinic data; offline queues are owner/clinic scoped. | `test_clinic_isolation_security.py`, `test_redteam_round2_clinical_idor.py`, browser URL/search/cache/history negative test. | Code + browser verified |
| Clinical audit | Patient/CIS reads and writes emit clinic-, actor-, patient-, action-, and resource-scoped immutable application records; audit listing is clinic scoped and capped to 1–500 rows. | `test_clinic_readiness.py`, security Wave 1, attachment denial regression. | Code verified; retention/export policy sign-off remains open |
| Attachments | Authenticated download route only; appointment/patient/doctor/clinic scope; opaque paths; traversal, extension/content mismatch, size, malware, encryption-at-rest, no-cache/nosniff, and successful/denied access audit. | `test_attachment_security.py`. | Code verified; production encryption key/restore exercise remains open |
| WebSockets | Query tokens rejected; cookie or first-message JWT only; JTI, active account, forced-password, current role, session version, token version, and denylist checked at connect and during the session. | `test_ws_auth_security.py` (9 cases). | Code verified; reverse-proxy timeout exercise remains open |

## Focused regression result

On 2026-08-18, 67/67 session, Wave 0/1, attachment, clinic-isolation,
clinical-IDOR, and WebSocket tests passed after the remediation; the WebSocket
subset passed 9/9 with the explicit logout-denylist case. The final full-suite
result is recorded in the canonical roadmap rather than inferred here.

## Operational items that remain

- Exercise privileged MFA and suspected-account-compromise response with the
  accountable operator.
- Review active staff/role assignments and record approvals at the clinic.
- Confirm audit and attachment retention, encrypted off-site backup, key
  rotation, and legal/privacy requirements.
- Exercise WebSocket proxy behavior and revocation timing in the deployed
  topology.
- Treat platform-level access to clinic PHI as break-glass operational access;
  review and document every use.
