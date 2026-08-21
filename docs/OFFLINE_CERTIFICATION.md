# Offline certification and clinic exercise

**Owner:** platform maintainers and clinic lead  
**Last code evidence:** 2026-08-21
**Field status:** open until the clinic exercise below is observed and signed

## Safety contract

- An offline patient receives a stable `offline_…` local ID immediately. This is
  an operational reference, not the final dossier number.
- The server remains the only authority that issues `PAT-…` dossier numbers.
- Admissions and invoices queued against a local patient ID wait for patient
  synchronization, then their patient references are remapped before replay.
- Exact concurrent registrations are prevented at the database boundary. A
  second device adopts the one canonical dossier; an intentional duplicate is
  still possible only through the explicit confirmation workflow.
- Corrupted derived cache entries are discarded. Corrupted durable mutations
  are quarantined and exported; they are never replayed as empty records.
- Recovery exports are clinic/user scoped, exclude stored request headers, and
  carry a versioned manifest whose record counts are validated before download.
  They contain health information and must be handled as confidential records.

## Automated matrix

| Scenario | Automated evidence | Expected result |
|---|---|---|
| Browser network loss → registration → invoice → reconnect | `e2e/reception-offline-registration.spec.js` | Local patient ID is usable for billing; one patient and one invoice replay; canonical dossier replaces all patient references. |
| Production PWA protected deep link after complete network loss | `e2e/pwa-offline-shell.spec.js` via `npm run test:pwa` | The installed/cached build serves `/clinical/reception`, restores the session-scoped clinic identity, renders Reception without an auth-network timeout, and shows offline state. |
| Restart while synchronization is in flight | Same browser spec | Stale in-flight work returns to pending and synchronizes after a new page/runtime starts. |
| Two devices register the same patient concurrently | Same browser spec | One canonical dossier; both devices adopt it; no duplicate patient. |
| Storage quota exhaustion | `tests/offline-outbox.test.mjs`, `apiError.test.mjs` | Existing work remains intact; new write fails explicitly; staff receive an actionable French message. |
| Corrupted patient cache | `tests/offline-failure-recovery.test.mjs` | Only the damaged derived cache row is removed; durable mutations remain. |
| Corrupted queued mutation or conflict | Same offline test | Content is quarantined, not sent, cannot be blindly retried, and every unreadable copy appears in the export integrity warnings. |
| Interrupted/stale in-flight row | `tests/offline-outbox.test.mjs` | Old in-flight work is recovered; active synchronization is untouched. |
| Recovery export validation | `recovery.js` and offline tests | A v2 manifest verifies mutation/conflict/warning counts and active clinic/user ownership; altered or cross-clinic bundles are rejected before hand-off. |

## Latest local release evidence

On 2026-08-21, the production-build PWA regression first reproduced a protected
route that showed only the cached shell while session bootstrap waited up to 15
seconds for an unreachable `/auth/me`. Offline bootstrap now immediately uses
the existing session-scoped cached profile and resumes server validation/sync on
reconnect. The corrected protected deep link rendered in 2.0 seconds with the
browser network fully disabled.

Local gates after the correction: 46/46 frontend unit tests, 42/42 offline
tests, 35/35 general Chromium tests, 1/1 production-service-worker Chromium
test, lint, production build, and all six performance budgets. This is local
verification only; CI, deployed production, and the observed clinic exercise
remain separate evidence states.

The same pass subsequently reproduced a recently interrupted mutation that was
still marked `in_flight`: the queue displayed one item but a manual retry sent
zero until the normal one-minute recovery age elapsed. An explicit staff retry
now safely reclaims every stranded in-flight row after any active replay has
finished. The browser regression marks a fresh registration in-flight, clicks
manual synchronization, and verifies the canonical dossier and completed queue.

## Clinic staff validation script

Run this on the clinic’s real workstation, browser, printer and normal network.
Use a clearly marked test patient. A platform maintainer observes without guiding
the wording interpretation.

1. Sign in as reception while online and confirm the offline status control is
   understandable when opened.
2. Disconnect the workstation network. Register the test patient.
3. Ask the receptionist what “ID local” and “synchronisation en attente” mean.
   Passing answer: the record is saved locally, the final dossier is pending,
   and the patient must not be registered again.
4. Open **Facturation**, add a consultation, and create the invoice while still
   offline. Confirm the queued message is understood.
5. Close and reopen the browser once while the work is queued. Confirm the work
   remains visible and the queue count is not lost.
6. Reconnect. Confirm the patient receives one `PAT-…` number and the invoice is
   attached to that same dossier. Search by phone and refresh the page.
7. With a maintainer-provided test failure row, open offline details, explain
   “échec permanent”, retry once, then use **Exporter pour récupération**.
8. Confirm staff know not to email or copy the recovery file to personal media,
   and know the clinic’s named support contact and secure transfer channel.

Record date, workstation/browser versions, staff role (not patient data), each
step pass/fail, confusing wording verbatim, observer, and follow-up owner. Only
then may the roadmap state move to `FIELD VALIDATED`.

## Recovery procedure

1. Do not clear browser data, uninstall the application, create a replacement
   patient, or repeat a financial entry.
2. Open the offline status control and try **Synchroniser** once when the network
   is stable.
3. If a permanent failure remains, select **Exporter pour récupération**.
4. Store the JSON file in the clinic-approved encrypted location and transfer it
   only to the authorized support contact.
5. Support reconciles each `client_request_id` against server records before any
   manual replay. Patient and financial records require two-person verification.
6. Delete the recovery file from the workstation only after reconciliation is
   documented and the clinic lead approves disposal.
