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
| Backend test suite | CI VERIFIED | 435 passed, 1 skipped locally; current backend and clinic-regression jobs are green in CI run 32191243319. |
| Frontend unit tests | CI VERIFIED | 44/44 passed locally and the current frontend job is green. |
| Offline unit/pure tests | CI VERIFIED | 37/37 passed locally, including corrupt-cache/export and restart recovery; current frontend job is green. |
| Browser E2E | CI VERIFIED | 34/34 passed locally and in the current CI browser job, including responsive, WCAG-blocking, offline, cross-clinic, and role workflows. |
| Dependency audits | CI VERIFIED | `pip-audit` reports no known production Python vulnerabilities locally and in CI; `npm audit --omit=dev` reports zero vulnerabilities locally. |
| Frontend build/performance | CI VERIFIED | Lint and production build pass locally and in CI; all six JavaScript/route/stylesheet budgets pass. |
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
| Security architecture | Strong | Dependency evidence is current; operational exercises remain. |
| Offline engine | Technically solid | Automated browser/network recovery is green; field wording exercise remains. |
| Frontend maintainability | Improving | Shared patterns and extracted workflows landed; further controller/style reduction remains routine debt. |
| UX consistency | Cohesive baseline | Core hospital workspaces now share navigation, layout, feedback, and responsive patterns; field review remains. |
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

**Status: CI VERIFIED — field validation open**

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

Remaining evidence: hospital staff must validate the navigation model on clinic
hardware.

Cross-clinic negative browser evidence (2026-08-18): a disposable two-clinic
Playwright scenario provisions real staff and patients, then proves that foreign
patient IDs do not hydrate in Laboratory, Pharmacy, Nursing, or PEV; foreign
patients do not appear in Laboratory search; cached Clinic B context does not
survive authentication as Clinic A; and Back/Forward navigation restores only
the authorized Clinic A dossier. This passed locally within the full **22/22**
browser suite. CI run
[32180157974](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32180157974)
passed all 5 required jobs at `8922963`; field validation remains open.

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

Reception service requests now use a compact, scrollable workflow rail and one
flat prescription workspace instead of nested card controls. Register search,
category/status setup, catalogue selection, and actions have explicit labels and
responsive alignment. A new Chromium regression creates a real patient and an
authorized catalogue-backed request, verifies the active-navigation treatment,
and proves the form collapses to one column at 390 px without page overflow.
Local verification is green: lint, **44/44** frontend unit tests, **34/34**
offline tests, production build, all 6 performance budgets, and the full
**26/26** Chromium suite. CI and clinic-hardware validation remain open for this
specific change.

A second clinical-UX tranche now gives Reception, Pharmacy, and PEV one shared
semantic workflow navigation instead of competing boxed-tab implementations;
removes the laboratory's redundant single-item tab bar; flattens nested
Laboratory, Pharmacy, and Nursing fieldsets into quieter section dividers; and
removes the duplicate PEV patient-identity banner while retaining vaccination
details beneath the canonical safety strip. Unified Billing now presents a
two-step cashier workflow with translated statuses and structured amounts, while
Clinic Administration has responsive staff management, explicit form metadata,
shared live-region feedback, and a keyboard-accessible table viewport. Module
styles are emitted as bounded route assets rather than added to `clinical.css`.
The expanded accessibility gate found and fixed unnamed Pharmacy quantity/price
controls. Local focused evidence: **10/10** Chromium responsive/accessibility/
workflow tests, lint, production build, and all 6 performance budgets. Broader
CI and clinic-hardware review remain open.

### P1 — Frontend decomposition and performance

**Status: IN PROGRESS — named decomposition tranche CI verified**

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
- the first Doctor controller extraction moved patient identity and read-only
  nursing observations into `DoctorPatientOverview`; the dashboard fell from
  **1,276** to **1,203** lines and the browser regression now opens a real
  consultation and verifies the extracted safety-critical identity panel.
- that stronger regression exposed and locked a doctor open/close timing defect:
  a late consultation URL write could restore a dossier just closed by the
  clinician. Patient URL selection now occurs at the start of the explicit open
  action, so closing wins deterministically.
- the first Laboratory controller extraction moved patient identity into
  `LabPatientOverview` and stored-payload parsing/constants into a tested domain
  module; the dashboard fell from **1,225** to **1,095** lines, its first
  module-owned stylesheet is emitted as a separate route asset, and duplicate
  date/time/name presentation now delegates to the shared Guinea formatter;
- the laboratory extraction is locally verified by **41/41** frontend unit
  tests, lint, production build, all 6 performance budgets, and the cross-role
  patient-context browser regression. That browser test now asserts the
  extracted laboratory identity panel and canonical dossier number directly.
- Laboratory report templates, result-grid editing, validation, summaries, and
  print rendering now live in `LabResultsWorkspace`, while queue and patient
  identity have their own components; the controller is **784** lines versus
  **1,225** at baseline;
- Pharmacy domain calculations/form primitives, Nursing assessment domain/form
  primitives, and the PEV register/presentation layer now live in bounded module
  directories. Reception was already split into a 153-line controller, hooks,
  tabs, and components; its billing tab remains the largest reception view;
- patient age, gender, address, workflow status, date/time, GNF, and patient-name
  presentation now share the tested Guinea clinical presentation layer across
  these workspaces;
- the Nursing-specific block moved out of `clinical.css`, reducing the shared
  stylesheet from **3,841** to **3,714** lines and emitting Nursing as a separate
  route stylesheet. Laboratory, Pharmacy, and PEV also use module-owned styles;
- this tranche passes locally: lint, **43/43** frontend unit tests, **31/31**
  offline tests, production build, all 6 bundle/style budgets, the full **22/22**
  browser suite, and a post-extraction focused **15/15** browser rerun.
- CI run
  [32180157974](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32180157974)
  passed backend, historical clinic regressions, frontend unit/offline/audit/build/
  performance, secrets guard, and **22/22** browser tests at `8922963`.
