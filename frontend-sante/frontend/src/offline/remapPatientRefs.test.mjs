import test from 'node:test';
import assert from 'node:assert/strict';
import 'fake-indexeddb/auto';

// Node has no Web Storage; offline owner scope reads auth from sessionStorage.
function makeMemoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(String(k), String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
    key: (i) => [...store.keys()][i] ?? null,
    get length() {
      return store.size;
    },
  };
}
if (typeof globalThis.sessionStorage === 'undefined') {
  globalThis.sessionStorage = makeMemoryStorage();
}
if (typeof globalThis.localStorage === 'undefined') {
  globalThis.localStorage = makeMemoryStorage();
}
if (typeof globalThis.window === 'undefined') {
  globalThis.window = globalThis;
}

import { offlineDb, getMeta, setMeta } from './db.js';
import {
  rewritePatientRefs,
  collectTempPatientIds,
  sortOutboxForPatientDependencies,
  remapDependentRecords,
  remapDependentOutboxReferences,
  resolveOutboxItemPatientRefs,
  outboxItemTempPatientIds,
} from './remapPatientRefs.js';

test('rewritePatientRefs replaces patient_id and URL segments', () => {
  const rewritten = rewritePatientRefs(
    {
      patient_id: 'offline_abc123',
      nested: { patientId: 'offline_abc123', note: 'keep' },
      items: [{ patient_id: 'offline_abc123' }, { patient_id: 9 }],
    },
    'offline_abc123',
    437,
  );
  assert.equal(rewritten.patient_id, 437);
  assert.equal(rewritten.nested.patientId, 437);
  assert.equal(rewritten.nested.note, 'keep');
  assert.equal(rewritten.items[0].patient_id, 437);
  assert.equal(rewritten.items[1].patient_id, 9);
  assert.equal(
    rewritePatientRefs('/clinical/hospitalization/admit/offline_abc123', 'offline_abc123', 437),
    '/clinical/hospitalization/admit/437',
  );
});

test('collectTempPatientIds finds offline tokens in payload and URL', () => {
  const ids = collectTempPatientIds({
    url: '/x/offline_aaa',
    patient_id: 'offline_bbb',
    body: { patient_id: 'offline_ccc' },
  });
  assert.ok(ids.has('offline_aaa'));
  assert.ok(ids.has('offline_bbb'));
  assert.ok(ids.has('offline_ccc'));
});

test('sortOutboxForPatientDependencies puts registration before dependents', () => {
  const sorted = sortOutboxForPatientDependencies([
    {
      client_request_id: 'bill',
      entity_type: 'billing',
      url: '/clinical/reception/his/invoices',
      created_at: 1,
    },
    {
      client_request_id: 'reg',
      entity_type: 'patient',
      url: '/clinical/reception/his/patients',
      created_at: 2,
    },
    {
      client_request_id: 'admit',
      entity_type: 'unknown',
      url: '/clinical/hospitalization/admissions',
      created_at: 3,
    },
  ]);
  assert.equal(sorted[0].client_request_id, 'reg');
  assert.equal(sorted[1].client_request_id, 'bill');
  assert.equal(sorted[2].client_request_id, 'admit');
});

test('sortOutboxForPatientDependencies puts invoice creation before its payment', () => {
  const sorted = sortOutboxForPatientDependencies([
    {
      client_request_id: 'payment',
      entity_type: 'billing',
      url: '/clinical/reception/his/invoices/offline_inv9/payments',
      created_at: 1,
    },
    {
      client_request_id: 'invoice',
      entity_type: 'billing',
      url: '/clinical/reception/his/invoices',
      created_at: 2,
    },
  ]);
  assert.deepEqual(sorted.map((row) => row.client_request_id), ['invoice', 'payment']);
});

test('invoice reconciliation rewrites a queued payment URL', async () => {
  await offlineDb.open();
  await offlineDb.outbox.clear();
  await offlineDb.meta.clear();
  const { setAuthItem } = await import('../utils/authStorage.js');
  setAuthItem('user_id', '155');
  setAuthItem('sg_auth_profile', JSON.stringify({ id: 155, clinic_id: 17 }));

  await offlineDb.outbox.add({
    client_request_id: 'offline-payment',
    owner_key: '155:17',
    user_id: '155',
    clinic_id: '17',
    entity_type: 'billing',
    operation: 'create',
    method: 'POST',
    url: '/clinical/reception/his/invoices/offline_inv9/payments',
    payload_json: JSON.stringify({ amount_gnf: 100000, payment_method: 'cash' }),
    params_json: null,
    headers_json: '{}',
    record_version: 1,
    optimistic_json: JSON.stringify({ id: 'offline_inv9', remaining_balance_gnf: 0 }),
    status: 'pending',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
    last_error: null,
  });

  const result = await remapDependentOutboxReferences('offline_inv9', 901, {
    entity_type: 'billing',
  });
  assert.equal(result.rewrittenOutbox, 1);
  const payment = await offlineDb.outbox.where('client_request_id').equals('offline-payment').first();
  assert.equal(payment.url, '/clinical/reception/his/invoices/901/payments');
  const mapped = await getMeta('idmap:155:17:offline_inv9');
  assert.equal(mapped.server_id, 901);
});

