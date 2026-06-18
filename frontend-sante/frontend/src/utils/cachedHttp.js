import httpClient from '../services/httpClient.js';
import { buildCacheKey, getCached, invalidateCache, setCached } from './apiCache.js';

/**
 * GET with optional TTL cache. Returns axios-like `{ data }`.
 * Set `forceRefresh: true` to bypass cache.
 */
export async function cachedGet(url, config = {}) {
  const {
    cacheTtlMs = 0,
    cachePersist = false,
    forceRefresh = false,
    params,
    ...axiosConfig
  } = config;

  const key = buildCacheKey('get', url, params);

  if (cacheTtlMs > 0 && !forceRefresh) {
    const hit = getCached(key, { persist: cachePersist });
    if (hit !== undefined) {
      return { data: hit, fromCache: true };
    }
  }

  const response = await httpClient.get(url, { params, ...axiosConfig });
  if (cacheTtlMs > 0) {
    setCached(key, response.data, cacheTtlMs, { persist: cachePersist });
  }
  return response;
}

export function invalidateApiCache(prefix) {
  invalidateCache(prefix);
}

export { invalidateCache };