- the next bounded extraction moved Laboratory sample collection into
  `LabSampleCollection`, PEV entry into `VaccinationEntryForm`, and the Pharmacy
  product grid into `PharmacyRequestEditor`. Laboratory fell from **768** to
  **707** controller lines, PEV from **619** to **519**, and Pharmacy from **720**
  to **647**. The extracted forms now own their accessible names, input metadata,
  table-region semantics, and loading/action copy. Local evidence is green:
  lint, **44/44** unit tests, production build, all 6 performance budgets, two
  focused **5/5** Chromium runs covering role behavior, narrow layout, and
  blocking WCAG checks across Laboratory, Pharmacy, Nursing, and PEV.

Remaining: continue reducing large view files and the shared clinical stylesheet
as normal maintainability work, and validate performance/UX on clinic
hardware/network conditions. The named controller/presentation tranche is code
complete locally; the broader workstream remains open until CI and field evidence.

### P1 — Offline release certification

**Status: CI VERIFIED; FIELD VALIDATION OPEN**

Existing strengths include Dexie persistence, durable FIFO outbox behavior,
exponential retry, dead-letter handling, stale in-flight recovery, per-user
ownership, idempotency, dossier reconciliation, temporary-ID remapping, and
dependent mutation ordering.

Local evidence added 2026-08-18:

- real Chromium network loss now covers offline patient registration, immediate
  local identity, offline invoice creation, reconnect, canonical dossier
  reconciliation, dependent billing remap, and an empty durable queue;
- a second Chromium case closes the active page with a stale in-flight patient
  mutation, starts a new runtime, and proves recovery to one searchable dossier;
- a two-browser/device case exposed and then locked a concurrent-registration
  race: an exact-registration fingerprint is uniquely enforced per clinic, the
  losing device adopts the canonical dossier, and search returns one patient;
- quota exhaustion preserves existing queued work and produces an actionable
  message; malformed derived cache is removed without touching the outbox;
  malformed durable payload is quarantined rather than replayed;
- the offline status panel now exports clinic-scoped recovery JSON without
  authentication headers; the confidential handling/escalation procedure and
  observed staff exercise are in `docs/OFFLINE_CERTIFICATION.md`.
- recovery export v2 now validates its version, active clinic/user ownership,
  required mutation identity, and manifest counts before download; corrupt
  conflicts are preserved with explicit warnings, while the UI prevents a
  meaningless retry of unreadable payloads and tells staff not to clear storage;
- the strengthened local gate passed **37/37 offline tests**, **44/44 frontend
  unit tests**, lint, production build, all six performance budgets, and **4/4**
  focused real-Chromium loss/restart/concurrent-device cases.

Local evidence added 2026-08-21:

- provisional invoice creation now reconciles its local invoice ID before any
  queued payment replays, preventing payments from remaining blocked against an
  `offline_*` URL;
- offline payment uses the complete invoice as its optimistic response, so
  prices, paid amount, remaining balance, and payment history update immediately
  without an online refresh replacing the invoice with an incomplete payload;
- known browser disconnection bypasses the network probe entirely; an
  unexpectedly degraded connection is capped at 1.5 seconds for its first safe
  clinical request and subsequent writes use the local queue during a bounded
  degraded-network window;
- the Admission laboratory control is now a compact search-and-select workflow:
  it no longer dumps arbitrary catalog rows, and separates examination name,
  internal code, price, and current selection with responsive behavior;
- locally verified: **46/46 frontend unit tests**, **41/41 offline tests**, lint,
  production build, all six performance budgets, and **2/2** focused
  real-Chromium regressions: the compact Admission catalog selection and the
  patient → invoice → payment → reconnect workflow (4.1 seconds in browser;
  offline payment acknowledgement asserted below 2.5 seconds).
- manual synchronization no longer silently exits when an automatic replay is
  already active: it joins that run, performs a forced follow-up pass, exposes
  loading/success/failure states, removes the action when the queue is empty,
  and asks Reception to refresh affected clinical data in place. The focused
  real-Chromium regression proves loading feedback, canonical dossier refresh,
  success confirmation, and disappearance of the completed sync action (**1/1**).
- a production-build/service-worker regression now opens the protected
  `/clinical/reception` deep link after complete browser network loss. It exposed
  and fixed a 15-second offline authentication bootstrap wait; an already
  authenticated workstation now renders from its session-scoped cached clinic
  identity immediately and resumes server validation/sync on reconnect;
- final local evidence for this certification pass is **46/46 frontend unit**,
  **42/42 offline**, **35/35 general Chromium**, and **1/1 production-PWA
  Chromium**, plus lint, production build, and all six performance budgets. The
  PWA protected route rendered in 2.0 seconds with the browser network disabled.
- manual retry now immediately reclaims a recently stranded `in_flight` row
  once no replay is active. This fixes the contradictory “one queued / zero
  sent” result captured in clinic testing; result messages now distinguish
  dependent-patient blocking, offline state, and wrong-session ownership. The
  exact recent-in-flight browser regression and **42/42** offline tests pass.
- the Reception dashboard now warms and locally reconstructs its clinic-scoped
  patient directory instead of caching only summary counters. Patient detail,
  dossier/name/phone search, and the “Total patients” queue therefore remain
  available after network loss. The exact existing-patient → admission → invoice
  browser flow preserves the 100,000 GNF tariff, acknowledges both writes below
  2.5 seconds, and replays both after reconnect. Locally verified with **44/44**
  offline tests and **4/4** Reception loss/restart/concurrent-device browser cases.
- Reception receipt printing now has a complete local print document and no
  longer requires the server PDF endpoint while offline. The printed document
  includes priced services, totals, payment history/mode, patient and operator
  identity, outstanding balance, and pending-sync status. The disconnected
  registration → invoice → payment browser regression proves the native print
  action before reconnect; 46/46 unit, 44/44 offline, build, lint, and all six
  frontend budgets remain locally green.
- receipt parity was then tightened against the canonical server PDF builder:
  section titles, metadata, cashier/date/time, four-column service table,
  exemption summary, payment detail, and footer now match its information
  architecture. The previously broken offline logo is explicitly precached and
  the production-PWA regression proves its bytes remain available after total
  network loss (**1/1** PWA Chromium).
