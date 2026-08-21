import { offlineDb } from './db.js';
import { buildCacheKey } from '../utils/apiCache.js';
import { isCatalogUrl, isPatientDetailUrl, isPatientSearchUrl } from './entityTypes.js';
import { readOfflineOwnerScope } from './sessionScope.js';

const MAX_PATIENT_CACHE = 500;
const MAX_CATALOG_CACHE = 50;
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

function isPatientDirectoryRequest(url, params) {
  return /\/clinical\/reception\/his\/dashboard\/queue\/?$/.test(String(url).split('?')[0])
    && params?.bucket === 'total_patients';
}

async function readCachedPatientDirectory(ownerKey, now) {
  const rows = await offlineDb.patients.orderBy('cached_at').reverse().toArray();
  const patients = [];
  for (const row of rows) {
    if (row.owner_key !== ownerKey || !String(row.search_key || '').startsWith('id:')) continue;
    if (row.expires_at && row.expires_at <= now) continue;
    const patient = await readCachedJson(offlineDb.patients, row);
    if (!patient) continue;
    patients.push({
      patient_id: patient.id || patient.patient_id,
      patient_name: patient.full_name || patient.patient_name
        || [patient.last_name, patient.first_name].filter(Boolean).join(' '),
      patient_number: patient.patient_number || patient.patient_code || null,
      phone: patient.phone || null,
      gender: patient.gender || null,
      registration_date: patient.registration_date || patient.created_at || null,
    });
  }
  return patients;
}

export function buildOfflineCacheKey(method, url, params) {
  return buildCacheKey(method, url, params);
}

async function readCachedJson(table, row) {
  try {
    return JSON.parse(row.payload_json);
  } catch {
    // A malformed cache must never crash a clinical screen or be mistaken for
    // valid patient data. Remove only the damaged derived row; durable outbox
    // mutations live in a separate table and remain untouched/exportable.
    await table.delete(row.id);
    return undefined;
  }
}

/** Store GET response in IndexedDB for offline replay. */
export async function cacheGetResponse(url, params, data) {
  const key = buildOfflineCacheKey('get', url, params);
  const now = Date.now();
  const expiresAt = now + CACHE_TTL_MS;
  const { ownerKey, userId } = readOfflineOwnerScope();
  if (!userId) {
    // Do not persist PHI for anonymous/unscoped sessions.
    return;
  }

  if (isPatientSearchUrl(url)) {
    const q = String(params?.q ?? '').trim().toLowerCase();
    await offlineDb.patients.put({
      owner_key: ownerKey,
      search_key: q || '__all__',
      patient_id: null,
      payload_json: JSON.stringify(data),
      cached_at: now,
      expires_at: expiresAt,
    });
    await pruneTable('patients', MAX_PATIENT_CACHE);
    return;
  }

  if (isPatientDetailUrl(url) && data && !Array.isArray(data)) {
    await cachePatientRecord(data);
    return;
  }

  if (isPatientDirectoryRequest(url, params) && Array.isArray(data)) {
    await Promise.all(data.map((patient) => cachePatientRecord(patient)));
  }

  if (isCatalogUrl(url)) {
    await offlineDb.catalogs.put({
      owner_key: ownerKey,
      catalog_key: key,
      payload_json: JSON.stringify(data),
      cached_at: now,
      expires_at: expiresAt,
    });
    await pruneTable('catalogs', MAX_CATALOG_CACHE);
    return;
  }

  await offlineDb.meta.put({
    key: `get:${ownerKey}:${key}`,
    value: { data, cached_at: now, expires_at: expiresAt, owner_key: ownerKey },
    updated_at: now,
  });
}

