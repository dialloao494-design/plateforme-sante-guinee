# Remote branch cleanup and historical review — 2026-11-23

Reviewed against remote `main` at `a0241660b1ec87a71b538ef2eec26cf4d49e30df`.
Today's `fix/defensive-auth-configuration` remains at
`d4a1b75873e894f9253559f317737950406a4333`; neither branch was changed.

## Final disposition after owner review

The owner subsequently approved deleting obsolete Cursor work rather than
retaining branches for optional UI changes, historic tests or design documents.
**48 remote branches are now deleted in total**: the 33 integration-proven
branches described below, plus 15 superseded/historical branches removed after
source review. The additional 15 are not claimed byte-identical to main; their
history remains recoverable in the verified local bundle.

Only three old branches remain because source comparison found specific missing
behavior worth recovering selectively:

- `cursor/security-wave2-documents-ab76`: upload malware-scanner integration and
  document-security regression cases.
- `cursor/security-wave4-clinic-node-ab76`: encryption/key-separation/network
  startup guard wiring.
- `cursor/clinical-regression-pilot-ab76`: backend receipt issuance time and cashier
  attribution, separate from printing provenance.

Do not merge any of these wholesale. Today's authentication branch and main stay
unchanged. `ci/clinical-decomposition-tenant-isolation` was already removed with
ancestry proof; its commits are in main. The older tables below preserve the
initial review dispositions; this section supersedes their retain/candidate
recommendations. Final per-branch disposition is recorded in the private local
manifest and deletion/readback receipts.

## Executed cleanup

Deleted **33 remote branches** authorized by the owner: 25 whose tips are ancestors
of main, three whose commits all have patch equivalents in main, and four whose
entire Git trees exactly match main-history commits after squash merges, and one
whose sole changed document is byte-identical to main.
All deletions used expected-commit leases and atomic pushes. Readback confirmed
all 33 absent, all 18 retained old branches present, and main/today unchanged.
Local working branches were not deleted. No application changes, merges,
deployments, database operations, or clinical data access occurred.

Before deletion, all 51 old branch tips and their reachable history were saved in
an ignored local recovery bundle. This bundle includes historical code and must
remain private; one retained old branch contains embedded credentials.

- Bundle: `backups/branch-cleanup/2026-11-23/old-branches.bundle`
- Manifest: `backups/branch-cleanup/2026-11-23/manifest.json`
- Deletion receipts and final readback: same directory.
- Bundle SHA-256: `fd11562b07f6d08f0c8a83a61be77f706fc847ede69c27878a66086121dd9511`
- `git bundle verify` passed before deletion.
- Recovery can fetch an individual named ref from the bundle into a new local
  branch; publishing a recovered branch is a separate operation.

These are local recovery artifacts, not an off-site backup or a credential-history
cleanup. Deleting a remote branch does not remove its commits from every clone,
PR, provider cache or retained backup.

## Deleted branches and proof

