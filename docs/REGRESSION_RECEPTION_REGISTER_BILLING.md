# Regression lock — Reception registration ID + Urgences billing specialty

Clinic report date: **08-08-26** (Dashbord Recep).

## Bug 1 — Enregistrement sans N° dossier

**Symptom:** After filling the registration form and clicking **Enregistrer**, data disappears / is accepted but no patient identifier is shown.

**Causes addressed:**
1. Offline/optimistic queue could return HTTP 202 without `patient_number`; UI treated it as success and cleared the form — or worse, queued silently while showing an error (duplicate outbox risk).
2. Successful online registration immediately wiped the form, so staff often missed the generated ID.
3. Two-phase DB commit left a short window where a patient row could exist without `patient_number`.

**Fix:**
- **Online-only HIS registration:** `POST /clinical/reception/his/patients` is not queueable (`entityTypes.js` / `isOnlineOnlyMutation`).
- Reject incomplete responses; network/offline errors show `REGISTRATION_ONLINE_REQUIRED_MESSAGE` (form preserved, no queue).
- Keep form fields filled until **Nouvel enregistrement**; show `data-testid="reception-patient-number"`.
- Assign `patient_number` via `flush` + single `commit`.

**Gates:** `tests/test_reception_patient_number_generation.py`, `registrationSuccess.test.mjs`, offline-pure `HIS patient registration is online-only`.

## Bug 2 — Urgences → spécialité changée à la facture

**Symptom:** Service **Urgences**, specialty selected, line looks correct in the products table; clicking **Créer la facture** rewrites the line to **Consultation spécialisée** (wrong label + specialized price).

**Root cause:** Emergency lines sent specialty `catalog_code` (e.g. `medicine`). Server `resolve_billing_catalog_item` always mapped specialty codes to specialized label/price.

**Fix:**
- `price_variant: "emergency" | "specialized"` on invoice line items.
- Catalog resolve uses `emergency_price_gnf` + `Consultation d'urgences — …` when variant is emergency.
- **Server validates variant against invoice `department`** — emergency tariff cannot be selected under a specialized/external department without privileged override + audit reason.
- When `price_variant` is omitted, infer from **department** (not free-text description).
- Clear shared specialty state when billing department changes (avoids stale « Autre » labels).

**Gates:** `tests/test_reception_emergency_specialty_invoice.py` (incl. mismatch rejection), `buildInvoiceItemPayload.test.mjs`.
