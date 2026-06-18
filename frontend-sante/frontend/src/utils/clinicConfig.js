import { CACHE_TTL, getCached, setCached } from './apiCache.js';
import { cachedGet } from './cachedHttp.js';

const CLINIC_KEY = 'get:/clinical/clinics';
const SESSION_CLINIC_KEY = 'clinic:profile';

/** Cached clinic list (admin) — session-persisted. */
export async function fetchClinicsCached({ forceRefresh = false } = {}) {
  const response = await cachedGet('/clinical/clinics', {
    cacheTtlMs: CACHE_TTL.clinicConfig,
    cachePersist: true,
    forceRefresh,
  });
  return response.data;
}

/** Clinic profile snippet from operations summary or auth user. */
export function readClinicProfile() {
  return getCached(SESSION_CLINIC_KEY, { persist: true }) ?? null;
}

export function writeClinicProfile(profile) {
  if (!profile) {
    return;
  }
  setCached(SESSION_CLINIC_KEY, profile, CACHE_TTL.clinicConfig, { persist: true });
}

export function cacheKeyForClinics() {
  return CLINIC_KEY;
}
