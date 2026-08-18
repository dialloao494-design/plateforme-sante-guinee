# Platform Excellence Roadmap

**Purpose:** canonical, living assessment and improvement backlog for Plateforme
Santé Guinée. This document is written for maintainers and coding agents working
toward a safe, coherent, hospital-grade product.

**Owner:** repository maintainers  
**Last evidence update:** 2026-08-18  
**Current branch:** `main`  
**Original assessment baseline:** approximately **7.5/10 as a supervised pilot**
and **6/10 for broad production deployment**.

## Executive verdict

The platform is a strong, functional pilot with a serious backend, meaningful
security controls, real offline engineering, broad regression coverage, and live
deployments. It is suitable for a **supervised clinic pilot**.

It is not yet certified for unsupervised, hospital-wide or multi-clinic expansion.
The main risks have shifted away from missing basic functionality and toward:

- fragmented patient context and clinical UX;
- frontend size and maintainability;
- browser-level and offline release evidence;
- operational recovery evidence;
- observed usability in real hospital workflows.

This is a safety and evidence distinction, not a claim that the platform is a
fragile prototype.

## How to use this document

- Treat the status table and workstreams below as the canonical improvement
  backlog.
- Link code, tests, CI runs, production checks, and field evidence when changing
  a status.
- Never replace a dated assessment with an unsupported score.
- A green unit test is not production verification; a green deployment is not
  clinical workflow validation.
- Keep historical reports as snapshots. Record reconciliation here when newer
  evidence supersedes them.

### Evidence states

| State | Meaning |
|---|---|
| `OPEN` | Known work remains and no adequate verification exists. |
| `IN PROGRESS` | Implementation or validation is underway. |
| `CODE COMPLETE` | Implemented, but not yet proven through all required gates. |
| `CI VERIFIED` | Required automated gates passed on the committed change. |
| `PRODUCTION VERIFIED` | Deployment and production smoke evidence passed. |
| `FIELD VALIDATED` | Representative hospital staff completed the workflow under observed conditions. |

## Current evidence snapshot

The original verdict was captured at commit `e4f2cdb`, when browser CI and the
post-deployment smoke check were red. Those two immediate blockers were repaired:

- patient intake now respects the production `patient_number NOT NULL` constraint;
- browser tests use a stable birth-date selector;
- Playwright selects a CI-available Python interpreter;
- embedded Alembic runs preserve API/Uvicorn diagnostics;
- post-deployment smoke checks retry bounded transient deployment warm-up failures.

Current evidence:

| Gate | State | Evidence |
|---|---|---|
| Backend test suite | CI VERIFIED | 425 passed, 1 skipped locally during remediation; backend CI green on `0a43385`. |
| Frontend unit tests | CI VERIFIED | 33 passed locally; frontend CI green on `0a43385`. |
| Offline unit/pure tests | CI VERIFIED | 31 passed locally; frontend CI green on `0a43385`. |
| Browser E2E | CI VERIFIED | 20/20 passed locally in CI mode; [CI run 32090605230](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32090605230) succeeded. |
| Deployment and production smoke | PRODUCTION VERIFIED | [Deployment run 32091947808](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32091947808) succeeded for `f6d5635`. |
| Latest validation-trigger CI | Superseded/cancelled | [Run 32091947800](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32091947800) was cancelled; use the preceding successful CI evidence above, not this run as a green claim. |
| Repository state at update | Documented | `main` at `f6d5635` before this documentation change. |

The release gates are therefore no longer the leading code blocker. They must
remain permanent gates, and cancellation must never be reported as success.

## Platform scorecard

| Area | Assessment | Current state |
|---|---|---|
| Core clinical functionality | Strong | Pilot-ready; field validation remains workflow-specific. |
| Backend reliability | Strong | Broad automated coverage and production health checks. |
| Database integrity | Strong | Versioned migrations, billing integrity, dossier-number constraints. |
| Security architecture | Strong | Operational exercises and fresh dependency evidence remain. |
| Offline engine | Technically solid | Full browser/network recovery and field evidence remain. |
| Frontend maintainability | Needs restructuring | Large modules and stylesheet create regression risk. |
| UX consistency | Improving, fragmented | Reception improved; clinical modules remain inconsistent. |
| Automated testing | Strong | Green reference CI exists; keep browser gate reliable. |
| Deployment | Live | Latest validation deployment and smoke workflow succeeded. |
| Supervised clinic pilot | Yes | Continue with backups and an escalation contact. |
| Hospital-wide readiness | Not yet | Requires the exit criteria in this roadmap. |