- clinic print-preview evidence exposed overlapping registration and invoice
  templates because the global print stylesheet revealed every hidden document.
  Reception now has an explicit single-document print target and uses one
  invoice component online/offline. The exact print-media browser regression
  proves only the invoice renders; unit **46/46**, offline **44/44**, build,
  lint, and all six performance budgets remain locally green.

This tranche is code-complete and locally/browser verified. CI, deployment,
production, and clinic field validation have not yet been claimed.

Remaining evidence:

- clinic staff must complete and sign the observed wording/recovery exercise on
  clinic hardware. This has not yet been claimed or inferred from automation.

CI evidence: [run 32183372265](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32183372265)
passed all five required jobs at `ac33f0d`, including **425 passed / 1 skipped**
backend tests, frontend/offline/build/performance gates, historical clinic
regressions, secrets, and the full **24/24** Chromium suite. The preceding run
`32183014841` failed only because legacy tests still expected migration `0028` as
the head; it is superseded, not reported as successful.

**Exit criterion:** the full offline matrix passes in CI and during an observed
clinic exercise without duplicate clinical or financial records.

### P1 — Backup, restore, and incident readiness

**Status: AUTOMATION LOCALLY VERIFIED; OPERATIONAL RESTORE EVIDENCE OPEN**

Documentation and endpoints are not substitutes for a restore exercise.

Local automation added 2026-08-18:

- scheduled VPS dumps now fail closed on gzip/SQL validation, write SHA-256
  sidecars and JSON evidence, apply the documented 30-day retention default,
  and evaluate the configured RPO;
- `scripts/db/backup_restore_evidence.py` refuses live/system restore targets,
  requires a distinct `_restore_verify` database, does not replace an existing
  drill database without an explicit flag, restores with `ON_ERROR_STOP`, and
  removes the isolated database after the drill by default;
- restore evidence records migration heads, critical row counts, patient/clinic
  orphan checks, measured RTO, backup age/RPO, checksum, and artifact sizes;
- shell syntax, Python compilation, and **31/31** focused backup, DR, encryption,
  and clinic-readiness tests pass locally.

This proves the tooling, not the production backup. A timed drill against a
recent encrypted production artifact and attachment store still requires an
authorized operator and must not be inferred from local tests.

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

**Status: architecture strong; dependency gate locally verified; operations partially verified**

- [x] Complete a fresh Python dependency CVE audit in a reproducible CI job.
  `pip-audit 2.10.1` now audits `requirements-prod.txt`; the 2026-08-18
  baseline found `PYSEC-2026-1917` in `sentry-sdk 1.40.0`, upgraded it to
  `1.45.1`, and then reported no known vulnerabilities.
- Maintain the zero-high/critical production npm policy.
- Enforce and test privileged MFA according to deployment policy.
- Verify secret rotation, access review, audit retention, attachment storage,
  WebSocket authentication, and webhook settlement procedures.
- Exercise session invalidation and suspected-account-compromise response.
- Reassess privacy, data retention, consent, and local regulatory obligations
  before expanding beyond the supervised pilot.

**Exit criterion:** automated dependency gates and a signed operational security
checklist exist, with no unresolved critical finding.

Code audit evidence added 2026-08-18:

- WebSocket authentication now checks the access-token denylist, current role,
  active/forced-password state, session version, and token version at connect
  and on every message/heartbeat; regression cases cover logout, disabled users,
  and invalidation of an established channel;
- denied cross-patient attachment downloads now create a clinic/patient/resource
  audit record, while successful access remains in the attachment access trail;
- clinical audit listing is bounded to 1–500 records even for malformed negative
  limits;
- **67/67** focused session, permission, tenant, attachment, IDOR, and WebSocket
  tests passed locally (WebSocket subset **9/9**). The detailed matrix is in
  `docs/SECURITY_CONTROL_AUDIT_2026-08-18.md`.

### P2 — Framework and deployment debt

**Status: IN PROGRESS — code and documentation aliases cleaned locally**

- [x] Replace deprecated Pydantic class configuration before Pydantic 3.
  All response schemas use `ConfigDict(from_attributes=True)` and a source
  regression guard rejects both `orm_mode` and legacy `class Config` blocks.
- Correct Railway's raw legacy `FRONTEND_URL` rather than relying on runtime
  canonicalization; verify the actual environment before changing it.
- [x] Remove obsolete deployment aliases from code, automation, and active
  deployment documentation. `FRONTEND_URL` is the only accepted configuration
  key; a regression test proves former aliases are ignored.
- Keep Alembic as the deployed schema authority and retain clean-database plus
  upgrade-path regression tests.

**Exit criterion:** no runtime compatibility warning in supported paths, deployment
configuration matches canonical documentation, and schema startup is deterministic.

### P2 — Complete ward, room, and bed management

**Status: PRODUCTION VERIFIED — clinic exercise and cross-module follow-through open**

The current system records hospitalization accommodation tariffs and basic
admission placement. It does not yet provide a complete operational inventory of
wards, rooms, beds, berceaux, occupancy, transfers, or availability over time.

The clinic-scoped accommodation foundation now includes:

- [x] configurable wards/services, rooms, and accommodation types;
- [x] individual beds and newborn berceaux with stable identifiers;
- [x] available, reserved, occupied, cleaning, maintenance, and unavailable states;
- [x] admission allocation, expected discharge, expiring reservations, optimistic
  version checks, and database-enforced current-stay overlap prevention;
- [x] safe transfers between rooms/beds with preserved stay and immutable bed-state history;
- [x] pediatric, newborn, isolation, and accessibility placement attributes without
  encoding clinical suitability only in a price;
- [x] a responsive ward census with occupancy, expected-discharge, turnover, and capacity views;
- [x] explicit separation between the physical accommodation, its clinical
  suitability, and the billable tariff;
- [x] clinic isolation, permission checks, audit events, and offline-queued/idempotent
  allocation behavior;
