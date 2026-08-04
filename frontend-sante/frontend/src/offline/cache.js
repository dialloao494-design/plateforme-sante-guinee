import { offlineDb } from './db.js';
import { buildCacheKey } from '../utils/apiCache.js';
import { isCatalogUrl, isPatientSearchUrl } from './entityTypes.js';

const MAX_PATIENT_CACHE = 500;
const MAX_CATALOG_CACHE = 50;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export function buildOfflineCacheKey(method, url, params) {
  return buildCacheKey(method, url, params);
}

/** Store GET response in IndexedDB for offline replay. */
export async function cacheGetResponse(url, params, data) {
  const key = buildOfflineCacheKey('get', url, params);
  const now = Date.now();
  const expiresAt = now + CACHE_TTL_MS;

  if (isPatientSearchUrl(url)) {
    const q = String(params?.q ?? '').trim().toLowerCase();
    await offlineDb.patients.put({
      search_key: q || '__all__',
      patient_id: null,
      payload_json: JSON.stringify(data),
      cached_at: now,
      expires_at: expiresAt,
    });
    await pruneTable('patients', MAX_PATIENT_CACHE);
    return;
  }

  if (isCatalogUrl(url)) {
    await offlineDb.catalogs.put({
      catalog_key: key,
      payload_json: JSON.stringify(data),
      cached_at: now,
      expires_at: expiresAt,
    });
    await pruneTable('catalogs', MAX_CATALOG_CACHE);
    return;
  }

  await offlineDb.meta.put({
    key: `get:${key}`,
    value: { data, cached_at: now, expires_at: expiresAt },
    updated_at: now,
  });
}

export async function getCachedGet(url, params) {
  const key = buildOfflineCacheKey('get', url, params);
  const now = Date.now();

  if (isPatientSearchUrl(url)) {
    const q = String(params?.q ?? '').trim().toLowerCase();
    const exact = await offlineDb.patients.where('search_key').equals(q || '__all__').first();
    if (exact && (!exact.expires_at || exact.expires_at > now)) {
      return JSON.parse(exact.payload_json);
    }
    if (q.length >= 2) {
      const all = await offlineDb.patients.orderBy('cached_at').reverse().toArray();
      const matches = [];
      for (const row of all) {
        if (row.expires_at && row.expires_at <= now) continue;
        const payload = JSON.parse(row.payload_json || '[]');
        const list = Array.isArray(payload) ? payload : payload?.results || payload?.patients || [];
        for (const p of list) {
          const hay = `${p.full_name || ''} ${p.patient_code || ''} ${p.phone || ''}`.toLowerCase();
          if (hay.includes(q)) matches.push(p);
        }
      }
      if (matches.length) return matches;
    }
    return undefined;
  }

  if (isCatalogUrl(url)) {
    const row = await offlineDb.catalogs.where('catalog_key').equals(key).first();
    if (row && (!row.expires_at || row.expires_at > now)) {
      return JSON.parse(row.payload_json);
    }
    return undefined;
  }

  const meta = await offlineDb.meta.get(`get:${key}`);
  if (meta?.value?.expires_at > now) {
    return meta.value.data;
  }
  return undefined;
}

export async function cachePatientRecord(patient) {
  if (!patient?.id && !patient?.patient_id) return;
  const patientId = patient.id || patient.patient_id;
  const now = Date.now();
  await offlineDb.patients.put({
    patient_id: String(patientId),
    search_key: `id:${patientId}`,
    payload_json: JSON.stringify(patient),
    cached_at: now,
    expires_at: now + CACHE_TTL_MS,
  });
}

export async function getCachedPatient(patientId) {
  const row = await offlineDb.patients
    .where('search_key')
    .equals(`id:${patientId}`)
    .first();
  if (!row) return undefined;
  if (row.expires_at && row.expires_at <= Date.now()) return undefined;
  return JSON.parse(row.payload_json);
}

export async function storeDomainEntity(domain, entity) {
  const table = offlineDb[domain];
  if (!table) return;
  const entityId = entity.id || entity.entity_id || entity.consultation_id;
  if (!entityId) return;
  const now = Date.now();
  await table.put({
    entity_id: String(entityId),
    consultation_id: entity.consultation_id ? String(entity.consultation_id) : undefined,
    patient_id: entity.patient_id ? String(entity.patient_id) : undefined,
    entity_type: entity.entity_type || domain,
    payload_json: JSON.stringify(entity),
    updated_at: now,
    record_version: entity.record_version || 1,
  });
}

async function pruneTable(tableName, maxRows) {
  const table = offlineDb[tableName];
  const count = await table.count();
  if (count <= maxRows) return;
  const excess = count - maxRows;
  const oldest = await table.orderBy('cached_at').limit(excess).toArray();
  await table.bulkDelete(oldest.map((r) => r.id));
}
