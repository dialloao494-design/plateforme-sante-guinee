import 'fake-indexeddb/auto';
import assert from 'node:assert/strict';
import { test, beforeEach } from 'node:test';
import { setOnlineStatus } from '../src/offline/connectivity.js';
import { applyOfflineEpoch, prepareOfflineEpoch } from '../src/offline/epoch.js';
import { cachePatientRecord, getCachedPatient } from '../src/offline/cache.js';
import { enqueueMutation, getPendingOutbox } from '../src/offline/outbox.js';
import { flushOutbox, startAutoSync, stopAutoSync, replayOutboxItem } from '../src/offline/sync.js';
import { attachOfflineInterceptors, detachOfflineInterceptors, probeServerConnectivity } from '../src/offline/register.js';
import { isOfflineAllowed } from '../src/offline/sessionScope.js';
import { offlineDb, clearOfflineDatabase } from '../src/offline/db.js';

const values = {};
const storage = { getItem: (k) => values[k] ?? null, setItem: (k, v) => { values[k] = v; }, removeItem: (k) => { delete values[k]; } };
global.window = { sessionStorage: storage, localStorage: storage };
global.sessionStorage = storage;
global.localStorage = storage;
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { onLine: false } });

beforeEach(() => setOnlineStatus(false));

function profile(enabled, epoch = 1) {
  values.sg_auth_profile = JSON.stringify({ id: 42, clinic_id: 7, offline_workstations_enabled: enabled, offline_data_epoch: epoch });
  values.user_id = '42';
}
function client() {
  const handlers = {};
  return {
    handlers,
    interceptors: {
      request: { use(fn) { handlers.request = fn; return 0; }, eject() {} },
      response: { use(ok, fail) { handlers.ok = ok; handlers.fail = fail; return 0; }, eject() {} },
    },
    get: async () => ({ data: { status: 'ok' } }),
  };
}

test('clinic policy prevents optimistic offline writes and cache fallback; re-enabling restores queueing', async () => {
  await offlineDb.open();
  const http = client();
  attachOfflineInterceptors(http);
  try {
    profile(false);
    const config = { method: 'post', url: '/clinical/reception/his/patients', data: { first_name: 'Test' } };
    assert.equal((await http.handlers.request({ ...config })).adapter, undefined);
    const error = { config, code: 'ERR_NETWORK' };
    await assert.rejects(http.handlers.fail(error), (e) => e === error);
    const readError = { config: { method: 'get', url: '/clinical/reception/his/patients' }, code: 'ERR_NETWORK' };
    await assert.rejects(http.handlers.fail(readError), (e) => e === readError);
    assert.equal(await offlineDb.outbox.count(), 0);
    profile(true);
    const queued = await http.handlers.request({ ...config });
    assert.equal((await queued.adapter()).status, 202);
    assert.equal(await offlineDb.outbox.count(), 1);
    profile(false);
    assert.equal(await offlineDb.outbox.count(), 1, 'disabling preserves existing unsynced work');
  } finally {
    detachOfflineInterceptors(http);
    await clearOfflineDatabase();
    offlineDb.close();
  }
});

test('proven API reachability overrides a stale browser offline flag for subsequent requests', async () => {
  await offlineDb.open();
  profile(true);
  const http = client();
  attachOfflineInterceptors(http);
  try {
    assert.equal(await probeServerConnectivity(http), true);
    const config = await http.handlers.request({ method: 'post', url: '/clinical/reception/his/patients', data: {} });
    assert.equal(config.adapter, undefined);
    assert.equal(navigator.onLine, false);
  } finally { detachOfflineInterceptors(http); await clearOfflineDatabase(); offlineDb.close(); }
});

test('legacy policy compatibility and clinic-specific disabled policy', () => {
  assert.equal(isOfflineAllowed({ id: 1 }), true);
  assert.equal(isOfflineAllowed({ offline_workstations_enabled: false }), false);
  assert.equal(isOfflineAllowed({ offline_workstations_enabled: true }), true);
});


test('automatic replay drains subsequent batches after proven connectivity despite stale browser flag', async () => {
  await offlineDb.open(); profile(true);
  let tick;
  Object.assign(window, { setInterval(fn) { tick = fn; return 1; }, clearInterval() {}, addEventListener() {}, removeEventListener() {} });
  let sent = 0;
  const http = { get: async () => ({ data: { status: 'ok' } }), post: async () => ({ status: 200, data: { id: ++sent } }) };
  try {
    for (let i = 0; i < 26; i++) await enqueueMutation({ method: 'post', url: '/clinical/consultations', data: { note: i }, clientRequestId: `batch-${i}`, entityType: 'consultation' });
    await probeServerConnectivity(http);
    startAutoSync(http);
    await tick();
    // Join the scheduled pass so the assertion observes its committed result.
    await flushOutbox(http);
    assert.equal(sent, 26);
    assert.equal((await getPendingOutbox()).length, 0);
    assert.equal(navigator.onLine, false);
  } finally { stopAutoSync(); await clearOfflineDatabase(); offlineDb.close(); }
});