export async function getCachedGet(url, params) {
  const key = buildOfflineCacheKey('get', url, params);
  const now = Date.now();
  const { ownerKey, userId } = readOfflineOwnerScope();
  if (!userId) return undefined;

  if (isPatientSearchUrl(url)) {
    const q = String(params?.q ?? '').trim().toLowerCase();
    const exact = await offlineDb.patients
      .where('search_key')
      .equals(q || '__all__')
      .filter((row) => row.owner_key === ownerKey)
      .first();
    if (exact && (!exact.expires_at || exact.expires_at > now)) {
      return readCachedJson(offlineDb.patients, exact);
    }
    if (q.length >= 2) {
      const all = await offlineDb.patients.orderBy('cached_at').reverse().toArray();
      const matches = [];
      for (const row of all) {
        if (row.owner_key !== ownerKey) continue;
        if (row.expires_at && row.expires_at <= now) continue;
        const payload = await readCachedJson(offlineDb.patients, row);
        if (payload === undefined) continue;
        const list = Array.isArray(payload)
          ? payload
          : payload?.results || payload?.patients || (payload?.id || payload?.patient_id ? [payload] : []);
        for (const p of list) {
          const hay = `${p.full_name || ''} ${p.patient_name || ''} ${p.first_name || ''} ${p.last_name || ''} ${p.patient_number || p.patient_code || ''} ${p.phone || ''}`.toLowerCase();
          if (hay.includes(q)) matches.push(p);
        }
      }
      if (matches.length) {
        return Array.from(new Map(matches.map((patient) => [String(patient.id || patient.patient_id), patient])).values());
      }
    }
    return undefined;
  }

  if (isPatientDetailUrl(url)) {
    const patientId = String(url).split('?')[0].match(/\/patients\/([^/]+)\/?$/)?.[1];
    if (patientId) return getCachedPatient(decodeURIComponent(patientId));
    return undefined;
  }

  if (isCatalogUrl(url)) {
    const row = await offlineDb.catalogs
      .where('catalog_key')
      .equals(key)
      .filter((r) => r.owner_key === ownerKey)
      .first();
    if (row && (!row.expires_at || row.expires_at > now)) {
      return readCachedJson(offlineDb.catalogs, row);
    }
    return undefined;
  }

  const meta = await offlineDb.meta.get(`get:${ownerKey}:${key}`);
  if (meta?.value?.expires_at > now && meta?.value?.owner_key === ownerKey) {
    if (isPatientDirectoryRequest(url, params)) {
      const directory = await readCachedPatientDirectory(ownerKey, now);
      const combined = [...(Array.isArray(meta.value.data) ? meta.value.data : []), ...directory];
      return Array.from(new Map(combined.map((patient) => [
        String(patient.patient_id || patient.id),
        patient,
      ])).values());
    }
    return meta.value.data;
  }
  if (isPatientDirectoryRequest(url, params)) {
    const directory = await readCachedPatientDirectory(ownerKey, now);
    return directory.length ? directory : undefined;
  }
  return undefined;
}

export async function cachePatientRecord(patient) {
  if (!patient?.id && !patient?.patient_id) return;
  const { ownerKey, userId } = readOfflineOwnerScope();
  if (!userId) return;
  const patientId = patient.id || patient.patient_id;
  const normalizedPatient = {
    ...patient,
    id: patientId,
    full_name: patient.full_name || patient.patient_name || [patient.last_name, patient.first_name].filter(Boolean).join(' '),
  };
  const now = Date.now();
  await offlineDb.patients.put({
    owner_key: ownerKey,
    patient_id: String(patientId),
    search_key: `id:${patientId}`,
    payload_json: JSON.stringify(normalizedPatient),
    cached_at: now,
    expires_at: now + CACHE_TTL_MS,
  });
}

export async function getCachedPatient(patientId) {
  const { ownerKey, userId } = readOfflineOwnerScope();
  if (!userId) return undefined;
  const row = await offlineDb.patients
    .where('search_key')
    .equals(`id:${patientId}`)
    .filter((r) => r.owner_key === ownerKey)
    .first();
  if (!row) return undefined;
  if (row.expires_at && row.expires_at <= Date.now()) return undefined;
  return readCachedJson(offlineDb.patients, row);
}

export async function storeDomainEntity(domain, entity) {
  const table = offlineDb[domain];
  if (!table) return;
  const { ownerKey, userId } = readOfflineOwnerScope();
  if (!userId) return;
  const entityId = entity.id || entity.entity_id || entity.consultation_id;
  if (!entityId) return;
  const now = Date.now();
  await table.put({
    owner_key: ownerKey,
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
