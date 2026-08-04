/**
 * IndexedDB outbox enqueue idempotency test (fake-indexeddb).
 * Run: npm run test:offline
 */
import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, before, after } from 'node:test';
import { offlineDb } from '../src/offline/db.js';
import { enqueueMutation, getPendingOutbox } from '../src/offline/outbox.js';

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
