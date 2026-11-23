# Selective recovery of security and receipt fixes

This change repairs current code using the historical branches as evidence.
It does not merge their obsolete migrations, deployment settings, purge rules,
session policies, fixtures or readiness claims.

## Upload scanning

All callers of `SecureAttachmentStorage.store` now scan validated plaintext before
encryption or persistent filesystem writes. The two asynchronous upload paths
offload storage/scanning to worker threads; database operations remain in their
original handlers. Rejected message uploads create no message or stored blob.

`ATTACHMENT_VIRUS_SCAN` retains its existing optional default, `off`:

- `off`: scanning disabled; MIME/size checks and configured encryption still apply.
- `stub`: synthetic EICAR detection for tests only; not a production antivirus.
- `clamav`: ClamAV daemon/client or `clamscan` must be available. Unavailable,
  failed or timed-out CLI scans return HTTP 503 without storing the file; a
  detected signature returns HTTP 400. CLI scans use a private temporary file
  with a fixed name and a 60-second subprocess timeout.
- An unknown mode returns HTTP 503 instead of silently disabling scanning.

Cipher-cache initialization and reset are serialized; construction errors stay
errors on retry instead of publishing an empty cipher that permits plaintext.
Concurrent round trips and a failed-retry regression cover this behavior.

No live scanner was installed or enabled and no existing attachment was rescanned.
An operator must provision and validate ClamAV before enabling `clamav` on a
deployed service. Existing encrypted/plaintext read formats remain unchanged;
there is no key rotation or attachment-data migration. Historical application-level
digest metadata and broader document-response hygiene are separate follow-ups,
not evidence that Fernet ciphertext authentication is absent.

## Clinic Node boot policy

Clinic Node requires an explicit valid Fernet attachment key. It cannot derive
that key from the signing secret or waive it using the cloud emergency bypass.
JWT, license, update and attachment secrets must be distinct. License and update
secrets are mandatory and must meet the dedicated 32-character minimum and
known-weak-value checks. Host
networking requires `CLINIC_NODE_ALLOW_HOST_NETWORK=true`; bridge remains the
preferred mode. Existing production cloud key derivation and TLS recovery policy
are preserved.

Use the installer-generated configuration. If an existing node fails these new
checks, review its current key lineage and configuration before upgrading. Do
not blindly replace keys: existing attachments/licenses/updates must stay readable
and verifiable. Missing-key or shared-key remediation may require a separate
backed-up migration and recovery rehearsal. No node settings or secrets were
changed by this source update.

## Receipt provenance

Backend Reception PDFs now use the invoice's stored issuance date/time and
original creator for the header, with the current printer/time only in the
printing footer. The existing legacy-midnight recovery helper is reused, so
the PDF and invoice API agree. An unknown issuer prints as unknown, not as the
current printer. Pharmacy receipts use the charge creation time and recorded
operator. Existing billing/clinic access checks remain in place.

This changes rendering only; no historical invoice or charge is rewritten.
Metadata passed to ReportLab paragraphs is escaped. Old UI-only printing fixes
remain in place.

## Validation scope

Regression cases cover blocked/clean uploads, scanner unavailability, typo modes,
CLI timeout, async responsiveness, invalid Clinic Node keys, key reuse, host-network
acknowledgment, original issuer versus reprint operator, legacy midnight recovery,
unknown issuer, pharmacy provenance and cross-clinic receipt denial.

The new defect regressions were observed failing before their repairs. Full local
backend verification passed **583 tests with 3 skipped**. Two opt-in PostgreSQL
concurrency checks and one existing-owner bootstrap case were skipped. The
living roadmap records the remaining release gates.
Real scanner/Clinic Node hardware, physical printing and deployment verification
remain separate operational gates.

## Senior pre-landing review follow-up

Review found and corrected these additional defects before landing:

- Fresh Clinic Node installation generated conflicting signing aliases. It now
  generates one signing key, preserves existing key lineage, and rejects incomplete
  or conflicting upgrade configuration before changing files. Existing missing keys
  require recovery planning rather than automatic replacement. Bridge is the default;
  the installer cannot silently grant host-network permission.
- Node license/update keys could be absent and fall back to signing material.
  Startup now rejects missing or weak dedicated secrets.
- Lab/imaging validation committed clinical state before archive scanning and audit.
  Validation, archive references, notes and audit now commit together. Scanner/audit
  failures roll back; successful retries do not duplicate archives. Edited lab
  findings become drafts requiring validation again. Precommit unreferenced blobs
  are removed; uncertain commit outcomes retain blobs to protect possibly committed
  records. Orphan reconciliation remains an operational follow-up.
- The production deployment workflow invoked a staging account seeder and mutating
  smoke checks. Production verification now performs read-only health/readiness
  and optional frontend checks. Seeding and synthetic patient checks require
  explicit staging configuration. Existing previously seeded accounts were not
  inspected or removed by this change; operators must inventory and remediate them
  separately without deleting clinical history.

Two synthetic PostgreSQL concurrency tests passed using an isolated local Unix
socket database, covering refresh races with MFA changes and administrator
revocation. Installer tests execute the real shell script with fake deployment
commands; no node or production service was changed during testing. These checks
are local evidence, not deployed or hospital-wide readiness evidence.

Final local verification: **616 passed, 1 skipped** (existing-owner bootstrap),
including both PostgreSQL concurrency tests. The final expanded installer suite
passed **17/17** separately. CI for the final pushed head remains pending.
