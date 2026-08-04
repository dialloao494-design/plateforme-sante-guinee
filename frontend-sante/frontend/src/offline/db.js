import Dexie from 'dexie';

export const DB_NAME = 'sante_offline_v1';
export const DB_VERSION = 1;

export const offlineDb = new Dexie(DB_NAME);

offlineDb.version(DB_VERSION).stores({
  patients: '++id, patient_id, search_key, cached_at',
  catalogs: '++id, catalog_key, cached_at',
  consultations: '++id, consultation_id, patient_id, updated_at',
  billing: '++id, entity_id, entity_type, patient_id, updated_at',
  pharmacy: '++id, entity_id, patient_id, updated_at',
  lab: '++id, entity_id, patient_id, updated_at',
  outbox: '++id, client_request_id, entity_type, status, created_at, next_retry_at',
  conflicts: '++id, client_request_id, entity_type, created_at, resolved',
  meta: 'key',
});

export async function getMeta(key, fallback = null) {
  const row = await offlineDb.meta.get(key);
  return row?.value ?? fallback;
}

export async function setMeta(key, value) {
  await offlineDb.meta.put({ key, value, updated_at: Date.now() });
}