- [x] responsive Hospitalization configuration, census, admission, and transfer workflows;
- [ ] add an embedded ward handoff summary to the Nursing dashboard and a compact
  placement summary to Reception (both roles already use the same APIs and route);
- [ ] complete real-browser two-user concurrent allocation and reconnect replay scenarios;
- [ ] validate the state wording and cleaning handoff with Reception and Nursing staff.

Local evidence (2026-08-24): Alembic `0035` passes clean-schema, partial stamped-
schema recovery, and create-all-before-upgrade paths. Full backend tests pass
**458/458 with 1 skipped**. Frontend unit **50/50**, offline
**45/45**, responsive Chromium **3/3**, lint, production build, and all six
performance budgets pass. [CI run 32760744306](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32760744306)
passes every required job, including the complete browser suite after its
Hospitalization navigation was aligned with the census-first workflow.
[Deployment run 32760965996](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32760965996)
passes Railway, Vercel, and post-deployment smoke. Railway `/health/build`
reports exact commit `a61e30b`, and the public Hospitalization route returns
HTTP 200. Clinic-field validation is not yet claimed.

**Exit criterion:** authorized staff can configure capacity, allocate and transfer
a patient without double-booking, see trustworthy real-time availability, and
recover safely from offline/concurrent updates; CI, production smoke, and an
observed clinic exercise all pass.

### P1 — Simplified clinic onboarding and daily administration

**Status: IN PROGRESS — secure onboarding and shift routines production-verified; field validation open**

- [x] Persist a resumable, clinic-scoped setup state instead of relying on staff
  memory or a one-time wizard.
- [x] Derive readiness on the server from identity, enabled services, active
  personnel, configured payment methods, required bed capacity, printing,
  offline-workstation, and test-patient evidence.
- [x] Replace the generic administration landing experience with a visible
  readiness route and a daily administrative handoff list.
- [x] Capture staff first and last names during account creation and use readable
  French role labels in the personnel view.
- [x] Add shift-oriented daily checks, role-specific opening/closing routines,
  and direct remediation for every warning.
- [x] Replace the legacy prompt-based password reset with an accessible,
  confirmation-oriented dialog that explains the forced first-login change.
- [x] Add a delivery-safe temporary-credential workflow so administrators do not
  need to communicate credentials through an insecure channel.
- [ ] Complete browser coverage using a deployed clinic-admin account, including
  narrow screens, keyboard navigation, cross-clinic denial, and resume-after-login.
- [ ] Validate setup wording and daily priorities with a clinic administrator.

Evidence: full backend suite **449 passed / 1 skipped**, frontend unit
tests **50/50**, focused accessibility/responsive Chromium checks **10/10**,
lint, production build, and all six performance budgets pass locally. Remote CI
run **32753005661** passed all six jobs. Gated deployment run **32753287391**
passed Railway, Vercel, and post-deploy smoke; Railway `/health/build` reports
commit `839864e`, and the production Vercel asset fingerprint matches the new
administration bundle. Clinic validation is not yet claimed.

Code-complete evidence (2026-08-24, current uncommitted tranche): clinic staff
onboarding now creates an inactive account and delivers a hashed, expiring,
single-use activation link; neither API nor administration UI reveals or sends a
temporary password. Existing-account resets use the same delivery-safe principle,
with expiring reset links and no raw-link logging. Resending revokes the prior
link, failed delivery remains visible and retryable, and activation atomically
enables both the user and clinic membership. Administration now includes an online-authoritative opening/closing
handoff register with printer/offline checks, server-derived clinical and billing
snapshots, one-open-shift enforcement, and explicit acknowledgement plus notes for
unresolved work. It is intentionally separate from future cash-drawer
reconciliation. Local verification is green: backend **456 passed / 1 skipped**,
frontend unit **50/50**, offline **45/45**, lint, production build, all six
performance budgets, and the focused **2/2** narrow-screen browser checks.
CI run **32756121047** passed all six required jobs for `7807b08`; gated
deployment run **32756387226** succeeded. Railway `/health/build` reports the
exact commit, and Vercel serves the public staff-activation route. Clinic field
validation is not yet claimed.

**Exit criterion:** a new clinic administrator can configure the establishment,
create the working team, verify billing/printing/offline operation, complete a
test patient journey, and run the daily administrative handoff without developer
assistance; tenant, accessibility, browser, CI, production, and field evidence pass.

### P3 — Future clinic expense and cash management

**Status: FUTURE ADD — documented, not scheduled**

This capability belongs to each clinic, not to the shared platform ledger. Every
financial record must be scoped by `clinic_id`; clinic staff must never see
another clinic's expenses or cash position. Platform-owner access should remain
aggregate/operational unless a separate, explicitly authorized support path is
defined and audited.

Future scope:

- expense categories and expense entry with supplier/payee, date, amount,
  payment method, notes, and supporting documents;
- approval thresholds and separation of requester, approver, and cashier roles;
- cashier shift opening/closing balances and cash-drawer reconciliation;
- reconciliation across cash, Orange Money, transfer, insurance, and other
  configured payment methods;
- shortage/surplus recording with required reason and immutable audit history;
- daily/monthly revenue-versus-expense, cash movement, and exportable reports;
- attachment authorization, tenant-isolation, accounting-integrity, and
  concurrent-update regression coverage.

Patient billing remains the source of patient revenue. Expense/cash management
must reconcile against billing and payments rather than duplicate or rewrite
those records.