## Prioritized workstreams

### P0 — Preserve release safety

**Status: PRODUCTION VERIFIED; continuous gate**

- Keep backend, regression, frontend, secrets, browser E2E, deployment, and
  post-deployment smoke checks green.
- Treat cancelled or skipped required jobs as inconclusive, not successful.
- Keep the full offline journey in browser coverage: disconnect, queue, reconnect,
  replay once, obtain the canonical dossier number, remap dependent records, and
  verify persisted server state after refresh.
- Add a regression test for every production or clinic defect.

**Exit criterion:** protected releases cannot advance unless every required job
finishes successfully, and failures provide actionable artifacts/logs.

### P1 — One canonical patient workspace

**Status: CODE COMPLETE — locally browser-verified; CI and field validation open**

The system has multiple independent `selectedPatient` and tab/workflow state
implementations. Reception has moved toward URL-backed state, while laboratory,
pharmacy, nursing, immunization, history, and other clinical modules still carry
their own context patterns.

Target information architecture:

```text
/clinical/patients/:patientId
├── Overview
├── Timeline
├── Admission
├── Clinical notes
├── Orders and results
├── Medication
├── Billing
└── Documents
```

Required qualities:

- one canonical patient identity and safety banner;
- URL-addressable module and subview state;
- refresh, Back, Forward, and deep-link correctness;
- explicit behavior when patient context changes;
- role-aware actions without duplicating patient state;
- no stale patient data crossing clinic or user boundaries.

**Exit criterion:** all clinical modules consume the shared patient-context model,
and cross-module browser tests prove context, navigation, refresh, and tenant safety.

Implemented evidence (2026-08-18):

- Reception, Nursing, Laboratory, and Pharmacy now share the `patient` URL
  parameter contract through `useClinicalPatientRoute`;
- deep links and refresh restore the patient in those workspaces;
- closing a dossier removes URL context without the hydration race reopening it;
- `clinical-patient-context.spec.js` verifies all 3 newly migrated roles against
  the same clinic patient in isolated authenticated sessions.
- Doctor, Billing, Hospitalization, History, Nutrition, Immunization/PEV,
  Nursing Care, Radiology, and Discharge now consume the same URL patient
  contract and shared patient safety strip;
- a doctor deep link restores identity without creating or reopening a clinical
  consultation; starting a consultation remains an explicit clinician action;
- the expanded browser regression covers 13 patient-bound workspaces, refresh,
  close, role isolation, and the doctor no-write-on-refresh safeguard;
- timeline identity now includes the canonical dossier number and recorded age,
  with backend contract coverage;
- discharge routing now matches backend authority instead of exposing a page to
  nurses whose API calls would all be rejected.
- PEV patient lookup and journey access now match the authorized vaccination
  workflow while retaining clinic-scoped patient checks.

Remaining evidence: required CI must pass this commit, cross-clinic negative
browser coverage must prove tenant isolation at the UI boundary, and hospital
staff must validate the navigation model on clinic hardware.

### P1 — Clinical UX coherence and patient safety

**Status: IN PROGRESS**

Reception established useful patterns: predictable patient opening, URL-backed
state, a patient safety strip, accessible application dialogs, and focus management.
Apply a common clinical design system across remaining modules.

Standardize:

- page hierarchy, spacing, typography, cards, forms, tables, empty states, and
  responsive behavior;
- primary, secondary, destructive, disabled, loading, and success actions;
- validation, error recovery, confirmations, notifications, and offline status;
- patient identity, allergies/alerts, clinic, visit status, and current task;
- keyboard navigation, focus placement, contrast, target size, and screen-reader
  semantics;
- French clinical terminology, dates, currency, names, statuses, and print output.

**Exit criterion:** role-based workflow reviews pass for reception, nursing,
physician, laboratory, pharmacy, cashier, and administration on clinic hardware
and realistic network conditions.

Implemented evidence (2026-08-18): the patient identity/safety strip is now a
shared clinical component used consistently by all patient-bound clinical
dashboards, with role-specific context labels and a single “Fermer le dossier”
action. The doctor workflow additionally separates passive dossier restoration
from the write action that starts a consultation. This is locally
browser-verified, not yet field-validated. Clinical errors and success messages
in the migrated workspaces now use one shared live-region component with alert
and status semantics; the focused WCAG browser gate reports no serious or
critical violations (known contrast warnings remain tracked).

