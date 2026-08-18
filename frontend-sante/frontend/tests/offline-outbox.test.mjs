/**
 * IndexedDB outbox enqueue idempotency test (fake-indexeddb).
 * Run: npm run test:offline
 */
import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { offlineDb } from '../src/offline/db.js';
import {
  enqueueMutation,
  getPendingOutbox,
  listDeadOutbox,
  normalizeQueuedPayload,
  recoverStaleInFlight,
  retryDeadOutbox,
} from '../src/offline/outbox.js';

before(async () => {
  await offlineDb.open();
});

after(async () => {
  await offlineDb.delete();
  offlineDb.close();
});

test('enqueueMutation is idempotent on client_request_id', async () => {
  const reqId = 'test-req-001';
  const first = await enqueueMutation({
    method: 'post',
    url: '/clinical/consultations',
    data: { patient_id: 7 },
    clientRequestId: reqId,
    entityType: 'consultation',
    operation: 'create',
  });
  const second = await enqueueMutation({
    method: 'post',
    url: '/clinical/consultations',
    data: { patient_id: 7 },
    clientRequestId: reqId,
    entityType: 'consultation',
    operation: 'create',
  });

  assert.equal(first.client_request_id, reqId);
  assert.equal(second.duplicate, true);

  const pending = await getPendingOutbox();
  const same = pending.filter((p) => p.client_request_id === reqId);
  assert.equal(same.length, 1);
});

test('getPendingOutbox returns FIFO order', async () => {
  await offlineDb.outbox.clear();
  await enqueueMutation({
    method: 'post',
    url: '/clinical/billing/unified/invoices/generate',
    data: { visit_id: 1 },
    clientRequestId: 'billing-a',
    entityType: 'billing',
  });
  await new Promise((r) => setTimeout(r, 5));
  await enqueueMutation({
    method: 'post',
    url: '/clinical/pharmacy/service-requests',
    data: { patient_id: 2 },
    clientRequestId: 'pharm-b',
    entityType: 'pharmacy',
  });

  const pending = await getPendingOutbox();
  assert.equal(pending.length, 2);
  assert.equal(pending[0].client_request_id, 'billing-a');
  assert.equal(pending[1].client_request_id, 'pharm-b');
});

test('Axios JSON strings are normalized before durable enqueue and replay', async () => {
  await offlineDb.outbox.clear();
  await enqueueMutation({
    method: 'post',
    url: '/clinical/lab/orders',
    data: JSON.stringify({ patient_id: 9, test: 'CBC' }),
    clientRequestId: 'serialized-body',
  });
  const row = await offlineDb.outbox.where('client_request_id').equals('serialized-body').first();
  assert.deepEqual(JSON.parse(row.payload_json), { patient_id: 9, test: 'CBC' });
  assert.deepEqual(normalizeQueuedPayload('{"a":1}'), { a: 1 });
  assert.equal(normalizeQueuedPayload('plain text'), 'plain text');
});

test('stale in-flight work is recovered but active work is untouched', async () => {
  await offlineDb.outbox.clear();
  // Test scope in this file is anonymous; provide a real scoped browser identity.
  global.sessionStorage = { getItem: (key) => key === 'user_id' ? '7' : key === 'sg_auth_profile' ? JSON.stringify({ id: 7, clinic_id: 3 }) : null };
  global.localStorage = { getItem: () => null };
  global.window = { sessionStorage: global.sessionStorage, localStorage: global.localStorage };
  const ownerKey = '7:3';
  const staleId = await offlineDb.outbox.add({ owner_key: ownerKey, status: 'in_flight', updated_at: 1 });
  const activeId = await offlineDb.outbox.add({ owner_key: ownerKey, status: 'in_flight', updated_at: Date.now() });
  assert.equal(await recoverStaleInFlight(1000), 1);
  assert.equal((await offlineDb.outbox.get(staleId)).status, 'pending');
  assert.equal((await offlineDb.outbox.get(activeId)).status, 'in_flight');
});

test('dead-letter work is visible and can be retried', async () => {
  await offlineDb.outbox.clear();
  const id = await offlineDb.outbox.add({ owner_key: '7:3', status: 'dead', attempt_count: 12 });
  assert.equal((await listDeadOutbox()).length, 1);
  assert.equal(await retryDeadOutbox(id), true);
  const row = await offlineDb.outbox.get(id);
  assert.equal(row.status, 'pending');
  assert.equal(row.attempt_count, 0);
});

test('storage quota failure rejects the new mutation without deleting existing work', async () => {
  await offlineDb.outbox.clear();
  await offlineDb.outbox.add({
    owner_key: '7:3',
    client_request_id: 'already-safe',
    status: 'pending',
    created_at: Date.now(),
  });
  const originalAdd = offlineDb.outbox.add.bind(offlineDb.outbox);
  offlineDb.outbox.add = async () => {
    throw new DOMException('Quota exceeded', 'QuotaExceededError');
  };
  try {
    await assert.rejects(
      enqueueMutation({
        method: 'post',
        url: '/clinical/reception/his/patients',
        data: { first_name: 'Quota' },
        clientRequestId: 'quota-rejected',
        entityType: 'patient',
      }),
      (error) => error?.name === 'QuotaExceededError',
    );
  } finally {
    offlineDb.outbox.add = originalAdd;
  }
  const rows = await offlineDb.outbox.toArray();
  assert.equal(rows.length, 1);
  assert.equal(rows[0].client_request_id, 'already-safe');
});
