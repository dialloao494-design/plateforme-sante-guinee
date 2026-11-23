# Pre-Landing Review — PR #46

Scope: complete changes from main `a0241660b1ec87a71b538ef2eec26cf4d49e30df`,
including authentication/runtime hardening and selective recovery from historical
branches. Review considered tenant access, transaction boundaries, concurrency,
secret lineage, upload persistence, migrations, receipt provenance and deployment
side effects. Historical branches were evidence; their obsolete changes were not
merged wholesale.

## Findings corrected before landing

| Finding | Correction and regression evidence |
| --- | --- |
| Fresh node installer generates conflicting signing aliases | One signing key for both aliases; real-script isolated installer cases |
| Upgrades fabricate missing keys, losing existing key lineage | Fail before mutation on missing, conflicting, weak, invalid or reused keys; preserve existing configuration |
| Installer silently permits host networking | Default bridge; explicit host acknowledgment required; no automatic fallback |
| Missing/weak dedicated license/update keys accepted | Node startup and installer reject unsafe keys |
| Result validation commits before archive/scanner/audit completion | One database commit, rollback on failure, precommit blob cleanup; lab/imaging scanner and audit-flush regressions |
| Repeated validation duplicates archive/audit; edited lab findings retain validation | Idempotent successful replay; lab edit returns to draft and requires new archive |
| Production deployment invokes staging seeder and mutating smoke | Remove seeding from production workflow; default read-only smoke; explicit staging gates tested |

The initial repair also covers scanning before attachment persistence, fail-closed
scanner configuration, encryption cache initialization failure/concurrency,
asynchronous upload responsiveness, explicit node encryption keys, and original
receipt issuance/operator provenance. Authentication review covered pending MFA
activation/replacement/expiry, refresh revocation, lock ordering, token versions,
staff revocation and fail-closed environment/signing configuration. Two real local
PostgreSQL synthetic races verified refresh against MFA activation and administrator
revocation. Fresh migration and clinical isolation/access regressions remain in CI.

## Review limits and remaining rollout work

No unresolved merge-blocking defect was identified in the reviewed scope after
these repairs. This is bounded code/test evidence, not proof of absence of all
vulnerabilities. Antivirus remains optional and disabled by default; operators
must provision and validate ClamAV before enabling it. No deployed keys were
rotated, existing files rescanned, node hardware tested or physical receipts
printed. Missing existing node keys need backed-up recovery planning. Uncertain
archive commit outcomes retain blobs to protect possibly committed records;
reconciliation is an operational follow-up. Previously seeded deployment accounts
need a separate operator inventory/remediation without deleting clinical history.
Doctor access within a clinic versus appointment-scoped dossier access remains the
explicit policy decision described in `DEFENSIVE_AUTH_CONFIGURATION.md`.

## Verification

Final local suite and final-head CI evidence are recorded below when completed.
Installer tests run the actual script against fake Docker/curl/PKI commands;
clinical/scanner tests use synthetic fixtures. Production data was not used.

Gate edits: none detected (26 listed, 12 read; patterns: RH-1,RH-3,RH-4,RH-12,RH-13,RH-14,RH-15,RH-16; unlisted idioms: none).
The removed deployment step was a staging seeder, not a test/check. Migration
assertions advance to the new head and check added fields. Scanner/environment
assertions tighten failure behavior; constructor failure is caught at its actual
boundary. No failing gate was bypassed.

Final local verification: **616 passed, 1 skipped** (existing-owner bootstrap),
including both PostgreSQL concurrency tests. The final expanded installer suite
passed **17/17** separately. CI for the final pushed head remains pending.
