import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { offlineDb, clearOfflineDatabase } from '../src/offline/db.js';
import { enqueueMutation, getPendingOutbox } from '../src/offline/outbox.js';
import { flushOutbox, replayOutboxItem } from '../src/offline/sync.js';
import { recordConflict, resolveConflict } from '../src/offline/conflict.js';
import {
  buildOfflineRecoveryExport,
  OFFLINE_RECOVERY_FORMAT,
  validateOfflineRecoveryExport,
} from '../src/offline/recovery.js';
import { getCachedPatient } from '../src/offline/cache.js';

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
  if (global.navigator) {
    Object.defineProperty(global.navigator, 'onLine', { configurable: true, value: true });
  } else {
    global.navigator = { onLine: true };
  }
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

test('manual retry includes failed rows whose automatic backoff has not elapsed', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  const id = await offlineDb.outbox.add({
    client_request_id: 'deferred-manual-retry',
    owner_key: '42:7',
    entity_type: 'billing',
    method: 'POST',
    url: '/clinical/reception/his/invoices',
    payload_json: '{}',
    status: 'failed',
    attempt_count: 2,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now() + 300_000,
  });

  assert.equal((await getPendingOutbox()).length, 0);
  assert.equal((await getPendingOutbox(50, { includeDeferred: true })).length, 1);

  let calls = 0;
  const result = await flushOutbox({
    post: async () => {
      calls += 1;
      return { status: 200, data: { id: 9 } };
    },
  }, { forceRetry: true });
  assert.equal(calls, 1);
  assert.equal(result.synced, 1);
  assert.equal((await offlineDb.outbox.get(id)).status, 'synced');
});

test('manual retry immediately recovers a recently stranded in-flight row', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  const id = await offlineDb.outbox.add({
    client_request_id: 'recent-interrupted-sync',
    owner_key: '42:7',
    entity_type: 'billing',
    method: 'POST',
    url: '/clinical/reception/his/invoices',
    payload_json: '{}',
    status: 'in_flight',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
  });

  let calls = 0;
  const result = await flushOutbox({
    post: async () => {
      calls += 1;
      return { status: 200, data: { id: 10 } };
    },
  }, { forceRetry: true });

  assert.equal(result.recovered, 1);
  assert.equal(result.synced, 1);
  assert.equal(calls, 1);
  assert.equal((await offlineDb.outbox.get(id)).status, 'synced');
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

test('corrupted cached patient is removed without touching durable mutations', async () => {
  mockScope('42', '7');
  await offlineDb.patients.clear();
  await offlineDb.outbox.clear();
  await offlineDb.patients.add({
    owner_key: '42:7',
    patient_id: '9',
    search_key: 'id:9',
    payload_json: '{broken',
    cached_at: Date.now(),
    expires_at: Date.now() + 60_000,
  });
  await enqueueMutation({
    method: 'post',
    url: '/clinical/lab/orders',
    data: { patient_id: 9 },
    clientRequestId: 'durable-survives-cache-repair',
  });
  assert.equal(await getCachedPatient(9), undefined);
  assert.equal(await offlineDb.patients.count(), 0);
  assert.equal(await offlineDb.outbox.count(), 1);
});

test('corrupted outbox payload is quarantined for export instead of replaying empty data', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  const id = await offlineDb.outbox.add({
    owner_key: '42:7',
    user_id: '42',
    clinic_id: '7',
    client_request_id: 'corrupt-payload',
    entity_type: 'billing',
    method: 'POST',
    url: '/clinical/reception/his/invoices',
    payload_json: '{broken',
    headers_json: JSON.stringify({ Authorization: 'must-not-export' }),
    status: 'pending',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
  });
  let calls = 0;
  const result = await flushOutbox({ post: async () => { calls += 1; return { status: 200, data: {} }; } });
  assert.equal(calls, 0);
  assert.equal(result.failed, 1);
  assert.equal((await offlineDb.outbox.get(id)).status, 'dead');

  const bundle = await buildOfflineRecoveryExport();
  assert.equal(bundle.mutations.length, 1);
  assert.equal(bundle.mutations[0].payload, '{broken');
  assert.equal(bundle.integrity_warnings.length, 1);
  assert.equal(JSON.stringify(bundle).includes('must-not-export'), false);
});

test('recovery export manifest is valid and remains scoped to the active clinic user', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  await offlineDb.conflicts.clear();
  await enqueueMutation({
    method: 'post',
    url: '/clinical/lab/orders',
    data: { patient_id: 9, exam: 'NFS' },
    clientRequestId: 'validated-export',
  });
  await offlineDb.outbox.add({
    owner_key: '99:8',
    client_request_id: 'foreign-export-row',
    entity_type: 'patient',
    method: 'POST',
    url: '/clinical/reception/his/patients',
    payload_json: '{}',
    status: 'dead',
    created_at: Date.now(),
  });

  const bundle = await buildOfflineRecoveryExport();
  assert.equal(bundle.format, OFFLINE_RECOVERY_FORMAT);
  assert.equal(bundle.manifest.mutation_count, 1);
  assert.equal(bundle.mutations[0].client_request_id, 'validated-export');
  assert.deepEqual(validateOfflineRecoveryExport(bundle, { userId: '42', clinicId: '7' }), {
    valid: true,
    errors: [],
  });
});

test('recovery validation blocks tampered manifests and cross-clinic hand-off', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  await offlineDb.conflicts.clear();
  const bundle = await buildOfflineRecoveryExport();
  bundle.manifest.mutation_count = 99;

  const result = validateOfflineRecoveryExport(bundle, { userId: '42', clinicId: '999' });
  assert.equal(result.valid, false);
  assert.ok(result.errors.some((message) => message.includes('manifeste')));
  assert.ok(result.errors.some((message) => message.includes("n'appartient pas")));
});

test('corrupted conflict copies are preserved with explicit integrity warnings', async () => {
  mockScope('42', '7');
  await offlineDb.outbox.clear();
  await offlineDb.conflicts.clear();
  await offlineDb.conflicts.add({
    owner_key: '42:7',
    conflict_id: 'broken-conflict',
    client_request_id: 'broken-conflict-request',
    entity_type: 'lab',
    local_json: '{broken',
    remote_json: '{also-broken',
    resolved: false,
    created_at: Date.now(),
  });

  const bundle = await buildOfflineRecoveryExport();
  assert.equal(bundle.conflicts.length, 1);
  assert.equal(bundle.integrity_warnings.length, 2);
  assert.equal(bundle.manifest.integrity_warning_count, 2);
  assert.equal(validateOfflineRecoveryExport(bundle, { userId: '42', clinicId: '7' }).valid, true);
});
