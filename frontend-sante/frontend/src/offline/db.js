import Dexie from 'dexie';

export const DB_NAME = 'sante_offline_v2';
export const DB_VERSION = 2;

export const offlineDb = new Dexie(DB_NAME);

offlineDb.version(DB_VERSION).stores({
  patients: '++id, owner_key, patient_id, search_key, cached_at',
  catalogs: '++id, owner_key, catalog_key, cached_at',
  consultations: '++id, owner_key, consultation_id, patient_id, updated_at',
  billing: '++id, owner_key, entity_id, entity_type, patient_id, updated_at',
  pharmacy: '++id, owner_key, entity_id, patient_id, updated_at',
  lab: '++id, owner_key, entity_id, patient_id, updated_at',
  outbox:
    '++id, owner_key, client_request_id, entity_type, status, created_at, next_retry_at, user_id, clinic_id',
  conflicts: '++id, owner_key, client_request_id, entity_type, created_at, resolved',
  meta: 'key',
});

export function buildOwnerKey(userId, clinicId) {
  const uid = userId == null || userId === '' ? 'anon' : String(userId);
  const cid = clinicId == null || clinicId === '' ? 'none' : String(clinicId);
  return `${uid}:${cid}`;
}

export async function getMeta(key, fallback = null) {
  const row = await offlineDb.meta.get(key);
  return row?.value ?? fallback;
}

export async function setMeta(key, value) {
  await offlineDb.meta.put({ key, value, updated_at: Date.now() });
}

/** Wipe all offline PHI/outbox state (logout / identity switch). */
export async function clearOfflineDatabase() {
  if (typeof indexedDB === 'undefined') return;
  try {
    await offlineDb.open();
    await Promise.all([
      offlineDb.patients.clear(),
      offlineDb.catalogs.clear(),
      offlineDb.consultations.clear(),
      offlineDb.billing.clear(),
      offlineDb.pharmacy.clear(),
      offlineDb.lab.clear(),
      offlineDb.outbox.clear(),
      offlineDb.conflicts.clear(),
      offlineDb.meta.clear(),
    ]);
  } catch {
    /* ignore */
  }
  try {
    offlineDb.close();
    await Dexie.delete(DB_NAME);
    // Also delete the legacy unscoped DB from PR #31 v1.
    await Dexie.delete('sante_offline_v1');
  } catch {
    /* ignore */
  }
}

/** Clear Cache Storage entries used by the service worker / runtime caches. */
export async function clearOfflineCacheStorage() {
  if (typeof caches === 'undefined') return;
  try {
    const keys = await caches.keys();
    await Promise.all(
      keys
        .filter((k) => /clinical|api|workbox|sante/i.test(k))
        .map((k) => caches.delete(k))
    );
  } catch {
    /* ignore */
  }
}

export async function purgeOfflinePrivacyState() {
  await clearOfflineDatabase();
  await clearOfflineCacheStorage();
}
