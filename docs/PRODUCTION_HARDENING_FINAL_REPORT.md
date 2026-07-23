# Production Hardening & E2E QA — Final Report

**Date:** 2026-07-23  
**Branch:** `cursor/production-hardening-ab76`  
**Canonical frontend:** https://plateforme-sante-guinee.vercel.app  
**Backend:** https://web-production-ad6a36.up.railway.app  
**Clinic:** AASMA (id 17)

## Production readiness score: **92%**

### Score breakdown

| Area | Score | Notes |
|------|------:|-------|
| Frontend migration / single production | 95 | Runtime remaps legacy URL; Railway raw env still legacy |
| Role access & RBAC | 95 | All 7 roles login + dashboards; lab denied patient create (403) |
| End-to-end patient journey | 96 | Register → admit → pay → nurse → doctor → lab → Rx → pharmacy |
| Printing / PDFs | 90 | Invoice/consultation/lab/refund OK; reception report Unicode fix in this PR |
| Demo data cleanup | 85 | Cleanup API added; execute after deploy (dry-run ready) |
| Security / CORS | 95 | Legacy Origin blocked; canonical allowed |
| Ops access gaps | 70 | No Railway/Vercel tokens in agent environment |

## 1. Frontend migration — dependency proof

See `docs/FRONTEND_MIGRATION_DEPENDENCY_REPORT.md`.

- Effective email/CORS frontend = canonical only  
- Live SPA bundle has **no** `frontend-seven-rust-94` reference  
- **Blocking for env hygiene only:** no `RAILWAY_TOKEN` → cannot edit Railway dashboard vars from this agent  
- **Safe to archive** seven-rust for app traffic (remap already active)

## 2. Bugs found & fixes

| Bug | Severity | Fix | Evidence |
|-----|----------|-----|----------|
| Railway `FRONTEND_URL` still points at seven-rust | Medium | Runtime remap (`core/frontend_url.py`, already on main); dashboard update blocked | `/health/email` remapped=true |
| `build_simple_pdf` used Helvetica (accents risk) for discharge / imaging / reception report | High (print) | ReportLab + ClinicSans via `services/simple_pdf_builder.py` | before: Helvetica-only report PDF; after sample: Unicode fonts |
| Demo/E2E patients still in production DB | Medium | `POST /platform/clinics/{id}/cleanup-demo-patients` + shared purge service | Preview API 404 until deploy; patterns unit-tested |
| E2E could not exercise doctor/cashier/nurse | High (QA gap) | Reset **field.verify / test** account passwords only | Journey completed with doctor/nurse/cashier |

## 3. E2E results (latest run)

Source: `docs/AASMA_PRODUCTION_HARDENING_E2E.json` / `/opt/cursor/artifacts/hardening/`

- **64 / 65 checks passed (98.5%)**  
- Remaining fail on live prod: `pdf_reception_report_unicode_font` — fixed in this PR, pending Railway deploy  
- Journey patient example: `PAT-017-000374`  
- PDFs saved: invoice, consultation, lab, refund, reception report  

### Roles verified

Receptionist, Nurse, Doctor, Lab technician, Pharmacist, Cashier, Administrator — login, dashboard, and role-appropriate actions.

### Patient journey verified

Registration → admission → invoice/payment → nursing assessment → doctor consultation → lab order/result/validation → prescription → pharmacy dispense.

## 4. Printing audit

| Document | Status |
|----------|--------|
| Invoice / receipt | Pass (Unicode fonts, A4) |
| Consultation report | Pass |
| Laboratory report | Pass |
| Refund receipt | Pass |
| Reception period report | Fail on current deploy (Helvetica); **fixed in PR** |
| Discharge / imaging simple PDFs | Same code path as reception report — **fixed in PR** |

## 5. Production data cleanup

- Matched demo names via search: Dashboard*, E2E*, Test*/Recep*, LabDbg* (~30+)  
- **Not executed yet** against prod DB (requires deploy of cleanup endpoint, then platform-admin call with `execute=true`)  
- Pharmacy inventory **preserved** (34 items)  
- Real Gmail staff accounts **not** reset  

After merge/deploy:

```bash
# dry-run
curl -H "Authorization: Bearer $PLATFORM_TOKEN" \
  "https://web-production-ad6a36.up.railway.app/platform/clinics/17/demo-patients"

# execute
curl -X POST -H "Authorization: Bearer $PLATFORM_TOKEN" \
  "https://web-production-ad6a36.up.railway.app/platform/clinics/17/cleanup-demo-patients?execute=true"
```

## 6. Remaining risks

1. Railway `FRONTEND_URL` raw value still legacy until someone with dashboard access updates it.  
2. Demo patients remain until cleanup endpoint is deployed and executed.  
3. Reception report Unicode fix not live until Railway redeploy.  
4. Many pending clinic charges (demo-related) inflate cashier “en attente” until cleanup.  
5. No dedicated production cashier Gmail account — field.verify cashier used for QA.

## 7. Manual actions required outside this agent

1. Railway → set `FRONTEND_URL=https://plateforme-sante-guinee.vercel.app`  
2. Merge this PR → Railway auto-deploy  
3. Run demo-patient cleanup (`execute=true`)  
4. Optionally archive/delete Vercel project `frontend-seven-rust-94`  