### P1 — Frontend decomposition and performance

**Status: IN PROGRESS — first performance/closure-risk tranche locally verified**

Known hotspots at the original assessment included a roughly 3,841-line clinical
stylesheet, 1,200–1,400-line clinical/reception modules, and several 700–820-line
dashboards. Re-measure before refactoring; do not assume those counts remain exact.

Work:

- split orchestration, API access, state machines, rendering, and reusable UI;
- replace the monolithic stylesheet with bounded tokens/components/module styles;
- centralize date, time, currency, patient-name, and status formatting;
- resolve all React hook warnings, treating stale closures as correctness risks;
- introduce route/module-level code splitting;
- measure the clinical bundle on constrained clinic connections;
- set explicit image dimensions where missing to prevent layout shift.

**Exit criterion:** no clinical dashboard is a monolithic workflow controller,
hook warnings are zero, shared formatters/components have regression tests, and
performance budgets pass on representative low-bandwidth hardware.

Implemented evidence (2026-08-18):

- all 10 existing React hook warnings were corrected without suppressions;
- stale polling/message/patient/order callbacks now have explicit dependency or
  ref semantics;
- the manual `clinical-pages` bundle rule that defeated route lazy loading was
  removed;
- the clinical JavaScript bundle fell from approximately **572 KB minified** to
  role-level route chunks (Reception approximately **109 KB**, Doctor clinical
  approximately **41 KB**, Lab approximately **33 KB**, Pharmacy approximately
  **27 KB**, Nurse approximately **18 KB** in the local production build);
- the build no longer reports a chunk over 500 KB or an ineffective clinical
  dashboard dynamic import.
- Guinea-French date, time, GNF currency, and patient-name presentation now use
  one tested formatter layer; existing appointment/date utilities delegate to
  it instead of maintaining competing locale behavior;
- CI now enforces explicit uncompressed budgets for the largest JavaScript
  asset, shared clinical stylesheet, Reception, Doctor, Laboratory, and Pharmacy
  route chunks. The local production build passes all 6 budgets (largest JS
  **214.84 KiB**, clinical CSS **58.56 KiB**, Reception **106.04 KiB**, Doctor
  **40.73 KiB**, Laboratory **32.62 KiB**, Pharmacy **26.58 KiB**).

Remaining: split large workflow controllers and the shared clinical stylesheet,
finish migrating legacy presentation calls, and validate on clinic
hardware/network conditions.

### P1 — Offline release certification

**Status: CI VERIFIED at component/logic level; FIELD VALIDATION OPEN**

Existing strengths include Dexie persistence, durable FIFO outbox behavior,
exponential retry, dead-letter handling, stale in-flight recovery, per-user
ownership, idempotency, dossier reconciliation, temporary-ID remapping, and
dependent mutation ordering.

Remaining evidence:

- browser-to-backend recovery under actual network loss;
- restart/crash recovery during synchronization;
- multi-device/concurrent conflict behavior;
- storage-quota and corrupted-cache recovery;
- clinic staff comprehension of queued, failed, conflict, and synchronized states;
- a documented escalation/export path when synchronization cannot recover.

**Exit criterion:** the full offline matrix passes in CI and during an observed
clinic exercise without duplicate clinical or financial records.

### P1 — Backup, restore, and incident readiness

**Status: OPEN operational evidence**

Documentation and endpoints are not substitutes for a restore exercise.

Required evidence:

- recent encrypted PostgreSQL backup and off-site retention policy;
- successful restore into an isolated environment;
- measured RPO and RTO;
- attachment/document recovery verification;
- storage, backup-age, database, queue, error-rate, and capacity alerting;
- named incident roles, escalation contacts, downtime procedure, and rollback drill;
- clinic paper-continuity/reconciliation procedure.

**Exit criterion:** a timed restore and incident simulation succeeds, with evidence
reviewed by the accountable operator and clinic lead.

### P2 — Security operations and dependency lifecycle

**Status: architecture strong; operations partially verified**

- Complete a fresh Python dependency CVE audit in a reproducible CI job.
- Maintain the zero-high/critical production npm policy.
- Enforce and test privileged MFA according to deployment policy.
- Verify secret rotation, access review, audit retention, attachment storage,
  WebSocket authentication, and webhook settlement procedures.
- Exercise session invalidation and suspected-account-compromise response.
- Reassess privacy, data retention, consent, and local regulatory obligations
  before expanding beyond the supervised pilot.

