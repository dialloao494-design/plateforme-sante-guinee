# Regression lock — Reception registration ID + Urgences billing specialty

Clinic report date: **08-08-26** (Dashbord Recep). Stabilization update: offline registration restored with reconciliation (no online-only bypass).

## Bug 1 — Enregistrement sans N° dossier

**Symptom:** After filling the registration form and clicking **Enregistrer**, data disappears / is accepted but no patient identifier is shown.

**Root causes:**
1. Offline optimistic responses were treated as hard failures *or* silent successes without a dossier number.
2. Converting registration to online-only violated the product requirement for clinic continuity offline.
3. Two-phase DB commit left a null-`patient_number` window (fixed via flush + single commit).

**Production design (current):**
- Offline / network failure **queues** HIS registration in the durable outbox (`queueable: true`).
- UI shows explicit **queued** state; submit disabled; staff told not to re-enter the same patient.
- Fingerprint dedupe prevents a second outbox row for the same phone/name/DOB while pending.
- On sync, `reconcilePatientCreate` maps temp `offline_*` id → server `{id, patient_number}` and updates the registration screen.
- Server idempotency via `X-Client-Request-Id` prevents double-create on ambiguous retries.

**Gates:** `test_reception_patient_number_generation.py`, `test_reception_register_idempotency.py`, `registrationSuccess.test.mjs`, `reconcilePatient.test.mjs`, offline-pure queueable classify.

## Bug 2 — Urgences → spécialité changée à la facture

**Symptom:** Service **Urgences**, specialty selected, line looks correct; **Créer la facture** rewrites to **Consultation spécialisée**.

**Fix:** `price_variant` + department validation (emergency tariff cannot be selected under specialized/external department without privileged override). Specialty state cleared on department change.

**Gates:** `test_reception_emergency_specialty_invoice.py`, `buildInvoiceItemPayload.test.mjs`.
