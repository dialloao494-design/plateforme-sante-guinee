/** In-memory + sessionStorage TTL cache for GET responses (low-bandwidth clinics). */

const memory = new Map();

const SESSION_PREFIX = 'sg_api_cache:';

function stableParams(params) {
  if (!params || typeof params !== 'object') {
    return '';
  }
  return Object.keys(params)
    .sort()
    .map((k) => `${k}=${String(params[k])}`)
    .join('&');
}

export function buildCacheKey(method, url, params) {
  const uid =
    typeof window !== 'undefined'
      ? localStorage.getItem('user_id') || localStorage.getItem('user_role') || ''
      : '';
  return `${uid}:${String(method || 'get').toLowerCase()}:${url}?${stableParams(params)}`;
}

function readSession(key) {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(SESSION_PREFIX + key);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed.expiresAt !== 'number') {
      return null;
    }
    if (Date.now() > parsed.expiresAt) {
      sessionStorage.removeItem(SESSION_PREFIX + key);
      return null;
    }
    return parsed.value;
  } catch {
    return null;
  }
}

function writeSession(key, value, ttlMs) {
  if (typeof window === 'undefined' || ttlMs <= 0) {
    return;
  }
  try {
    sessionStorage.setItem(
      SESSION_PREFIX + key,
      JSON.stringify({ value, expiresAt: Date.now() + ttlMs })
    );
  } catch {
    /* quota — memory cache still works */
  }
}

export function getCached(key, { persist = false } = {}) {
  const mem = memory.get(key);
  if (mem && Date.now() <= mem.expiresAt) {
    return mem.value;
  }
  if (mem) {
    memory.delete(key);
  }
  if (persist) {
    return readSession(key);
  }
  return undefined;
}

export function setCached(key, value, ttlMs, { persist = false } = {}) {
  if (ttlMs <= 0) {
    return;
  }
  memory.set(key, { value, expiresAt: Date.now() + ttlMs });
  if (persist) {
    writeSession(key, value, ttlMs);
  }
}

export function invalidateCache(prefix = '') {
  for (const key of [...memory.keys()]) {
    if (!prefix || key.includes(prefix)) {
      memory.delete(key);
    }
  }
  if (typeof window === 'undefined') {
    return;
  }
  try {
    const keys = [];
    for (let i = 0; i < sessionStorage.length; i += 1) {
      const k = sessionStorage.key(i);
      if (k?.startsWith(SESSION_PREFIX) && (!prefix || k.includes(prefix))) {
        keys.push(k);
      }
    }
    keys.forEach((k) => sessionStorage.removeItem(k));
  } catch {
    /* ignore */
  }
}

/** TTL presets (ms) tuned for clinic LAN / 3G. */
export const CACHE_TTL = {
  authProfile: 5 * 60 * 1000,
  clinicConfig: 30 * 60 * 1000,
  clinicDoctors: 10 * 60 * 1000,
  immunizationSchedule: 24 * 60 * 60 * 1000,
  operationsSummary: 45 * 1000,
  workflowQueue: 20 * 1000,
  staticList: 60 * 60 * 1000,
};