| Branch | Preserved tip | Integration proof |
|---|---|---|
| `ci/clinical-decomposition-tenant-isolation` | `1deb360d` | ancestor-of-main |
| `cursor/align-vercel-production-cors-ab76` | `a175cce8` | ancestor-of-main |
| `cursor/billing-integrity-hardening-ab76` | `d2e5e69a` | ancestor-of-main |
| `cursor/canonical-frontend-url-ab76` | `d6ca1668` | ancestor-of-main |
| `cursor/clinic-login-safari-auth-ab76` | `12de53a9` | ancestor-of-main |
| `cursor/clinic-node-phase0-ab76` | `60cddd57` | ancestor-of-main |
| `cursor/clinic-stabilization-id-remap-ab76` | `67e66a7c` | all-patches-equivalent |
| `cursor/clinic-stabilization-offline-ab76` | `310b3be4` | exact-tree-in-main-history at `3e91799a` |
| `cursor/clinic-stabilization-offline-e2e-ab76` | `213129f1` | exact-tree-in-main-history at `8287b7e9` |
| `cursor/clinic-stabilization-residuals-ab76` | `9ce14b65` | exact-tree-in-main-history at `f01c6643` |
| `cursor/clinic-stabilization-ws-prod-ab76` | `83c8e858` | all-patches-equivalent |
| `cursor/clinical-workflow-fixes-ab76` | `f12c9e92` | ancestor-of-main |
| `cursor/db-fingerprint-proof-ab76` | `76891ff1` | ancestor-of-main |
| `cursor/doctor-clinic-requests-ab76` | `1a8d1e93` | ancestor-of-main |
| `cursor/fix-alembic-0017-idempotent-ab76` | `8e3a7bae` | ancestor-of-main |
| `cursor/git-reconciliation-deploy-ab76` | `300bbe89` | ancestor-of-main |
| `cursor/offline-v1-production-go-ab76` | `af7693c8` | ancestor-of-main |
| `cursor/production-findings-completion-ab76` | `73dd1e64` | ancestor-of-main |
| `cursor/production-hardening-ab76` | `9e44cc1d` | ancestor-of-main |
| `cursor/railway-autodeploy-trigger-ab76` | `5c52f448` | ancestor-of-main |
| `cursor/reception-billing-refund-fixes-ab76` | `9ee0d091` | ancestor-of-main |
| `cursor/reception-register-billing-hotfix-ab76` | `759e5646` | exact-tree-in-main-history at `03415e05` |
| `cursor/reception-register-duplicate-hotfix-ab76` | `677f82ed` | ancestor-of-main |
| `cursor/reception-review-hardening-ab76` | `a3fd9df5` | all-patches-equivalent |
| `cursor/reception-service-billing-ab76` | `9e44d610` | ancestor-of-main |
| `cursor/reception-unlock-lockout-ab76` | `c1538944` | ancestor-of-main |
| `cursor/red-team-final-assessment-ab76` | `49a26d12` | ancestor-of-main |
| `cursor/registration-regression-guard-ab76` | `57e94e08` | ancestor-of-main |
| `cursor/retire-seven-rust-refs-ab76` | `cb7c3c59` | ancestor-of-main |
| `cursor/security-wave6-pentest-ab76` | `8e0e05d2` | ancestor-of-main |
| `cursor/security-wave7-certification-ab76` | `abf7d9e0` | ancestor-of-main |
| `cursor/zero-legacy-frontend-ab76` | `d52d4ff2` | ancestor-of-main |
| `cursor/security-pentest-plan-ab76` | `84b50c4b` | Sole changed document byte-identical to main |

## Review method and limits

Reviewed each old branch's unique commits and authored diffs, traced current
implementations on pinned main, and compared exact file/tree content where
applicable. A positive `git cherry` count alone does not establish missing
functionality: squash merges and later rewrites frequently changed patch identity.
This is static source/history review, not a fresh security certification or
behavioral regression run. No new CI, browser, container, warehouse, production,
or physical-clinic verification was performed. Older success/readiness claims
remain dated snapshots and do not override PLATFORM_EXCELLENCE_ROADMAP.md.

## Retained workflow and stabilization branches

All branch names below use the `cursor/` prefix. “Candidate” is a recommendation;
these retained branches were not deleted.

