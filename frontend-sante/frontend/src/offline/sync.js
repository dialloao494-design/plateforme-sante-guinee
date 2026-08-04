import { getMeta, setMeta } from './db.js';
import {
  getPendingOutbox,
  markOutboxFailed,
  markOutboxInFlight,
  markOutboxSynced,
  OUTBOX_STATUS,
} from './outbox.js';
import { detectAndRecordConflict } from './conflict.js';
import { cacheGetResponse } from './cache.js';

let flushing = false;
let syncTimer = null;
let httpClientRef = null;
let onlineListeners = new Set();

const SYNC_META_KEY = 'last_sync_at';
const SYNC_INTERVAL_MS = 15_000;

export function getSyncState() {
  return { flushing, hasClient: Boolean(httpClientRef) };
}

export function onSyncStateChange(listener) {
  onlineListeners.add(listener);
  return () => onlineListeners.delete(listener);
}

function notifySyncState(extra = {}) {
  for (const fn of onlineListeners) {
    try {
      fn(extra);
    } catch {
      /* ignore */
    }
  }
}

export function bindHttpClient(client) {
  httpClientRef = client;
}

function isNetworkError(error) {
  if (!error) return false;
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') return true;
  return !error.response;
}

function parseJson(raw, fallback = {}) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Replay one outbox row against the API.
 * @returns {Promise<'synced' | 'failed' | 'conflict'>}
 */
export async function replayOutboxItem(item, client) {
  const payload = parseJson(item.payload_json);
  const params = parseJson(item.params_json, null);
  const headers = {
    ...parseJson(item.headers_json),
    'X-Client-Request-Id': item.client_request_id,
    'X-Record-Version': String(item.record_version || 1),
  };

  const method = String(item.method || 'POST').toLowerCase();
  const config = { headers, params: params || undefined };

  let response;
  if (method === 'post') {
    response = await client.post(item.url, payload, config);
  } else if (method === 'patch') {
    response = await client.patch(item.url, payload, config);
  } else if (method === 'put') {
    response = await client.put(item.url, payload, config);
  } else if (method === 'delete') {
    response = await client.delete(item.url, config);
  } else {
    throw new Error(`Unsupported outbox method: ${method}`);
  }

  const serverData = response?.data;
  const localOptimistic = parseJson(item.optimistic_json);

  if (response?.status === 409 || serverData?.conflict) {
    await detectAndRecordConflict({
      clientRequestId: item.client_request_id,
      entityType: item.entity_type,
      entityId: serverData?.id || localOptimistic?.id,
      localPayload: localOptimistic,
      remotePayload: serverData?.server_copy || serverData,
    });
    return 'conflict';
  }

  await markOutboxSynced(item.id, serverData);
  return 'synced';
}

/** Flush pending outbox mutations to the API. */
export async function flushOutbox(client = httpClientRef) {
  if (!client || flushing) {
    return { synced: 0, failed: 0, conflicts: 0, skipped: true };
  }
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return { synced: 0, failed: 0, conflicts: 0, offline: true };
  }

  flushing = true;
  notifySyncState({ flushing: true });

  let synced = 0;
  let failed = 0;
  let conflicts = 0;

  try {
    const pending = await getPendingOutbox(25);
    for (const item of pending) {
      await markOutboxInFlight(item.id);
      try {
        const result = await replayOutboxItem(item, client);
        if (result === 'synced') synced += 1;
        else if (result === 'conflict') conflicts += 1;
        else failed += 1;
      } catch (error) {
        const attempt = Number(item.attempt_count || 0) + 1;
        if (isNetworkError(error)) {
          await markOutboxFailed(item.id, error, attempt);
          failed += 1;
          break;
        }
        if (error?.response?.status === 409) {
          const localOptimistic = parseJson(item.optimistic_json);
          await detectAndRecordConflict({
            clientRequestId: item.client_request_id,
            entityType: item.entity_type,
            entityId: localOptimistic?.id,
            localPayload: localOptimistic,
            remotePayload: error.response?.data,
          });
          conflicts += 1;
          await markOutboxSynced(item.id, error.response?.data);
        } else {
          await markOutboxFailed(item.id, error, attempt);
          failed += 1;
        }
      }
    }
    await setMeta(SYNC_META_KEY, Date.now());
  } finally {
    flushing = false;
    notifySyncState({ flushing: false, synced, failed, conflicts });
  }

  return { synced, failed, conflicts };
}

export function startAutoSync(client = httpClientRef) {
  if (client) httpClientRef = client;
  stopAutoSync();

  const tick = async () => {
    if (typeof navigator !== 'undefined' && navigator.onLine) {
      await flushOutbox(httpClientRef);
    }
  };

  syncTimer = window.setInterval(tick, SYNC_INTERVAL_MS);
  window.addEventListener('online', onReconnect);
  tick();
}

export function stopAutoSync() {
  if (syncTimer) {
    window.clearInterval(syncTimer);
    syncTimer = null;
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('online', onReconnect);
  }
}

async function onReconnect() {
  notifySyncState({ online: true, recovering: true });
  await flushOutbox(httpClientRef);
  notifySyncState({ online: true, recovering: false });
}

export async function getLastSyncAt() {
  return getMeta(SYNC_META_KEY, null);
}

/** After successful online GET, refresh IndexedDB cache. */
export async function cacheOnlineGet(url, params, data) {
  try {
    await cacheGetResponse(url, params, data);
  } catch {
    /* non-fatal */
  }
}

export { OUTBOX_STATUS };