**Exit criterion:** a clinic can close a cashier shift and produce an auditable
reconciliation from patient payments through cash position and approved expenses,
with tenant isolation, accounting integrity, and clinic acceptance proven.

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
| 2026-08-18 | Doctor patient overview extracted from the monolithic controller; expanded browser coverage found and fixed a late open/close URL race. | First workflow-controller decomposition landed with a patient-context regression lock. |
| 2026-08-18 | Laboratory patient overview and stored-payload domain logic extracted; local unit, build, performance, and cross-role browser gates passed. | Laboratory controller reduced by 130 lines with direct safety-identity regression coverage; broader controller/style decomposition remains open. |
| 2026-08-18 | Laboratory results/validation, Pharmacy, Nursing, and PEV boundaries extracted; shared presentation expanded; two-clinic browser attack scenario and full local release matrix passed. | Named frontend decomposition tranche is locally code-complete; canonical patient workspace gains direct tenant-isolation evidence. CI rerun and field validation remain open. |
| 2026-08-18 | CI-only run 32180157974 passed all 5 required jobs at `8922963`, including 22/22 browser tests with the cross-clinic negative scenario. | Canonical patient workspace moves to CI VERIFIED; named decomposition tranche is CI verified. No deployment was triggered. |
| 2026-08-18 | Reception service-request navigation and prescription workspace redesigned; desktop/mobile request regression added; local 44-unit/34-offline/26-browser release matrix passed. | Clinical UX coherence advances with a responsive, behavior-locked reception pattern; CI and field validation remain open for the tranche. |
| 2026-08-18 | Shared workflow navigation, flatter clinical forms, cashier/admin workspaces, and Pharmacy accessible grid labels added across Reception, Billing, Lab, Pharmacy, Nursing, PEV, and Administration; focused 10/10 Chromium gate passed. | Cross-role UI coherence advances and new billing/admin module CSS avoids growing the shared stylesheet; full CI and field review remain open. |
| 2026-08-18 | Laboratory sample collection, PEV vaccination entry, and Pharmacy request editing extracted into bounded components; controller sizes reduced and focused role/WCAG/browser gates passed. | Frontend decomposition advances without relaxing bundle budgets; Reception billing and Nursing assessment remain the principal large view sections. |
| 2026-08-18 | Production Python CVE audit added to CI; `PYSEC-2026-1917` remediated by upgrading Sentry SDK to 1.45.1; all Pydantic ORM schemas migrated to `ConfigDict`; obsolete frontend configuration aliases removed. Local `pip-audit` reported zero known vulnerabilities and backend tests passed 426/426 with one skip. | Dependency and framework debt substantially reduced; CI verification and direct confirmation of Railway's raw `FRONTEND_URL` remain before closing the workstreams. |
| 2026-08-18 | Offline recovery export upgraded to a scope-checked v2 manifest; corrupt conflict copies gain integrity warnings; unreadable mutations cannot be blindly retried; restart/network/concurrent-device Chromium cases passed 4/4 with 37/37 offline tests and all performance budgets green. | Automated offline recovery evidence is stronger and safer for clinic support; the observed clinic wording exercise remains the only offline certification exit item. |
| 2026-08-18 | Guarded backup/restore evidence runner, checksum manifests, isolated-target enforcement, migration/table/orphan integrity probes, and RPO/RTO measurement added; 31/31 focused DR tests passed. | Backup tooling moves to locally verified; a timed restore of a recent encrypted production backup plus attachment recovery remains an operational release requirement. |
| 2026-08-18 | Session, permission/tenant, audit, attachment, and WebSocket controls re-audited; live WebSockets now honor logout/disable/version invalidation and denied attachment access is audited. Focused security gates passed 67/67 (WebSockets 9/9). | Requested code-level security controls are verified; privileged MFA, access review, retention/key rotation, proxy exercise, and incident response remain operational work. |
| 2026-08-18 | Final local release matrix exposed and fixed a logout/re-login revocation race, duplicate refresh rotation, a stale registration assertion, and clinic-admin billing permission mismatch. Final gates: backend 435 passed/1 skipped; frontend 44/44; offline 37/37; Chromium 34/34; lint/build and six budgets green; Python and npm production audits clean. | Requested code-based tranche is locally release-green. Current commits still require remote CI/deployment verification; field/offline wording, production restore, MFA/access review, and operational drills are not claimed complete. |
| 2026-08-18 | [CI run 32191243319](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32191243319) passed all six jobs at `31ff30d`: backend, clinic regressions, frontend, browser E2E, secrets, and the new Python dependency audit. | The complete requested code tranche is CI verified. No production deployment was triggered; field validation and operational exercises remain explicitly open. |
| 2026-08-20 | Hospital workstation UX hardening established a shared 16 px action rhythm, responsive action stacking, explicit offline manual synchronization, reconnect-after-offline-bootstrap recovery, and price-preserving provisional invoices. Header-level refresh controls now state their scope and expose last-update context; shared polling exposes refresh progress. Local offline/unit/browser/build/performance gates pass for the completed tranche. | UI consistency and offline recoverability materially improve. A structured representative-staff validation session and remaining per-module form/accessibility cleanup are still required before closing observed workflow validation. |
| 2026-08-21 | Production-PWA certification reproduced a protected offline deep link that rendered only the shell while auth waited on an unreachable server. Cached, session-scoped clinic identity now unlocks offline startup immediately; a real service-worker regression passes in 2.0 seconds. Final local gates: frontend 46/46, offline 41/41, general Chromium 35/35, production-PWA Chromium 1/1, lint/build and six budgets green. | Offline startup is locally code- and browser-verified against the production artifact, not merely Vite development mode. CI/deployment verification and the observed clinic wording/recovery exercise remain explicitly open. |
| 2026-08-21 | Clinic evidence reproduced “one queued / zero sent” after manual sync: a recent interrupted row remained `in_flight` until the one-minute stale threshold. Staff-triggered retry now safely reclaims stranded in-flight rows immediately, and feedback distinguishes dependency, connectivity, and session blockers. Exact browser regression, 42/42 offline tests, lint/build, and all budgets pass locally. | The reported manual-sync blocker is code-complete and locally browser-verified. CI, deployment, and confirmation against the clinic’s existing queued record remain open. |
| 2026-08-21 | Clinic evidence reproduced an offline Reception dashboard with cached counters but an empty patient list. Reception now warms and reconstructs its scoped directory from patient records; cached patients can be searched/opened, admitted, and invoiced offline without a network wait. Exact 4/4 Reception browser matrix, 44/44 offline tests, lint/build, and six budgets pass locally. | The existing-patient continuity blocker is code-complete and locally browser-verified. CI, deployment, production verification, and the observed clinic exercise remain open. |
| 2026-08-21 | Reception “Imprimer reçu” depended only on an online PDF endpoint. A print-only local receipt now uses the durable provisional invoice/payment and prints while disconnected; the exact browser action passes with 46/46 unit, 44/44 offline, lint/build, and six budgets green. | Offline receipt printing is code-complete and locally browser-verified. CI, deployment, production verification, and physical-printer clinic validation remain open. |
| 2026-08-23 | Clinic print preview exposed the registration sheet and invoice superimposed. Reception now activates one print root at a time and uses the same invoice component online/offline; print-media regression proves invoice visible and registration hidden. | The overlapping-document defect is code-complete and locally browser-verified. Deployment and physical-printer clinic confirmation remain open. |
| 2026-08-24 | Clinic invoice evidence showed missing dossier, date/time, cashier, and print-audit values. Online responses now include canonical dossier/creator metadata; offline invoices snapshot equivalent fields; the shared template separates issue and print timestamps. Focused backend tests pass 14/14 and exact online/offline Chromium cases pass 2/2 with lint, build, and all performance budgets green. | Missing invoice metadata is code-complete and locally browser-verified for connected and disconnected workflows. CI, deployment, and physical-printer confirmation remain open. |
| 2026-08-24 | Clinic intake corrections added editable Reception patient records online/offline, preserved reported newborn/unknown ages in days, weeks, months, or years, and corrected the confirmed AASMA laboratory tariffs while retaining Progesterone at 300,000 GNF. Focused backend registration/update/tariff tests and 45/45 offline tests pass locally. | Patient editing, age-unit storage, and tariff corrections are code-complete and locally unit-verified. CI, deployment, production catalog synchronization, and clinic validation remain open. |
| 2026-08-24 | The second clinic-request review added non-pediatric hospitalization ordering with specialty, duration, explicit 30-day month conversion, standard-bed (200,000 GNF/day) or private-cabin (500,000 GNF/day) selection, server-authoritative totals, and admission placement for beds 1–12 or cabins 1–2. Focused backend tests pass 8/8; lint, production build, and all six performance budgets pass locally. | The clarified non-pediatric hospitalization and placement tranche is code-complete and locally verified. Pediatric hospitalization remains deliberately excluded pending clinic clarification; CI, migration deployment, production verification, and field validation remain open. |
| 2026-08-24 | CI run 32743844262 exposed stale migration-head assertions and an age backfill that assumed every recovery fixture retained the legacy `patients.age` column; the independent push-triggered deployment nevertheless completed in run 32743845716. The migration is now defensive, head assertions track `0032`, and automatic deployment waits for successful CI while preserving explicit manual dispatch. The exact local gates now pass: backend 444/444 with one skip and clinic regressions 246/246 with one skip. | The immediate CI compatibility defect and CI/deployment ordering gap are code-complete and locally verified; remote CI, gated redeployment, and production verification remain required before this fix is considered deployed. |
| 2026-08-24 | Clinic-admin navigation exposed “Administration” and “Utilisateurs” as separate top-level choices even though both opened the same administration page and both appeared active. The duplicate route is removed; staff listing and account creation remain explicit anchored sections inside Administration. The navigation contract passes 2/2, frontend unit suite 48/48, focused Chromium 1/1, lint/build, and all six performance budgets locally. | The false navigation choice is code-complete and locally browser-verified; CI, deployment, and clinic confirmation remain open. |
| 2026-08-24 | Clinic clarification established that the two pediatric hospitalization prices represent different accommodation types: berceau nouveau-né (80,000 GNF/day) and lit pédiatrique standard (120,000 GNF/day). Reception now exposes both only for pediatric specialties, resets incompatible selections when specialty changes, and the API rejects specialty/bed/catalog mismatches while applying the authoritative tariff. Focused backend tests pass 10/10; frontend 48/48, exact Reception Chromium 2/2, lint/build, and all six performance budgets pass locally. | Pediatric hospitalization pricing is code-complete and locally browser-verified. CI, deployment, production catalog verification, and clinic validation remain open. |
| 2026-08-24 | Competitive feature review selected complete ward/room/bed management as the preferred next product initiative and recorded clinic-scoped expense/cash management as a future addition. The accommodation roadmap explicitly separates physical beds, clinical suitability, and tariffs; the finance roadmap preserves existing billing as the patient-revenue source. | Product direction is documented only; neither capability is represented as implemented, tested, or scheduled. |
| 2026-08-24 | Clinic administration gained a persistent readiness model, guided setup route, daily handoff list, real-name staff provisioning, prompt-free password reset, and derived checks for staffing, payments, bed capacity, printing, offline operation, and a test patient journey. Full backend suite passes 449/449 with one skip; frontend unit tests pass 50/50; accessibility/responsive Chromium checks pass 10/10 with lint, production build, and all six performance budgets green. | Simplified onboarding foundation is code-complete, locally regression-verified, and browser-verified. Remote CI/deployment, secure credential delivery, and clinic-admin field validation remain open. |
| 2026-08-24 | [CI run 32753005661](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32753005661) passed all six jobs for `839864e`; [deployment run 32753287391](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32753287391) passed Railway/Vercel readiness and production smoke. Railway identifies `839864e`, and Vercel serves the new administration bundle. | The onboarding foundation is CI- and production-verified. Secure credential delivery, shift routines, broader browser scenarios, and observed clinic-admin validation remain open. |
| 2026-08-24 | Secure one-time staff activation and clinic opening/closing handoff routines were implemented with migration, tenant-scoped APIs, audit events, responsive administration UI, and focused security/shift regression coverage. Local backend 456/456 (plus one skip), frontend 50/50, offline 45/45, focused browser 2/2, lint, build, and six performance budgets pass. | Code-complete and locally verified. CI, production, and clinic-field validation remain open. |
| 2026-08-24 | [CI run 32756121047](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32756121047) passed all six jobs for `7807b08`; [deployment run 32756387226](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32756387226) passed. Railway reports exact commit `7807b08`, and Vercel serves `/activate-staff`. | Secure staff activation and operational shift handoff are production-verified. Observed clinic-admin validation remains open. |
| 2026-08-24 | Complete ward-management foundation added real clinic wards, stable regular-bed/berceau inventory, suitability attributes, six-state lifecycle, expected discharge and reservation metadata, immutable turnover events, transactional/versioned allocation, database overlap guards, and a responsive census/configuration workspace. Focused backend 28/28, frontend 50/50, offline 45/45, responsive Chromium 3/3, lint/build/budgets pass locally. | Core ward management is code-complete and locally verified. CI/deployment, two-user browser concurrency/reconnect proof, embedded Nursing/Reception summaries, and observed clinic turnover exercise remain open. |
| 2026-08-24 | [CI run 32760744306](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32760744306) passed every required job for `a61e30b`; [deployment run 32760965996](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32760965996) passed Railway, Vercel, and post-deployment smoke. Railway `/health/build` reports the exact commit and the public Hospitalization route returns HTTP 200. | Core ward management is production-verified. Embedded Nursing/Reception summaries, real-browser two-user concurrency/reconnect proof, and an observed clinic turnover exercise remain open. |
| 2026-08-24 | Clinic review exposed Unified Billing invoices as an unstructured raw list: paid records appeared under work to process, browser bullets leaked into the UI, actions and amounts were widely detached, and “PDF” did not describe the outcome. The cashier queue now separates pending/paid tabs, scopes the payment method to collection, presents compact invoice ledger cards with total/paid/balance, and uses explicit collection/download actions with progress states. A representative pending/paid fixture locks the exact 390 px browser state. Frontend 50/50, offline 45/45, responsive Chromium 3/3, full Chromium 38/38, lint/build, and all six performance budgets pass locally. CI run [32774294190](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32774294190) and deployment run [32774516227](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32774516227) passed; production reports commit `419b57d1b7be2a62ec72fcdca9604d0603bfb50d` and the live billing route returns HTTP 200. | Unified Billing queue redesign is code-complete, accessibility-checked, responsive-browser verified, CI-verified, and production-verified. Cashier field review remains open. |
| 2026-08-24 | Reception’s “Fermer le dossier” could immediately reopen the same patient because URL hydration observed the stale `patient` query value between state and route updates; older patient-loading work could also overwrite the close confirmation. Closing now guards that transition, invalidates stale patient requests, removes patient and tab URL state atomically, clears patient-derived registration/print/billing/refund state, returns to the neutral dashboard, confirms the outcome, and focuses patient search. The offline existing-patient browser journey now waits through the former race window and asserts the URL, safety strip, active tab, confirmation, and focus state. Exact Chromium 1/1 and full Chromium 38/38 pass, with frontend 50/50, offline 45/45, lint/build, and all six performance budgets green locally. CI run [32778710635](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32778710635) and deployment run [32778958496](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32778958496) passed; production reports exact commit `4e261003afd82ff3dbb75562be7a957fd0a605e4`, and the live Reception route returns HTTP 200. | Reception close-dossier correction is code-complete, CI-verified, and production-verified; clinic field confirmation remains open. |
| 2026-08-24 | Unified Billing exposed a detached global payment-method selector with no visible response, while “Encaisser” immediately submitted a full payment. Collection is now an invoice-level two-step workflow: opening an invoice reveals its exact amount, payment method, cancel action, and explicit confirmation beside the affected invoice. The shared formatter also presents `issued` as “Émise.” The responsive browser fixture proves opening, changing the method, cancelling without submission, reopening, and submitting the selected method. Frontend 50/50, offline 45/45, focused responsive Chromium 1/1, full Chromium 38/38, lint/build, and all six performance budgets pass locally. CI run [32780002776](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32780002776) and deployment run [32780244833](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32780244833) passed; production reports exact commit `d7d78fd810d655848cd6d59140ac144223216411`, and the live billing route returns HTTP 200. | Safer cashier collection interaction is code-complete, locally browser-verified, CI-verified, and production-verified; cashier field confirmation remains open. |
| 2026-08-24 | Invoice creation combined the selected billing date with midnight, so online invoice printouts showed `Heure : 00:00`. Invoice issuance now keeps the selected business date while preserving the actual creation time. API serialization also recovers the real `created_at` timestamp for legacy midnight rows, repairing existing affected printouts without fabricating a time. Online and offline browser print assertions reject midnight output, and deterministic backend regressions cover new and historical invoices. Focused backend billing tests pass 12/12; the serial online/offline invoice browser suite passes 5/5; frontend unit tests pass 50/50; lint, build, and all six performance budgets are green locally. CI run [32781331808](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32781331808) and deployment run [32781570916](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32781570916) passed; production reports exact commit `48d596f385038b6c5d3cb310c284e357b6b9c3bb`, and the live Reception route returns HTTP 200. | Billing-time correction is code-complete, locally browser-verified, CI-verified, and production-verified; clinic print confirmation remains open. |
| 2026-08-24 | The clinical reports page presented undifferentiated counters as oversized cards and raw full-width rows, obscuring the operational questions staff need to answer. It is now a compact clinical ledger: an explicit URL-backed period command bar with presets and apply semantics, export progress/error feedback, decision-focused KPIs, separated patient-flow and finance panels, appointment completion, service-revenue distribution, and an optional monthly program summary. Module-specific responsive CSS keeps the 390 px view free of horizontal overflow. Frontend 50/50, offline 45/45, focused accessibility/responsive Chromium 13/13, full Chromium 40/40, lint/build, and all six performance budgets pass locally. [CI run 32782935787](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32782935787) and [deployment run 32783160457](https://github.com/dialloao494-design/plateforme-sante-guinee/actions/runs/32783160457) passed; Railway reports exact commit `d70203aa21f0d25735db743a6d70e6c6dd2f5cd6`, and the public Reports route returns HTTP 200. | Clinical reporting redesign is code-complete, locally regression-verified, accessibility-checked, responsive-browser verified, CI-verified, and production-verified. Clinic-management field review remains open. |
| 2026-08-26 | The physician defect review was implemented as a clinical workflow correction: consultation actions expose deterministic progress and save before print; duplicate lab/imaging orientation controls are removed in favor of the actual order forms; doctors can no longer overwrite nurse-owned hospitalization vitals; discharge uses one structured authorization flow and its A4 print is constrained to one page; catalog-backed surgical acts retain code/tariff; structured prescriptions route to Pharmacy and appear in a dedicated doctor register. Backend 460/460 with one skip, frontend 51/51, the patient-context Chromium regression 1/1, lint, production build, and all six performance budgets pass locally. | Physician workflow tranche is code-complete and locally regression/browser-verified. CI, deployment, production verification, dedicated accessibility/responsive coverage, and doctor field validation remain open. |
| 2026-08-26 | The reported Nursing defects and continuity gaps were implemented as one append-only observation workflow. Vital signs now precede the consultation reason and include TA, temperature, pulse, respiration, SpO₂, pain, weight, height, BMI, PB, PC, consciousness, observations, and non-diagnostic review cues. The same patient workspace separates read-only physician prescriptions from nurse-entered clarifications, captures history, hospitalized surveillance, care planning, medication administration, specimens, wounds, safety checks, notes, and SBAR handoff, and exposes every saved observation immediately in chronological history. Offline saves now acknowledge locally in seconds, keep the patient open, show pending synchronization, and remain usable when the optional prescription cache is unavailable. The migration self-heals historical databases where the legacy nursing table is absent. Tenant-scoped prescription denial and exact online-to-offline browser coverage were added. Local evidence: backend **461 passed / 1 skipped**, frontend/domain **54/54**, offline **45/45**, full Chromium **41/41**, lint, production build, and all six performance budgets pass; no serious or critical accessibility violation was found in the Nursing workspace. | Nursing observation and continuity workflow is code-complete and locally regression-, accessibility-, responsive-browser-, tenant-, and offline-verified. Remote CI, deployment/production verification, validation of clinical alert thresholds, medication-administration wording, and observed nurse field acceptance remain open; this evidence does not claim hospital-wide readiness. |
| 2026-08-26 | A persistent full-surface browser acceptance gate now signs into all **11** application roles and audits every inventoried patient, platform-owner, administration, physician, reception, nursing, laboratory, pharmacy, nutrition, PEV, and cashier route at **1440 px** and **390 px**. The gate checks visible page titles, horizontal overflow, named actions, labeled controls, serious/critical WCAG violations, route stability, and unexpected browser errors. Its first run exposed and corrected unlabeled appointment controls, invalid Nursing tab semantics, a keyboard-inaccessible Pharmacy billing viewport, incomplete physician-message form/dialog semantics, missing patient-history failure hierarchy, unstable image dimensions, and the canonical pilot patient's missing clinic assignment. Local evidence: full-surface audit **11/11**, complete Chromium regression matrix **52/52**, backend **461 passed / 1 skipped**, frontend/domain **54/54**, offline **45/45**, lint, production build/PWA generation, and all six performance budgets pass. | Cross-role UI/UX assurance is code-complete and locally functional-, accessibility-, responsive-browser-, tenant-, offline-, build-, and performance-verified. Remote CI/deployment/production verification, physical printer/scanner/device validation, and observed clinic-staff workflow acceptance remain open; automated evidence does not claim that every real-world workflow is field-certified. |
| 2026-08-31 | At the clinic owner's explicit request, production clinic **17 — CLINIQUE AASMA** was reset in one clinic-scoped transaction. The owner explicitly waived a backup. The transaction deleted 45 patients and their patient-linked appointments, admissions, visits, consultations, vitals, invoices/items/payments/refunds, charges/payments, laboratory and imaging orders/results, prescriptions/items/pharmacy orders, nursing assessments, service requests, documents, medical records, and patient-linked clinical audit rows. An independent post-commit query returned zero for patients, appointments, admissions, invoices/payments, charges, consultations, laboratory, imaging, prescription, pharmacy, nursing, and service-request domains. It preserved 31 clinic users/staff and 175 clinic laboratory catalog entries; no ward, room, or bed configuration existed for this clinic at reset time. | Production reset is executed and database-verified. It is intentionally **not recoverable from a task-created backup** because the owner waived backup creation. Every clinic workstation must clear old offline site data before resuming operations so a browser-held queue cannot replay deleted records. The production database credential discovered in legacy source remains a security defect requiring immediate rotation and repository-history remediation. |
| 2026-08-31 | Clinic administration now exposes a complete, safety-tiered staff lifecycle: active users can be deactivated with immediate session/token revocation; previously activated users can be reactivated; and only inactive invitation accounts that have never logged in or activated can be permanently deleted. Self-deactivation/deletion and removal of the last active clinic administrator are blocked. Accounts with clinical history remain immutable identities and must be retained in a deactivated state. The personnel table presents explicit, spaced actions with confirmation dialogs and outcome feedback. Focused backend lifecycle/security tests pass **11/11**, frontend lint and production build pass. | Staff lifecycle controls are code-complete and locally unit/build verified. Full backend/browser regression, CI, deployment, production verification, and clinic-admin field acceptance remain open. |

## Related evidence

- [`STABILIZATION_FINDINGS_MATRIX.md`](STABILIZATION_FINDINGS_MATRIX.md)
- [`HISTORICAL_REGRESSION_MATRIX.md`](HISTORICAL_REGRESSION_MATRIX.md)
- [`OFFLINE_FAILURE_RECOVERY_MATRIX.md`](OFFLINE_FAILURE_RECOVERY_MATRIX.md)
- [`BACKUP_RESTORE.md`](BACKUP_RESTORE.md)
- [`SECURITY_CONTROL_AUDIT_2026-08-18.md`](SECURITY_CONTROL_AUDIT_2026-08-18.md)
- [`PRODUCTION_CHECKLIST.md`](PRODUCTION_CHECKLIST.md)
- [`FINAL_PRODUCTION_READINESS_REPORT.md`](FINAL_PRODUCTION_READINESS_REPORT.md)

The older “Production Ready: YES” report is a dated module/clinic validation
snapshot. It does not override the broader hospital-wide readiness gate here.