test('outboxItemTempPatientIds ignores non-patient optimistic entity id', () => {
  const ids = outboxItemTempPatientIds({
    url: '/clinical/consultations',
    payload_json: JSON.stringify({ patient_id: 'offline_pat1', chief_complaint: 'fièvre' }),
    optimistic_json: JSON.stringify({
      id: 'offline_consult9',
      patient_id: 'offline_pat1',
      entity_type: 'consultation',
    }),
  });
  assert.deepEqual(ids, ['offline_pat1']);
});

test('remapDependentRecords rewrites pending billing/admission outbox rows', async () => {
  await offlineDb.open();
  await offlineDb.outbox.clear();
  await offlineDb.patients.clear();
  await offlineDb.meta.clear();

  // Simulate authenticated owner scope used by remap filters.
  const { setAuthItem } = await import('../utils/authStorage.js');
  setAuthItem('user_id', '155');
  setAuthItem('sg_auth_profile', JSON.stringify({ id: 155, clinic_id: 17 }));

  const tempId = 'offline_dep001';
  await offlineDb.outbox.add({
    client_request_id: 'dep-invoice',
    owner_key: '155:17',
    user_id: '155',
    clinic_id: '17',
    entity_type: 'billing',
    operation: 'create',
    method: 'POST',
    url: '/clinical/reception/his/invoices',
    payload_json: JSON.stringify({ patient_id: tempId, items: [] }),
    params_json: null,
    headers_json: '{}',
    record_version: 1,
    optimistic_json: JSON.stringify({ id: 'offline_inv1', patient_id: tempId }),
    status: 'pending',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
    last_error: null,
  });
  await offlineDb.outbox.add({
    client_request_id: 'dep-admit',
    owner_key: '155:17',
    user_id: '155',
    clinic_id: '17',
    entity_type: 'unknown',
    operation: 'create',
    method: 'POST',
    url: '/clinical/hospitalization/admissions',
    payload_json: JSON.stringify({ patient_id: tempId, reason: 'observation' }),
    params_json: null,
    headers_json: '{}',
    record_version: 1,
    optimistic_json: JSON.stringify({ id: 'offline_adm1', patient_id: tempId }),
    status: 'pending',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
    last_error: null,
  });
  await offlineDb.billing.add({
    owner_key: '155:17',
    entity_id: 'offline_inv1',
    entity_type: 'billing',
    patient_id: tempId,
    payload_json: JSON.stringify({ patient_id: tempId, amount: 1 }),
    updated_at: Date.now(),
    record_version: 1,
  });

  const result = await remapDependentRecords(tempId, 438, {
    patientNumber: 'PAT-017-000438',
  });
  assert.equal(result.rewrittenOutbox, 2);
  assert.ok(result.rewrittenCaches >= 1);

  const rows = await offlineDb.outbox.toArray();
  for (const row of rows) {
    const payload = JSON.parse(row.payload_json);
    assert.equal(payload.patient_id, 438);
    const optimistic = JSON.parse(row.optimistic_json);
    assert.equal(optimistic.patient_id, 438);
  }
  const billCache = await offlineDb.billing.toArray();
  assert.equal(String(billCache[0].patient_id), '438');
  assert.equal(JSON.parse(billCache[0].payload_json).patient_id, 438);

  const idmap = await getMeta('idmap:155:17:offline_dep001', null);
  assert.equal(idmap.server_id, 438);
  assert.equal(idmap.patient_number, 'PAT-017-000438');

  await offlineDb.delete();
  offlineDb.close();
});

test('resolveOutboxItemPatientRefs blocks until idmap exists', async () => {
  await offlineDb.open();
  await offlineDb.meta.clear();
  const { setAuthItem } = await import('../utils/authStorage.js');
  setAuthItem('user_id', '155');
  setAuthItem('sg_auth_profile', JSON.stringify({ id: 155, clinic_id: 17 }));

  const item = {
    id: 99,
    entity_type: 'billing',
    url: '/clinical/reception/his/invoices',
    payload_json: JSON.stringify({ patient_id: 'offline_wait1' }),
    params_json: null,
    optimistic_json: JSON.stringify({ patient_id: 'offline_wait1' }),
    headers_json: '{}',
    client_request_id: 'wait-1',
    record_version: 1,
    method: 'POST',
  };

  const blocked = await resolveOutboxItemPatientRefs(item);
  assert.deepEqual(blocked.blockedTempIds, ['offline_wait1']);

  await setMeta('idmap:155:17:offline_wait1', { server_id: 501, patient_number: 'PAT-017-000501' });
  // Need a real outbox row for persistence path
  await offlineDb.outbox.clear();
  const rowId = await offlineDb.outbox.add({
    ...item,
    owner_key: '155:17',
    status: 'pending',
    attempt_count: 0,
    created_at: Date.now(),
    updated_at: Date.now(),
    next_retry_at: Date.now(),
    last_error: null,
  });
  const ready = await resolveOutboxItemPatientRefs({ ...item, id: rowId });
  assert.equal(ready.blockedTempIds.length, 0);
  assert.equal(JSON.parse(ready.item.payload_json).patient_id, 501);

  await offlineDb.delete();
  offlineDb.close();
});
