# Phase 0 E2E Acceptance Report

- Timestamp UTC: 20260728T133741Z
- Host: cursor
- Network mode: host
- HTTP_PORT=8088 HTTPS_PORT=8443

## Criteria results


## 1. Fresh installation on a clean machine
- [x] PASS: Fresh installation completed on clean data directory

## 2. PostgreSQL starts automatically

## 3. FastAPI starts automatically
- [x] PASS: PostgreSQL starts automatically and accepts connections
- [x] PASS: FastAPI starts automatically - container healthy

## 4. Frontend is accessible over HTTPS
- [x] PASS: Frontend is accessible over HTTPS

## 5. API can read and write to PostgreSQL
- [x] PASS: API read path to PostgreSQL works via health/ready
- [x] PASS: API can write and read PostgreSQL through application engine

## 6. Full machine reboot simulated

## 7. Everything starts automatically after reboot

## 8. No manual intervention required
- [x] PASS: Full reboot simulation executed - cold stop then single compose up -d
- [x] PASS: Everything started automatically after reboot
- [x] PASS: No manual per-service intervention required

## 9. Health endpoint returns READY
- [x] PASS: Health endpoint returns READY with database ok
- [x] PASS: PostgreSQL data survived reboot

## Summary

**Phase 0 E2E acceptance: ALL CRITERIA PASSED**

Evidence directory: `evidence/clinic-node/e2e-phase0/20260728T133741Z/`