test('disabled clinic does not warm new patient caches through direct storage calls', async () => {
  await offlineDb.open(); profile(false);
  try {
    await cachePatientRecord({ id: 101, first_name: 'Private' });
    assert.equal(await offlineDb.patients.count(), 0);
  } finally { await clearOfflineDatabase(); offlineDb.close(); }
});

test('reset quarantines old work, clears only owner caches, and preserves recovery payloads', async () => {
  await offlineDb.open(); profile(true);
  try {
    await enqueueMutation({ method: 'post', url: '/clinical/consultations', data: { note: 'old' }, clientRequestId: 'pre-reset', entityType: 'consultation' });
    await cachePatientRecord({ id: 1, first_name: 'old' });
    await offlineDb.patients.add({ owner_key: '99:8', patient_id: '9', payload_json: '{}' });
    await applyOfflineEpoch({ id: 42, clinic_id: 7, offline_data_epoch: 2 });
    profile(true, 2);
    const row = await offlineDb.outbox.where('client_request_id').equals('pre-reset').first();
    assert.equal(row.status, 'dead');
    assert.equal(JSON.parse(row.payload_json).note, 'old');
    assert.equal(await offlineDb.patients.filter(r => r.owner_key === '42:7').count(), 0);
    assert.equal(await offlineDb.patients.filter(r => r.owner_key === '99:8').count(), 1);
    await assert.rejects(replayOutboxItem(row, { post() { throw new Error('must not send'); } }), { code: 'OFFLINE_EPOCH_MISMATCH' });
    await enqueueMutation({ method: 'post', url: '/clinical/consultations', data: {}, clientRequestId: 'post-reset', entityType: 'consultation' });
    const fresh = await offlineDb.outbox.where('client_request_id').equals('post-reset').first();
    assert.equal(fresh.offline_data_epoch, 2);
    setOnlineStatus(true);
    await flushOutbox({ post: async (_url, _data, config) => {
      assert.equal(config.headers['X-Offline-Data-Epoch'], '2');
      throw { response: { status: 409, data: { detail: { code: 'offline_epoch_mismatch' } } } };
    } });
    assert.equal((await offlineDb.outbox.get(fresh.id)).status, 'dead');
    assert.equal(await offlineDb.conflicts.count(), 0);
  } finally { await clearOfflineDatabase(); offlineDb.close(); }
});


test('stale patient caches remain unreadable even if local epoch cleanup fails', async () => {
  await offlineDb.open(); profile(true);
  const originalTransaction = offlineDb.transaction;
  try {
    await cachePatientRecord({ id: 'legacy-cache', first_name: 'old test data' });
    assert.ok(await getCachedPatient('legacy-cache'));
    profile(true, 2);
    offlineDb.transaction = async () => { throw new Error('storage unavailable'); };
    await prepareOfflineEpoch({ id: 42, clinic_id: 7, offline_data_epoch: 2 });
    assert.equal(await getCachedPatient('legacy-cache'), undefined);
    assert.equal(await offlineDb.patients.count(), 1, 'failure did not erase the old data');
  } finally { offlineDb.transaction = originalTransaction; await clearOfflineDatabase(); offlineDb.close(); }
});

test('replay never accepts another optimistic local queue response as server persistence', async () => {
  await offlineDb.open(); profile(true);
  try {
    await enqueueMutation({ method: 'post', url: '/clinical/consultations', data: {}, clientRequestId: 'must-reach-server', entityType: 'consultation' });
    const row = await offlineDb.outbox.where('client_request_id').equals('must-reach-server').first();
    await assert.rejects(replayOutboxItem(row, { post: async () => ({ status: 202, data: { _offline_queued: true } }) }), { code: 'ERR_NETWORK' });
    assert.equal((await offlineDb.outbox.get(row.id)).status, 'pending');
  } finally { await clearOfflineDatabase(); offlineDb.close(); }
});


test('a request failing after reset keeps its original generation and cannot recreate pre-reset data', async () => {
  await offlineDb.open(); profile(true);
  const http = client();
  attachOfflineInterceptors(http);
  try {
    setOnlineStatus(true);
    const config = await http.handlers.request({ method: 'post', url: '/clinical/consultations', data: { note: 'before reset' }, headers: { 'X-Client-Request-Id': 'late-pre-reset' } });
    profile(true, 2);
    await assert.rejects(http.handlers.fail({ config, code: 'ERR_NETWORK' }), { code: 'OFFLINE_EPOCH_MISMATCH' });
    const row = await offlineDb.outbox.where('client_request_id').equals('late-pre-reset').first();
    assert.equal(row.offline_data_epoch, 1);
    assert.equal(row.status, 'dead');
    assert.equal(JSON.parse(row.payload_json).note, 'before reset');
    await assert.rejects(http.handlers.fail({ config, code: 'ERR_NETWORK' }), { code: 'OFFLINE_EPOCH_MISMATCH' });
    assert.equal(await offlineDb.outbox.count(), 1);
  } finally { detachOfflineInterceptors(http); await clearOfflineDatabase(); offlineDb.close(); }
});
