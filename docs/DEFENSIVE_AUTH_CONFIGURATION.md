# Authentication and configuration hardening

This change is source-only. It authorizes no production access, account changes,
key rotation, deployment, or clinical-data inspection.

## MFA API

`POST /auth/mfa/setup` requires `password` and, for an enrolled account,
`current_code` from the active factor. It stores a separate pending secret for ten
minutes. Login continues using the active factor throughout an abandoned or
failed enrollment.

`POST /auth/mfa/confirm` requires `code` from the pending factor. Replacement also
requires a freshly submitted `password` and `current_code` from the existing
factor. Confirmation activates the pending factor, clears pending state,
increments the token version and revokes prior refresh sessions in one database
transaction. It then returns a fresh access/refresh session for the caller.
Clients must persist that response just as they persist a password-change token
response. Both endpoints limit attempts to five per minute per source IP. Refresh rotation,
MFA changes and administrator session revocation acquire the user lock before
refresh-token locks; pending changes in revocation callers are preserved.

Migration `20261123_0041_pending_mfa` adds two nullable columns and preserves active
MFA secrets and enabled flags. Apply it using the established Alembic deployment
process before serving the new application. No production migration was performed
for this work. For rollback, stop enrollment requests, roll back application code,
and leave the additive nullable columns in place; do not restore an older users
snapshot or factor secret. The migration downgrade removes only pending fields
and discards unfinished enrollments; it does not restore previously replaced
factors or sessions. SQLite migration/rollback and HTTP behavior are locally tested with synthetic
data. Two additional real PostgreSQL concurrency tests verify MFA/refresh and
administrator-revocation/refresh ordering in a disposable local database. The
main-version refresh control fails the new lock-wait assertion. Staging and
production behavior remain unverified.

## Signing and attachment keys

Cached application settings resolve the JWT signing key once for the running
application. `SECRET_KEY` and `JWT_SECRET` remain aliases; if both are populated
they must match. Startup rejects conflicting aliases without reporting their
values. Do not resolve a deployment conflict by blindly changing either value:
an authorized operator must identify the current signing key and the attachment
key lineage first.

Existing explicit `ATTACHMENT_ENCRYPTION_KEY` values, the existing production
SHA-256/Fernet derivation (`sante-guinee-attachment-v1:`), and legacy plaintext
attachment reads are preserved. No keys were rotated. Independent attachment-key
rotation requires a separate backed-up migration with old-key reads, re-encryption,
verification and rollback. Do not introduce a new key into an existing attachment
store without that plan.

## Environment, seeds and diagnostics

Known hosted runtimes require explicit `ENVIRONMENT=staging` or `production`.
Unsupported environment names fail closed. Local supported environments are
`development`, `test`, `clinic-node` and its existing `clinic_node` alias.
Deployments on unrecognized providers must also explicitly select staging or
production. Pilot/demo seeding defaults off, including staging examples. Seed
flags do not remove accounts created previously.

Public `/health` and `/health/ready` responses contain only `status`; readiness
failure returns HTTP 503 with `status=not_ready`. Build, email and database
information remain available at `/health/build`, `/health/email` and
`/health/database` only to authenticated platform administrators/owners.
Monitoring scripts expecting public build identity must be updated by an
operator to use an authorized diagnostic session or CI/deployment metadata.
Readiness probes remain anonymous. No monitoring settings were changed here.

An authorized administrator can review leftover demo accounts without passwords:

1. Use their own administrator session and the existing account directory
   (`GET /platform/accounts`) with clinic/role/search filters. Review `test` and
   `unknown` categories, but also review all categories: classification is heuristic
   and some seed addresses are not classified as test accounts.
2. Compare account identifiers against the email/username manifests in
   `services/pilot_seed.py`, `services/clinic_pilot_seed.py`,
   `services/demo_clinic_seed.py`, and the startup seed helpers in `main.py`.
   Inspect only identifiers, roles, clinic assignments, active status and session
   metadata. Do not submit passwords, compare password hashes, try seeded logins,
   or open patient records to identify an account.
3. Verify each candidate with the responsible clinic administrator. Review the
   account's sign-in/audit metadata and preserve evidence. Use the existing
   governed deactivate/session-revoke workflow only after authorization; preserve
   linked clinical history. Do not bulk-delete accounts from name matches alone.

## Full clinical content policy

`DOSSIER_PATIENT.md` sections 3–4 document full dossier reads for administrators,
doctors and the patient. Receptionists, lab technicians and pharmacists are
therefore denied full notes, summaries, documents and full clinical timelines,
including grouped timeline and medical-history responses containing notes.
The shared service policy enforces this in addition to router role checks.
Clinic administrators and doctors still must match the patient's clinic;
patients still must own their record. Operational intake/allergy write authority
is preserved and does not confer full-note read access. Lab results, pharmacy
orders and reception workflows retain their dedicated APIs.

Policy decision still open: the historical document requires a doctor/patient
appointment link, while the current clinic model authorizes doctors within their
clinic. This change preserves the current clinic boundary rather than inventing a
new doctor-assignment rule. Clinical owners must also approve the field-level
subset, if any, of clinical history needed by operational roles; no new subset is
guessed here. Local regressions do not establish hospital-wide clinical readiness.

## Authorized incident follow-up

The clinic administrator must confirm that the exposed password was invalidated,
or reset it through an authorized account workflow; revoke affected sessions;
and preserve/review sign-in and authentication logs for the relevant interval.
The append-only authentication event ledger is available only if its migration
was already applied; preserve provider/application sign-in evidence as well.
Do not place credentials, patient information or raw logs in public issues.
Permanent removal of an affected GitHub description edit-history revision requires
explicit owner approval and a repository maintainer with the required GitHub
permissions. This work does not delete edit history or rewrite Git history.

## Local verification

Run the normal synthetic suite with `.venv/bin/python -m pytest tests/ -q`.
`tests/test_mfa_refresh_postgres.py` additionally requires a disposable PostgreSQL
instance with TCP disabled and its Unix socket in a private
`/tmp/defensive-auth-pg.*` directory. The test refuses remote URLs, passwords,
other database names and sockets outside that directory pattern. Create an empty
`defensive_auth_synthetic` database there, then run:

```sh
SYNTHETIC_POSTGRES_URL='postgresql+psycopg2:///defensive_auth_synthetic?host=/tmp/defensive-auth-pg.YOUR_TEMP_SUFFIX&port=55487' \
  .venv/bin/python -m pytest tests/test_mfa_refresh_postgres.py -q
```

Stop the disposable PostgreSQL server afterward. These tests never target a clinic
database. Their default skip in the regular suite is not evidence of PostgreSQL
verification; cite the separate opt-in run. This tranche has no CI, production or
field-validation claim.
