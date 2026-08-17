import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { offlineDb, clearOfflineDatabase } from '../src/offline/db.js';
import { enqueueMutation, getPendingOutbox } from '../src/offline/outbox.js';
import { replayOutboxItem } from '../src/offline/sync.js';
import { recordConflict, resolveConflict } from '../src/offline/conflict.js';

function mockScope(userId = '42', clinicId = '7') {
  const storage = {
    user_id: String(userId),
    sg_auth_profile: JSON.stringify({ id: userId, clinic_id: clinicId }),
  };
  const sessionStorage = {
    getItem(key) { return storage[key] ?? null; },
    setItem(key, value) { storage[key] = value; },
    removeItem(key) { delete storage[key]; },
    clear() { Object.keys(storage).forEach((k) => delete storage[k]); },
  };
  const localStorage = { getItem() { return null; }, setItem() {}, removeItem() {}, clear() {} };
  global.sessionStorage = sessionStorage;
  global.localStorage = localStorage;
  global.window = { sessionStorage, localStorage };
}

before(async () => { await offlineDb.open(); });
after(async () => { await clearOfflineDatabase(); offlineDb.close(); });

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
  const result = await replayOutboxItem(row, { post: async () => ({ data: {}, status: 200 }) });
  assert.equal(result, 'skipped');
});

test('getPendingOutbox ignores legacy rows without owner_key', async () => {
  mockScope('1', '1');
  await offlineDb.outbox.clear();
  await offlineDb.outbox.add({
    client_request_id: 'legacy',
    owner_key: null,
    entity_type: 'billing',
    method: 'POST',
    url: '/x',
    payload_json: '{}',
    status: 'pending',
    created_at: Date.now(),
    next_retry_at: Date.now(),
  });
  const pending = await getPendingOutbox();
  assert.equal(pending.length, 0);
});

test('retry_local conflict resolution restores the original mutation', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  await offlineDb.conflicts.clear();
  await enqueueMutation({
    method: 'patch',
    url: '/clinical/lab/orders/4',
    data: { patient_id: 2, result: 'local', record_version: 2 },
    clientRequestId: 'conflict-retry',
  });
  const row = await offlineDb.outbox.where('client_request_id').equals('conflict-retry').first();
  await offlineDb.outbox.update(row.id, { status: 'synced' });
  const conflictId = await recordConflict({
    clientRequestId: 'conflict-retry',
    entityType: 'lab',
    entityId: 4,
    localPayload: { patient_id: 2, result: 'local', record_version: 2 },
    remotePayload: { patient_id: 2, result: 'remote', record_version: 2 },
  });
  assert.equal(await resolveConflict(conflictId, 'retry_local'), true);
  const restored = await offlineDb.outbox.get(row.id);
  assert.equal(restored.status, 'pending');
  assert.equal(JSON.parse(restored.payload_json).result, 'local');
  assert.equal(restored.record_version, 3);
});
