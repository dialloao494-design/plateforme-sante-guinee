# Offline Strategy & Implementation Roadmap

**Context:** Centre de Santé Koloma and rural Guinea clinics face unreliable internet.  
**Current state:** Online-first SPA + REST API (no offline support today).

---

## Design principles

1. **Reception is the gate** — patient creation must eventually sync to central record.
2. **Queue locally, sync centrally** — no duplicate patient IDs after sync.
3. **Conflict = server wins** for clinical facts; **client wins** for draft notes with merge UI.
4. **Modules by priority:** Reception → Nursing pointage → PEV → Pharmacy dispensing.

---

## Target architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PWA Frontend   │────▶│  IndexedDB cache │────▶│  Sync queue     │
│  (Service Worker)│     │  patients, forms │     │  (outbox table) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │ online
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  Railway API    │
                                                  │  + idempotency  │
                                                  └─────────────────┘
```

---

## Phase A — Read-only offline (4 weeks)

| Item | Description |
|------|-------------|
| Service worker | Cache static assets + `/clinical/*` shell |
| Patient lookup cache | Last 500 patients seen at this clinic (IndexedDB) |
| Read-only timeline | Show cached timeline when offline |
| Offline banner | Clear UX: "Mode hors ligne — saisie désactivée" |

**Deliverable:** Staff can look up recently seen patients without network.

---

## Phase B — Write queue (6 weeks)

| Item | Description |
|------|-------------|
| Outbox pattern | Local queue table: `{action, payload, client_uuid, created_at}` |
| Idempotent API | `X-Client-Request-Id` header on POST endpoints |
| Sync worker | Background retry on `online` event + exponential backoff |
| Nursing + PEV forms | First write-capable offline modules (simple forms) |

**Conflict rules:**
- Same patient + same day + same procedure type → dedupe on server.
- Patient create with duplicate phone → server returns existing patient, client remaps ID.

---

## Phase C — Full clinical offline (8 weeks)

| Module | Offline scope |
|--------|---------------|
| Reception | Register patient, start visit |
| Nursing | Full pointage notebook |
| PEV | Vaccination register |
| Pharmacy | Dispense from pre-synced stock snapshot |
| Lab | Sample collection status only (results require online) |

---

## Phase D — Reporting & resilience (4 weeks)

- Pre-compute monthly registers on server; cache PDFs in CDN.
- SMS fallback for critical alerts (stock bas, RDV PEV) via Africa's Talking.
- Local export CSV when sync blocked > 24h.

---

## Technology choices

| Layer | Recommendation |
|-------|----------------|
| Frontend cache | IndexedDB via Dexie.js |
| Sync | Workbox + custom sync manager |
| Backend | Idempotency keys + `sync_events` audit table |
| Conflict UI | Simple modal: "Conflit détecté — conserver version serveur" |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Duplicate patients | Client UUID + phone dedup on server |
| Stock oversell offline | Reserve stock on dispense intent; reconcile on sync |
| Data loss on device | Export outbox daily; encrypted backup |
| Staff training | Start with nursing pointage only (lowest risk) |

---

## Current readiness

| Capability | Status |
|------------|--------|
| Offline read | ❌ Not implemented |
| Offline write | ❌ Not implemented |
| Sync queue | ❌ Not implemented |
| PWA install | ⚠️ Partial (Vercel SPA, no service worker) |
| API idempotency | ❌ Not implemented |

**Offline readiness: NOT READY for field use.**  
**Recommended for go-live tomorrow:** Online-only with mobile hotspot backup at Koloma.

---

## Immediate mitigations (no code — for tomorrow)

1. Download monthly register PDFs/screenshots at end of each day while online.
2. Designate one "sync station" with best connectivity at the centre.
3. Keep paper registers as backup for first week; enter data during connectivity windows.
4. Pre-load patient search results for known follow-up lists each morning.