| Branch | What's in it / current-main comparison | Disposition |
|---|---|---|
| `aasma-nurse-dashboard-fix-0618` | Nurse patient endpoint and clickable assessment/admission lists. Newer equivalents exist in `routers/nurse_assessment.py`, `services/nurse_assessment_service.py`, `clinicalApi.js` and `NurseDashboard.jsx`. | Superseded; further cleanup candidate. |
| `doctor-dashboard-ux-ab76` | Consultation-first layout, queue cap/collapse, scroll to active consultation; lockout/unlock fixes already implemented elsewhere. Current `DoctorClinicalDashboard.jsx:789–811` still renders the full department queue before consultation. | Keep; selectively port consultation UX with browser regression coverage. |
| `fix-slowapi-backend-startup-862c` | Removes unsupported `limiter.init_app(app)`. Main already omits it and uses middleware/app state (`main.py:151–154,262`). | Superseded; further cleanup candidate. |
| `legacy-frontend-redirect-ab76` | Legacy redirect site, production Vercel workflow and live-login script; canonical frontend is already handled in current deployment workflow. | Do not merge. Historical script contains embedded clinic credentials; review exposure and rotate/revoke if still usable. No credentials reproduced or tested. |
| `offline-architecture-ab76` | Unique `OFFLINE_FIRST_ARCHITECTURE.md` (970 lines) and `OFFLINE_IMPLEMENTATION_ROADMAP.md` (349 lines): Clinic Node, local network HTTPS, UPS, installer, licensing, migration and recovery goals. | Preserve/reconcile design material; do not import old readiness or zero-loss claims. |
| `split-payment-reception-0618` | Split payments already implemented in BillingTab/useReceptionDashboard, server PDF payment details and browser print. Old server PDF additionally displayed transaction references; current browser receipt retains these. | Core feature superseded; preserve optional server-PDF parity difference for a decision. |
| `clinic-stabilization-db-alembic-ab76` | Deployed Alembic startup, canonical patient-number backfill/index, startup tests. Runtime/migration/test changes are in main ancestor `f01c664`; later main also wires the webhook router. | No missing DB feature identified; further cleanup candidate. |
| `clinic-stabilization-security-ab76` | Cookie authentication, WS query-token rejection, webhook HMAC, tenant mutation policy. Current `routers/ws.py`, `core/mobile_money_webhook_security.py` and `core/patient_ownership_policy.py` implement the controls, with newer validation/coverage. | Earlier implementation superseded; preserve pending final exact-content reconciliation. |
| `clinic-stabilization-e2e-matrix-ab76` | Multi-role seed helpers, dashboard tests and interrupted/delayed/duplicate/logout-relogin offline matrix. Main has newer restart/concurrency/policy tests; branch-only docs, commands and test cases remain. | Keep test/design material; selectively reconcile missing scenarios. Avoid obsolete password fixtures/selectors. |
| `clinical-regression-pilot-ab76` | Backend receipt identity/date/time/cashier corrections plus clinical UI, idle timeout and purge heuristics. Current nursing/catalogue are newer; some PDF behavior remains different. | Keep; selectively recover PDF fixes, never wholesale merge. |

### Specific workflow follow-ups

- **Backend receipt provenance:** branch `services/invoice_pdf_builder.py:121–123`
  accepts issuance date/time and cashier separately. Current main
  `services/invoice_pdf_builder.py:162–164` labels printing date/time/operator as
  invoice date/time/cashier. Port the narrow correction with PDF assertions. Later
  frontend printing fixes do not prove the backend PDF equivalent.
- **Legacy dossier fallback:** branch `routers/reception_his.py:602` creates a PAT
  fallback; current main `:682` falls back to numeric patient ID. Verify whether
  reachable under current integrity constraints before choosing a repair.
- **Doctor workspace:** current scroll-to-top and queue-first rendering differ
  from old consultation-panel scrolling/collapsed queues. Preserve newer patient
  workspace and admin controls when implementing.
- **Do not reintroduce old purge matching:** pilot branch heuristics include
  generic names and short/hex-like surnames and can misclassify actual people.
  Use the current explicit, scoped, audited reset workflow.
- **Idle timeout is a product decision:** old pilot branch uses 5/1 minutes;
  current main uses 30/5. No session policy was changed during this review.
- **Credential exposure:** old `scripts/deploy/prod_login_clinic_e2e.py:39–52`
  contains hardcoded clinic credentials. No login was attempted; current validity
  is unknown. Sanitization or deletion of a branch alone is not revocation.

## Retained security branches

