/**
 * Durable offline failure/recovery unit coverage (IndexedDB + sync replay).
 * Run: npm run test:offline
 */
import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { offlineDb, clearOfflineDatabase } from '../src/offline/db.js';
import {
  enqueueMutation,
  getPendingOutbox,
  OUTBOX_STATUS,
} from '../src/offline/outbox.js';
import { detectAndRecordConflict } from '../src/offline/conflict.js';
import { replayOutboxItem } from '../src/offline/sync.js';

function mockScope(userId = '42', clinicId = '7') {
  const storage = {
    user_id: String(userId),
    sg_auth_profile: JSON.stringify({ id: userId, clinic_id: clinicId }),
  };
  const sessionStorage = {
    getItem(key) {
      return storage[key] ?? null;
    },
    setItem(key, value) {
      storage[key] = value;
    },
    removeItem(key) {
      delete storage[key];
    },
    clear() {
      Object.keys(storage).forEach((k) => delete storage[k]);
    },
  };
  const localStorage = {
    getItem() {
      return null;
    },
    setItem() {},
    removeItem() {},
    clear() {},
  };
  global.sessionStorage = sessionStorage;
  global.localStorage = localStorage;
  global.window = { sessionStorage, localStorage };
}

before(async () => {
  await offlineDb.open();
});

after(async () => {
  await clearOfflineDatabase();
  offlineDb.close();
});

test('replayOutboxItem skips rows owned by another user', async () => {
  mockScope('10', '1');
  const { client_request_id: reqId } = await enqueueMutation({
    method: 'post',
    url: '/clinical/reception/his/patients',
    data: { first_name: 'A' },
    clientRequestId: 'owner-a-req',
    entityType: 'patient',
  });

  mockScope('99', '1');
  const row = await offlineDb.outbox.where('client_request_id').equals(reqId).first();
  const client = { post: async () => ({ status: 201, data: { id: 1 } }) };
  const result = await replayOutboxItem(row, client);
  assert.equal(result, 'skipped');
});

test('detectAndRecordConflict records scoped conflict row (scenario h unit coverage)', async () => {
  await offlineDb.conflicts.clear();
  mockScope('55', '3');
  const outcome = await detectAndRecordConflict({
    clientRequestId: 'conflict-req-1',
    entityType: 'patient',
    entityId: 'offline_abc',
    localPayload: { record_version: 2, note: 'local', updated_at: '2026-03-01' },
    remotePayload: { record_version: 1, note: 'remote', updated_at: '2026-01-01' },
  });
  assert.equal(outcome.conflict, true);
  const rows = await offlineDb.conflicts.toArray();
  assert.equal(rows.length, 1);
  assert.equal(rows[0].owner_key, '55:3');
});

test('clearOfflineDatabase purges pending outbox (logout privacy contract)', async () => {
  mockScope('12', '2');
  await enqueueMutation({
    method: 'post',
    url: '/clinical/reception/his/patients',
    data: { first_name: 'B' },
    clientRequestId: 'purge-req',
    entityType: 'patient',
  });
  assert.ok((await getPendingOutbox()).length >= 1);
  await clearOfflineDatabase();
  await offlineDb.open();
  const pendingAfter = await offlineDb.outbox
    .where('status')
    .anyOf([OUTBOX_STATUS.PENDING, OUTBOX_STATUS.FAILED, OUTBOX_STATUS.IN_FLIGHT])
    .count();
  assert.equal(pendingAfter, 0);
});

test('getPendingOutbox ignores legacy rows without owner_key', async () => {
  mockScope('20', '4');
  await offlineDb.outbox.add({
    client_request_id: 'legacy-unscoped',
    owner_key: null,
    user_id: null,
    clinic_id: null,
    entity_type: 'patient',
    operation: 'create',
    method: 'POST',
    url: '/clinical/reception/his/patients',
    payload_json: '{}',
    params_json: null,
    headers_json: '{}',
    record_version: 1,
    optimistic_json: '{}',
    status: OUTBOX_STATUS.PENDING,
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
    last_error: null,
  });
  const pending = await getPendingOutbox();
  assert.equal(pending.some((r) => r.client_request_id === 'legacy-unscoped'), false);
});
