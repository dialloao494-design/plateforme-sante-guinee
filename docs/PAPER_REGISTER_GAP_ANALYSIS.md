# Paper Register Gap Analysis — Centre de Santé Koloma

**Date:** 2026-05-25  
**Scope:** Digital modules vs. paper registers used at Koloma

## Summary

| Module | Paper parity | Gap level |
|--------|-------------|-----------|
| PEV / Vaccination | **95%** | Minor |
| Hospitalization | **90%** | Minor |
| Nursing Care | **92%** | Minor |
| Nutrition | **88%** | Moderate |
| Laboratory | **85%** | Moderate |
| Pharmacy | **80%** | Moderate |

---

## PEV / Vaccination

| Paper column / workflow | Digital equivalent | Status |
|-------------------------|-------------------|--------|
| Date, child name, sex, DOB, age | Register row + patient snapshot | ✅ |
| Mother/guardian, quartier | `mother_or_guardian`, `address` | ✅ |
| Vaccine, dose, lot, expiry | Full PEV form fields | ✅ |
| Injection site, strategy, vaccinator | Field options API | ✅ |
| Next appointment | `next_appointment_date` | ✅ |
| AEFI / observations | `notes`, `aefi_notes` | ✅ |
| Monthly tally by vaccine | Monthly report + register | ✅ |
| Missed / due tracking | Status API (due/missed/upcoming) | ✅ |
| **Daily pointage (same-day list)** | Procedures list by date only | ⚠️ Partial — use register filtered by day |
| **Printed monthly register PDF** | CSV/PDF export | ❌ Missing — manual screen only |

---

## Hospitalization

| Paper workflow | Digital | Status |
|----------------|---------|--------|
| Admission date, diagnosis, clinician | Admission form | ✅ |
| Bed assignment | Assign bed API | ✅ |
| Discharge date, outcome | Status update + outcome | ✅ |
| Length of stay | Auto-calculated | ✅ |
| Occupancy / lits | Occupancy dashboard | ✅ |
| Monthly admission register | `register_rows` in monthly report | ✅ |
| **Separate discharge register book** | Discharge summaries API | ⚠️ Partial — merged in admission register |
| **Printed discharge slip (duplicate)** | Discharge PDF | ✅ exists |
| Ward/room paper log | Room/bed management | ✅ |

---

## Nursing Care

| Paper pointage | Digital | Status |
|----------------|---------|--------|
| Injection | `procedure_type=injection` | ✅ |
| Perfusion | `procedure_type=perfusion` | ✅ |
| Pansement | `procedure_type=dressing` | ✅ |
| Suture | `procedure_type=suture` | ✅ |
| Date, time, nurse, notes | All fields including `procedure_time` | ✅ |
| Daily register | Procedures list + daily tally in monthly report | ✅ |
| Monthly register | `/clinical/nursing-care/register` | ✅ |
| Monthly statistics | By type + daily tally | ✅ |
| **Signature infirmier (paper)** | Text name only | ⚠️ No digital signature |

---

## Nutrition

| Paper workflow | Digital | Status |
|----------------|---------|--------|
| Weight, height, MUAC | Assessment form | ✅ |
| Nutritional diagnosis | `nutritional_diagnosis` | ✅ |
| Follow-up date | `follow_up_date`, `is_follow_up` | ✅ |
| Recommendations | `recommendations` | ✅ |
| Status classification | Auto MUAC classification | ✅ |
| Monthly register | `/clinical/nutrition/register` | ✅ |
| Active / due dashboard | `follow_up_due`, `active_patients` | ✅ |
| **WHO growth chart plotting** | Not implemented | ❌ Missing |
| **Anthropometric z-scores** | Not calculated | ❌ Missing |
| **Printed nutrition card for mother** | No PDF | ❌ Missing |

---

## Laboratory

| Paper workflow | Digital | Status |
|----------------|---------|--------|
| Test request (médecin) | Lab order from consultation | ✅ |
| Sample collection status | Order status workflow | ✅ |
| Results entry + validation | Lab result + validate | ✅ |
| Result history per patient | Timeline + validated results | ✅ |
| Test catalog (NFS, ECBU, HIV, etc.) | `/clinical/lab/catalog` | ✅ |
| Monthly activity report | Monthly report + by category | ✅ |
| **Pre-printed request form layout** | Generic order form | ⚠️ Partial |
| **Structured result fields per test type** | Free-text summary only | ⚠️ Partial |
| **Daily lab register (separate book)** | Queue view only | ⚠️ Partial |

---

## Pharmacy

| Paper workflow | Digital | Status |
|----------------|---------|--------|
| Dispensing linked to patient | Pharmacy orders from Rx | ✅ |
| Stock inventory | Inventory API | ✅ |
| Low stock alerts | Dashboard `low_stock_count` | ✅ |
| Stock movements | Local movements log (UI) | ⚠️ Partial — not full ledger |
| Monthly dispensing register | Monthly report `register_rows` | ✅ |
| Daily dispensing count | `dispensed_today` | ✅ |
| **Paper sales notebook (cash amounts)** | Billing charges separate | ⚠️ Partial — revenue in billing module |
| **Batch/expiry on every dispense line** | Inventory has batch; dispense line does not | ⚠️ Partial |
| **Printed dispensing label** | No label print | ❌ Missing |

---

## Priority gaps for field use (tomorrow)

1. **PDF export** for monthly registers (PEV, nursing, nutrition, hospitalization, lab, pharmacy) — staff expect printable books.
2. **WHO growth charts** for nutrition — high value for Koloma child monitoring.
3. **Structured lab result templates** per test type — reduces free-text errors.
4. **Pharmacy batch tracking on dispense** — traceability for audits.

## Non-blocking (future sprints)

- Digital nurse signatures
- Offline mode (see OFFLINE_STRATEGY_ROADMAP.md)
- Separate discharge register view (can use discharge summaries today)