| Branch (`cursor/…-ab76`) | What's in it / current-main comparison | Disposition |
|---|---|---|
| `security-architecture` | Unique 1,258-line threat model and cloud/node/sync design document; absent main. Predates later implementation. | Preserve as historical design; reconcile outstanding requirements against the living roadmap. |
| `security-wave0-identity` | Session-version/refresh/lockout/MFA/password work largely integrated through main ancestor `74c9a3b`. Old migration matches current identity migration except revision/parent IDs. Old validation script/reports remain branch-only. | Preserve historical evidence. Never merge the obsolete migration into the current chain. |
| `security-wave1-api` | Core authorization, input validation, rate limiter, output encoding and security-header helpers identical to main. Routers/tests evolved; old reports and validation script absent. | Mostly integrated/superseded; archive evidence before further cleanup. |
| `security-wave2-documents` | Encryption/scanner helpers exist, but scanner invocation, stored digest checks and response hygiene differ from current storage/download paths. | Keep; selectively recover integration and adapt regression cases. |
| `security-wave3-infra` | Compose hardening identical; later main changes support Railway private mesh. Old Railway config/validation evidence/tests remain. | Preserve evidence; do not restore stale cloud TLS/startup settings wholesale. |
| `security-wave4-clinic-node` | All 23 implementation/deploy/checklist files identical, but current settings omit some old startup guard calls. | Keep; selectively recover boot guards with settings regressions. |
| `security-wave5-sync-dr` | Eleven implementation/docs/test files identical; main update verifier additionally rejects unsigned images, path escapes and unlisted images. Six historical evidence files absent. | Implementation integrated and strengthened; preserve dated evidence before cleanup. |
| `tenant-security-hardening` | Ownership policy, PatientContext, patient schema and tenant mutation regression file identical; current routes retain ownership enforcement. Later registration/search/UI changed. | Core protection represented; reconcile remaining UX/schema-check differences before cleanup. |

### Priority security follow-ups (static evidence only)

1. **Upload malware integration:** Wave2 `services/secure_attachment_storage.py:116–120`
   scans bytes before storage. Main `:109–126` validates size/MIME and encrypts,
   but does not call the scanner. Repository-wide source review found scanner
   calls in tests, not upload/storage runtime. Recover/adapt the integration and
   verify harmless and scanner-rejected uploads through actual callers.
2. **Attachment digest and response hygiene:** old storage records SHA-256 and
   compares an expected digest when reading; main `StoredAttachment:34–39` lacks
   that field and `read:130–134` decrypts without application-level digest
   comparison. Fernet still authenticates encrypted ciphertext; this does not
   establish that all current integrity protection is absent. Main
   `schemas/patient_record.py:72–80` exposes internal `file_path` and the service
   fills it from storage keys. Review current middleware before asserting a
   download-caching vulnerability. Adapt the 14 branch-only Wave2 regression
   scenarios; do not assume every old assertion remains valid.
3. **Clinic Node startup checks:** Wave4 settings enforce attachment encryption
   for production **or clinic-node** (`core/settings.py:222–240` on branch).
   Main `:271–272` gates this block on production only. The identical
   `assert_clinic_node_secret_separation` helper exists but is not invoked by
   current settings; old host-network acknowledgment guard is absent too.
   Restore appropriate wiring and adapt the 18 branch-only settings/boot tests.
   No deployed Clinic Node configuration was inspected.
4. **Historical evidence is not certification:** old Wave0/1/3/5 reports,
   validation scripts and snapshots must not be relabeled as current CI or
   production evidence. Current stronger update verification must be preserved.

## Recommended next work

Address upload scanning, Clinic Node startup guards and historical credential
exposure first; then selectively implement backend PDF provenance and doctor
consultation focus. Reconcile useful old test matrices and design documents.
Further cleanup candidates may be removed after their remaining evidence or
optional feature differences have been explicitly accounted for. No wholesale
merge of the retained historical branches is recommended.

## Subsequent selective repairs

The owner subsequently authorized repairing the three concrete gaps against the
current branch. Scanner integration, Clinic Node boot wiring and backend receipt
provenance are now code-complete and locally verified, including async scan
responsiveness and encryption-cache hardening. Full backend: **583 passed,
3 skipped**. See [the recovery note](SECURITY_RECOVERY_2026-11-23.md) and the
living roadmap for current evidence and rollout limits. The three old branches
remain preserved until the replacement changes are merged; none was merged
wholesale. This does not close historical credential or broader hygiene items.
