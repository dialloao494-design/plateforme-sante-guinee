# Phase 3 E2E Acceptance — Backups, sync deltas, conflicts, license

- **Status:** ACCEPTED
- **Timestamp UTC:** 2026-07-28T17:50:50Z
- **Run directory:** `evidence/clinic-node/e2e-phase3-5/20260728T175050Z/`
- **Console log:** `evidence/clinic-node/phase3-5-e2e-console.txt`
- **Validator:** `deploy/clinic-node/scripts/validate-e2e-phase3-5.sh`

## Criteria

| Criterion | Result |
|-----------|--------|
| Local license jeton issued/validated (`state=OK`) | PASS |
| Delta sync outbox enqueue / list / ack | PASS |
| Conflict detection/storage | PASS |
| Local `pg_dump` backup succeeds (≥200 bytes `.sql.gz`) | PASS (20 457 bytes) |

## Evidence artifacts

- `01-license.json`, `02-outbox-enqueue.json`, `03-outbox-list.json`, `04-outbox-ack.json`
- `05-conflict.json`, `06-conflicts-list.json`, `07-backup.json`
- Durable backups under `deploy/clinic-node/data/backups/` (gitignored)

## Notes

- Heartbeat disk counters use **BIGINT** (Integer overflow previously broke related ops paths).
- Backend image ships **postgresql-client-16** to match Postgres 16.

## Summary

**Phase 3 E2E acceptance: ALL CRITERIA PASSED**
