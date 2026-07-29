# Santé Guinée — Security Wave 2 Report

**Wave:** 2 — File uploads / PDF generation / Medical documents / Storage / Encryption / PHI / Download permissions / Malware / Integrity  
**Status:** COMPLETE  
**Date:** 2026-07-29  
**Branch:** `cursor/security-wave2-documents-ab76`

---

## 1. Implemented protections

| Area | Implementation |
|------|----------------|
| **File uploads** | MIME + extension sniffing, size limits, opaque storage keys under `uploads/secure` (unchanged + reinforced) |
| **Malware validation** | `core/attachment_malware.py` — `ATTACHMENT_VIRUS_SCAN=off\|stub\|clamav` (default off for clinic UX; stub rejects EICAR; clamav via pyclamd/clamscan) |
| **Encryption at rest** | Fernet via `ATTACHMENT_ENCRYPTION_KEY`; **mandatory in production** (`core/settings.py` boot guard) |
| **File integrity** | SHA-256 of plaintext stored on messages (`attachment_content_sha256`) and patient documents (`content_sha256`); verified on download (409 on mismatch) |
| **Download permissions** | Message attachments: clinic admins scoped to their clinic (IDOR fix); patient docs remain dossier-RBAC + audit |
| **PHI hygiene** | `file_path` / storage keys removed from patient document API responses; `download_url` only |
| **Download headers** | Shared `phi_download_headers()` — `no-store`, `nosniff`, safe `Content-Disposition`, optional `X-Content-SHA256` |
| **PDF generation** | `escape_pdf_paragraph` on consultation, lab report, and invoice PHI/user fields (`core/output_encoding.py`) |
| **Storage schema** | Additive migrations for integrity/MIME/filename columns (`ensure_message_attachment_columns`, `ensure_patient_document_security_columns`) |

---

## 2. Validation evidence

| Suite | Result | Artifact |
|-------|--------|----------|
| Wave 2 document security tests | **passed** (with attachment + dossier suites) | `evidence/security/WAVE2_PYTEST_DOCS.txt` |
| Full backend pytest | **217 passed** | `evidence/security/WAVE2_PYTEST_FULL.txt` |
| Production boot guard | ATTACHMENT_ENCRYPTION_KEY required | `tests/test_production_boot_guard.py` |

---

## 3. Ops notes

- Set `ATTACHMENT_ENCRYPTION_KEY` to a Fernet key before production deploy (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- Optional: `ATTACHMENT_VIRUS_SCAN=stub` in staging CI; `clamav` when ClamAV is installed on the host.
- Legacy plaintext attachments remain readable; new uploads encrypt when the key is set.
- Existing patient documents without `content_sha256` skip integrity verify until re-uploaded.

---

## 4. Remaining risks (later waves)

| Risk | Notes |
|------|-------|
| ClamAV not default-on | Offline clinics may lack scanner; enable when ops capacity exists |
| PDF watermarking / short-lived URLs | Architecture §29 — deferred |
| Backup dump encryption | Architecture § encryption — separate wave |
| Not every PDF builder escaped | Consultation / lab / invoice covered; refund/simple builders use separate escapes |

---

## 5. Verdict

**Security Wave 2 is COMPLETE.** All automated validations pass (217 pytest).
