# Offline failure / recovery matrix

Maps network-loss and outbox edge cases to automated coverage.
Core requirement: offline queueing must never be converted to online-only bypass.

## Playwright E2E (`frontend-sante/frontend/e2e/`)

| Scenario | Description | Coverage | Spec |
|---|---|---|---|
| **a** | Network loss **before** request | Queued registration, no invented PAT- number | `reception-offline-registration.spec.js`, `offline-failure-recovery.spec.js` |
| **b** | Network loss **during** request (abort mid-flight) | Route abort → queued state | `offline-failure-recovery.spec.js` |
| **c** | Server commit before response (delayed response + offline) | Best-effort: delay + offline queue + reconnect reconcile | `offline-failure-recovery.spec.js` |
| **d** | Browser reload with pending outbox | IndexedDB row survives reload; sync drains on reconnect | `offline-failure-recovery.spec.js` |
| **e** | Repeated reconnects | Toggle offline/online; outbox eventually empty | `offline-failure-recovery.spec.js` |
| **f** | Duplicate submissions (double-click / same fingerprint) | Single outbox row reused | `offline-failure-recovery.spec.js` |
| **g** | Logout → login as another user | Outbox purged; no reception queued UI leak | `offline-failure-recovery.spec.js` |
| **h** | Sync conflicts | No conflict resolution UI in SPA yet | **Unit** — `tests/offline-failure-recovery.test.mjs` (`detectAndRecordConflict`) |

## Unit / integration (`frontend-sante/frontend/tests/`)

| Scenario | Test file | Notes |
|---|---|---|
| Outbox idempotency (`client_request_id`) | `offline-outbox.test.mjs` | Duplicate enqueue |
| Owner-scoped pending count | `offline-pure.test.mjs` + `offline-failure-recovery.test.mjs` | Cross-user replay skipped |
| Replay skip wrong owner | `offline-failure-recovery.test.mjs` | `replayOutboxItem` → `skipped` |
| Logout purge | `offline-failure-recovery.test.mjs` | `clearOfflineDatabase` |
| Legacy unscoped rows ignored | `offline-failure-recovery.test.mjs` | `getPendingOutbox` filter |
| Conflict LWW merge | `offline-pure.test.mjs` | `resolveLastWriteWins` / `mergeLastWriteWins` |
| Patient dossier reconcile | `reconcilePatient.test.mjs` | Post-sync PAT- assignment |
| Temp→server dependent remap | `remapPatientRefs.test.mjs` | Admission/billing rewrite |
| Registration queued vs failure | `registrationSuccess.test.mjs` | UI contract |

## npm scripts

- `npm run test:e2e:offline-recovery` — offline failure/recovery Playwright suite
- `npm run test:offline` — Node unit tests (pure + outbox + failure-recovery + reconcile + remap)

## Not fully simulable in browser E2E

| Gap | Mitigation |
|---|---|
| True DB commit with TCP reset before HTTP response | Unit replay + backend idempotency (`test_reception_register_idempotency.py`) |
| Multi-device concurrent offline edits | Documented partial; conflict rows unit-tested |
| Conflict resolution UI | Pending product work; conflicts stored in IndexedDB only |