**Exit criterion:** automated dependency gates and a signed operational security
checklist exist, with no unresolved critical finding.

### P2 — Framework and deployment debt

**Status: OPEN**

- Replace deprecated Pydantic class configuration before Pydantic 3.
- Correct Railway's raw legacy `FRONTEND_URL` rather than relying on runtime
  canonicalization; verify the actual environment before changing it.
- Remove obsolete deployment aliases and document the single canonical topology.
- Keep Alembic as the deployed schema authority and retain clean-database plus
  upgrade-path regression tests.

**Exit criterion:** no runtime compatibility warning in supported paths, deployment
configuration matches canonical documentation, and schema startup is deterministic.

### P2 — Observed hospital workflow validation

**Status: OPEN**

Run structured sessions with real representatives from:

- reception;
- nursing;
- physicians;
- laboratory;
- pharmacy;
- cashier/billing;
- clinic administration.

Measure task completion, time, errors, help required, terminology confusion,
handoff failures, print/document needs, offline comprehension, and accessibility.
Do not expose real patient data in test evidence.

**Exit criterion:** critical workflows complete without facilitator intervention,
all patient-safety findings are closed, and the clinic owner accepts the operating
and escalation procedures.

## Hospital-wide readiness gate

Do not label the platform hospital-wide production-ready until all of the following
are evidenced:

1. required CI and deployment gates are consistently green;
2. one canonical patient workspace is adopted across clinical modules;
3. the offline recovery matrix passes in CI and in a clinic exercise;
4. backup restore and incident drills meet accepted RPO/RTO targets;
5. security/dependency operational verification is current;
6. representative staff validate end-to-end workflows;
7. monitoring, support ownership, downtime procedures, and escalation are active;
8. no unresolved critical patient-safety, tenant-isolation, data-integrity, or
   billing-integrity issue remains.

Until then, continue the pilot with supervision, tested backups, controlled scope,
and a clear escalation contact.

## Decision log

| Date | Decision/evidence | Effect on verdict |
|---|---|---|
| 2026-08-17 | Original whole-platform assessment captured at `e4f2cdb`. | Supervised pilot approved; hospital-wide expansion withheld. |
| 2026-08-18 | Patient intake DB constraint, E2E selector, CI interpreter, migration logging, and smoke retry fixes landed in `a819aed` through `343f2c1`. | Immediate release blockers corrected. |
| 2026-08-18 | CI run 32090605230 succeeded. | Browser release gate has green reference evidence. |
| 2026-08-18 | Deployment run 32091947808 succeeded at `f6d5635`. | Latest validation deployment and production smoke are green. |
| 2026-08-18 | Shared patient URL context and safety strip landed locally for Reception, Nursing, Laboratory, and Pharmacy; focused browser regression passed. | Canonical workspace and clinical UX workstreams moved to IN PROGRESS. |
| 2026-08-18 | Hook warnings reduced from 10 to 0 and forced 572 KB clinical bundle removed. | Frontend maintainability/performance tranche locally verified; workstream remains open overall. |
| 2026-08-18 | Shared patient context expanded to every patient-bound clinical dashboard; doctor deep links made read-only until explicit consultation start; focused browser regression passed across 13 workspaces. | Canonical workspace implementation moved to CODE COMPLETE; CI, cross-clinic browser evidence, and field validation remain. |
| 2026-08-18 | Shared clinical formatters/live-region feedback added and route/style performance budgets enforced in CI; local unit, build, budget, accessibility, and cross-role browser checks passed. | UX coherence and frontend maintainability advanced; controller/style decomposition and field validation remain. |

## Related evidence

- [`STABILIZATION_FINDINGS_MATRIX.md`](STABILIZATION_FINDINGS_MATRIX.md)
- [`HISTORICAL_REGRESSION_MATRIX.md`](HISTORICAL_REGRESSION_MATRIX.md)
- [`OFFLINE_FAILURE_RECOVERY_MATRIX.md`](OFFLINE_FAILURE_RECOVERY_MATRIX.md)
- [`BACKUP_RESTORE.md`](BACKUP_RESTORE.md)
- [`PRODUCTION_CHECKLIST.md`](PRODUCTION_CHECKLIST.md)
- [`FINAL_PRODUCTION_READINESS_REPORT.md`](FINAL_PRODUCTION_READINESS_REPORT.md)

The older “Production Ready: YES” report is a dated module/clinic validation
snapshot. It does not override the broader hospital-wide readiness gate here.
