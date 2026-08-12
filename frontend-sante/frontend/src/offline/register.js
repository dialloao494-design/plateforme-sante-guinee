import { enqueueMutation } from './outbox.js';
import { cacheGetResponse, getCachedGet } from './cache.js';
import { classifyRequest, isOnlineOnlyMutation } from './entityTypes.js';
import { bindHttpClient, cacheOnlineGet, flushOutbox, startAutoSync, stopAutoSync } from './sync.js';

let requestInterceptorId = null;
let responseInterceptorId = null;
let initialized = false;

const statusListeners = new Set();
let onlineStatus = typeof navigator !== 'undefined' ? navigator.onLine : true;

export function isBrowserOnline() {
  return onlineStatus;
}

export function onOnlineStatusChange(listener) {
  statusListeners.add(listener);
  listener(onlineStatus);
  return () => statusListeners.delete(listener);
}

function setOnlineStatus(next) {
  if (onlineStatus === next) return;
  onlineStatus = next;
  for (const fn of statusListeners) {
    try {
      fn(onlineStatus);
    } catch {
      /* ignore */
    }
  }
}

function isNetworkError(error) {
  if (!error) return false;
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') return true;
  return !error.response;
}

function isMutationMethod(method) {
  return ['post', 'patch', 'put', 'delete'].includes(String(method || '').toLowerCase());
}

function shouldSkipOffline(url = '') {
  const path = String(url);
  if (path.includes('/auth/')) return true;
  if (path.includes('/platform/')) return true;
  return false;
}

/**
 * Attach offline interceptors to the shared axios client.
 * Online flows are unchanged; offline/network failures queue or serve cache.
 */
export function attachOfflineInterceptors(httpClient) {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;
  bindHttpClient(httpClient);

  requestInterceptorId = httpClient.interceptors.request.use(async (config) => {
    const method = String(config.method || 'get').toLowerCase();
    const url = config.url || '';
    if (shouldSkipOffline(url)) return config;

    const classified = classifyRequest(url, method);

    if (method === 'get' && !navigator.onLine && classified.cacheable) {
      const cached = await getCachedGet(url, config.params);
      if (cached !== undefined) {
        config.adapter = () =>
          Promise.resolve({
            data: cached,
            status: 200,
            statusText: 'OK (offline cache)',
            headers: { 'x-offline-cache': 'true' },
            config,
            request: {},
          });
      }
      return config;
    }

    // Online-only mutations (HIS patient register): never enqueue — let the
    // request fail so reception cannot create silent duplicate outbox entries.
    if (
      isMutationMethod(method)
      && !navigator.onLine
      && classified.queueable
      && !isOnlineOnlyMutation(url, method)
    ) {
      const { optimistic, client_request_id } = await enqueueMutation({
        method,
        url,
        data: config.data,
        params: config.params,
        headers: config.headers,
        entityType: classified.entityType,
        operation: classified.operation,
      });

      config.adapter = () =>
        Promise.resolve({
          data: { ...optimistic, client_request_id, _offline_queued: true },
          status: 202,
          statusText: 'Accepted (offline queue)',
          headers: { 'x-offline-queued': 'true' },
          config,
          request: {},
        });
    }

    return config;
  });

  responseInterceptorId = httpClient.interceptors.response.use(
    async (response) => {
      const config = response.config || {};
      const method = String(config.method || 'get').toLowerCase();
      const url = config.url || '';
      if (method === 'get' && !shouldSkipOffline(url)) {
        await cacheOnlineGet(url, config.params, response.data);
      }
      return response;
    },
    async (error) => {
      const config = error?.config;
      if (!config || shouldSkipOffline(config.url)) {
        return Promise.reject(error);
      }

      const method = String(config.method || 'get').toLowerCase();
      const classified = classifyRequest(config.url, method);

      if (method === 'get' && isNetworkError(error) && classified.cacheable) {
        const cached = await getCachedGet(config.url, config.params);
        if (cached !== undefined) {
          return {
            data: cached,
            status: 200,
            statusText: 'OK (offline cache fallback)',
            headers: { 'x-offline-cache': 'true' },
            config,
            fromOfflineCache: true,
          };
        }
      }

      if (
        isMutationMethod(method)
        && isNetworkError(error)
        && classified.queueable
        && !isOnlineOnlyMutation(config.url, method)
      ) {
        const { optimistic, client_request_id } = await enqueueMutation({
          method,
          url: config.url,
          data: config.data,
          params: config.params,
          headers: config.headers,
          entityType: classified.entityType,
          operation: classified.operation,
        });

        return {
          data: { ...optimistic, client_request_id, _offline_queued: true },
          status: 202,
          statusText: 'Accepted (offline queue)',
          headers: { 'x-offline-queued': 'true' },
          config,
        };
      }

      return Promise.reject(error);
    }
  );
}

export function detachOfflineInterceptors(httpClient) {
  if (!initialized) return;
  if (requestInterceptorId !== null) {
    httpClient.interceptors.request.eject(requestInterceptorId);
    requestInterceptorId = null;
  }
  if (responseInterceptorId !== null) {
    httpClient.interceptors.response.eject(responseInterceptorId);
    responseInterceptorId = null;
  }
  initialized = false;
}

export async function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return null;
  }
  try {
    const { registerSW } = await import('virtual:pwa-register');
    const updateSW = registerSW({
      immediate: true,
      onOfflineReady() {
        console.info('[PWA] App ready for offline use');
      },
      onNeedRefresh() {
        console.info('[PWA] New version available');
      },
    });
    return updateSW;
  } catch (err) {
    console.warn('[PWA] Service worker registration skipped:', err?.message || err);
    return null;
  }
}

function hookBrowserConnectivity() {
  if (typeof window === 'undefined') return;

  const handleOnline = () => {
    setOnlineStatus(true);
    flushOutbox();
  };
  const handleOffline = () => setOnlineStatus(false);

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);
  setOnlineStatus(navigator.onLine);
}

/** Bootstrap offline support: SW, interceptors. Auto-sync starts after auth. */
export async function initOfflineSupport(httpClient) {
  if (typeof window === 'undefined') return;

  hookBrowserConnectivity();
  attachOfflineInterceptors(httpClient);
  // Do not flush the outbox until AuthContext confirms an authenticated user.
  // Callers should invoke startAutoSync(httpClient) after bootstrap succeeds.
  await registerServiceWorker();
}

export { startAutoSync, stopAutoSync };

export { flushOutbox, cacheGetResponse, getCachedGet };
