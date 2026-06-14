# Clinic Acceptance Checklist

Use this checklist during **UAT on staging** with real clinic staff (réception, médecin, laboratoire, pharmacie, caissier, manager). Each item must be signed off before production go-live.

**Environment:** Staging with `ENVIRONMENT=staging`, PostgreSQL, HTTPS, pilot seed **disabled**.

---

## A. Access & roles

| # | Scenario | Role | Pass | Tester | Date |
|---|----------|------|:----:|--------|------|
| A1 | Login with clinic-assigned staff account | Réception | ☐ | | |
| A2 | Login with doctor account | Médecin | ☐ | | |
| A3 | Login with lab technician account | Laboratoire | ☐ | | |
| A4 | Login with pharmacist account | Pharmacie | ☐ | | |
| A5 | Login with cashier account | Caissier | ☐ | | |
| A6 | Login with clinic manager account | Manager | ☐ | | |
| A7 | Patient portal login (telehealth) still works independently | Patient | ☐ | | |
| A8 | Staff cannot access another clinic's patients via search | Réception | ☐ | | |

---

## B. Patient registration & search

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| B1 | Register new walk-in patient (name, age, gender, phone) | ☐ | |
| B2 | Duplicate phone number rejected with clear message | ☐ | |
| B3 | Search patient by last name (clinic-scoped results only) | ☐ | |
| B4 | Search patient by phone partial match | ☐ | |

---

## C. Appointments & check-in

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| C1 | Create appointment (patient + doctor + date/time) | ☐ | |
| C2 | Reception queue shows scheduled appointment | ☐ | |
| C3 | Check-in updates status to "checked in" | ☐ | |
| C4 | 48h and 24h reminders scheduled automatically | ☐ | Verify in DB or admin view |

---

## D. Consultation & orders

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| D1 | Doctor starts consultation from queue | ☐ | |
| D2 | Doctor views patient medical history panel | ☐ | |
| D3 | Doctor orders lab test from consultation | ☐ | |
| D4 | Doctor orders imaging (radiology) from consultation | ☐ | |
| D5 | Doctor writes prescription | ☐ | |

---

## E. Laboratory

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| E1 | Lab queue shows pending order | ☐ | |
| E2 | Enter lab result | ☐ | |
| E3 | Validate result | ☐ | |
| E4 | Download lab result PDF | ☐ | |
| E5 | Result appears in patient documents | ☐ | |

---

## F. Radiology

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| F1 | Radiology worklist shows imaging order | ☐ | |
| F2 | Enter radiology report | ☐ | |
| F3 | Doctor validates report | ☐ | |
| F4 | Report attached to patient record | ☐ | |

---

## G. Pharmacy

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| G1 | Pharmacy queue shows prescription order | ☐ | |
| G2 | Mark order as dispensed | ☐ | |
| G3 | Add/update inventory item (SKU, quantity, reorder level) | ☐ | |
| G4 | Low-stock items visible | ☐ | |

---

## H. Billing

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| H1 | Pending charges appear after consultation/lab/pharmacy | ☐ | |
| H2 | Pay charge with cash at reception | ☐ | |
| H3 | Pay charge with Orange Money | ☐ | |
| H4 | Generate unified invoice for visit | ☐ | |
| H5 | Pay unified invoice | ☐ | |
| H6 | Download invoice PDF | ☐ | |
| H7 | Daily revenue report shows collected amount > 0 | ☐ | |

---

## I. Hospitalization & beds

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| I1 | Create admission from consultation | ☐ | |
| I2 | View available beds by ward | ☐ | |
| I3 | Assign patient to bed | ☐ | |
| I4 | Transfer or release bed | ☐ | |

---

## J. Discharge

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| J1 | Discharge checklist shows prerequisites | ☐ | |
| J2 | Block discharge if billing incomplete | ☐ | |
| J3 | Execute discharge after billing validated | ☐ | |
| J4 | Download discharge summary PDF | ☐ | |
| J5 | Record archived to EMR | ☐ | |

---

## K. Medical history & reports

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| K1 | Doctor views consolidated medical history | ☐ | |
| K2 | Manager exports clinical report CSV | ☐ | |
| K3 | Manager downloads clinical report PDF | ☐ | |
| K4 | Revenue summary matches paid charges | ☐ | |

---

## L. WhatsApp reminders

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| L1 | WhatsApp webhook verified with Meta | ☐ | |
| L2 | Test reminder sent to patient phone | ☐ | |
| L3 | Patient confirms via WhatsApp → status updated | ☐ | |
| L4 | Patient cancels via WhatsApp → appointment cancelled | ☐ | |
| L5 | Patient requests reschedule → staff notification appears | ☐ | |
| L6 | Notification center shows event for reception | ☐ | |

---

## M. Security acceptance

| # | Scenario | Pass | Notes |
|---|----------|:----:|-------|
| M1 | Weak password rejected at registration | ☐ | e.g. `password1` |
| M2 | No demo login buttons visible in production build | ☐ | |
| M3 | API docs disabled in production (`/docs` → 404) | ☐ | |
| M4 | File upload rejects unsupported file type | ☐ | |
| M5 | Cross-clinic invoice access denied | ☐ | |

---

## Acceptance sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Clinic director | | | |
| Head of reception | | | |
| IT / vendor | | | |

**Minimum for acceptance:** All items in sections A–L marked Pass, plus all items in section M.

**If any item fails:** Log defect with steps to reproduce; do not proceed to production until resolved and re-tested.
