import { getMeta, setMeta } from './db.js';
import {
  getPendingOutbox,
  markOutboxFailed,
  markOutboxInFlight,
  markOutboxCorrupted,
  markOutboxSynced,
  resetOutboxForRetry,
  recoverStaleInFlight,
  OUTBOX_STATUS,
} from './outbox.js';
import { detectAndRecordConflict } from './conflict.js';
import { cacheGetResponse } from './cache.js';
import { readOfflineOwnerScope } from './sessionScope.js';
import { isHisPatientRegisterUrl } from './entityTypes.js';
import { reconcilePatientCreate } from './reconcilePatient.js';
import { resolveOutboxItemPatientRefs } from './remapPatientRefs.js';

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

function parseMutationPayload(raw) {
  try {
    const parsed = raw ? JSON.parse(raw) : {};
    if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('payload is not an object');
    }
    return parsed;
  } catch (error) {
    const corrupted = new Error(`Contenu hors ligne illisible: ${error?.message || 'JSON invalide'}`);
    corrupted.code = 'OFFLINE_CORRUPTED_PAYLOAD';
    throw corrupted;
  }
}

/**
 * Replay one outbox row against the API.
 * @returns {Promise<'synced' | 'failed' | 'conflict' | 'skipped' | 'blocked'>}
 */
export async function replayOutboxItem(item, client) {
  const scope = readOfflineOwnerScope();
  if (!item.owner_key || item.owner_key !== scope.ownerKey || !scope.userId) {
    // Never replay another user's queued PHI mutation with the current cookies.
    return 'skipped';
  }

  // Dependents queued against offline_* patient ids must wait until the
  // registration row reconciles and rewrites their foreign keys.
  const resolved = await resolveOutboxItemPatientRefs(item);
  if (resolved.blockedTempIds.length) {
    return 'blocked';
  }
  const playable = resolved.item;

  const payload = parseMutationPayload(playable.payload_json);
  const params = parseJson(playable.params_json, null);
  const headers = {
    ...parseJson(playable.headers_json),
    'X-Client-Request-Id': playable.client_request_id,
    'X-Record-Version': String(playable.record_version || 1),
  };

  const method = String(playable.method || 'POST').toLowerCase();
  const config = { headers, params: params || undefined };

  let response;
  if (method === 'post') {
    response = await client.post(playable.url, payload, config);
  } else if (method === 'patch') {
    response = await client.patch(playable.url, payload, config);
  } else if (method === 'put') {
    response = await client.put(playable.url, payload, config);
  } else if (method === 'delete') {
    response = await client.delete(playable.url, config);
  } else {
    throw new Error(`Unsupported outbox method: ${method}`);
  }

  const serverData = response?.data;
  const localOptimistic = parseJson(playable.optimistic_json);

  if (response?.status === 409 || serverData?.conflict) {
    await detectAndRecordConflict({
      clientRequestId: playable.client_request_id,
      entityType: playable.entity_type,
      entityId: serverData?.id || localOptimistic?.id,
      localPayload: localOptimistic,
      remotePayload: serverData?.server_copy || serverData,
    });
    return 'conflict';
  }

  await markOutboxSynced(playable.id, serverData);

  if (
    playable.entity_type === 'patient'
    && isHisPatientRegisterUrl(playable.url)
    && serverData?.patient_number
  ) {
    await reconcilePatientCreate({
      clientRequestId: playable.client_request_id,
      localOptimistic,
      serverPatient: serverData,
    });
  }

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
    const scope = readOfflineOwnerScope();
    if (!scope.userId) {
      return { synced: 0, failed: 0, conflicts: 0, skipped: true };
    }
    await recoverStaleInFlight();
    const pending = await getPendingOutbox(25, { ownerKey: scope.ownerKey });
    for (const item of pending) {
      // Probe dependency before marking in-flight so blocked dependents stay
      // pending and retry after the patient registration remap completes.
      const preflight = await resolveOutboxItemPatientRefs(item);
      if (preflight.blockedTempIds.length) {
        continue;
      }

      await markOutboxInFlight(item.id);
      try {
        const result = await replayOutboxItem(item, client);
        if (result === 'synced') synced += 1;
        else if (result === 'conflict') conflicts += 1;
        else if (result === 'blocked') {
          // Registration may have been mid-flight; restore pending for retry.
          await resetOutboxForRetry(item.id);
        } else if (result === 'skipped') {
          await markOutboxFailed(item.id, new Error('owner mismatch'), 12);
        } else failed += 1;
      } catch (error) {
        if (error?.code === 'OFFLINE_CORRUPTED_PAYLOAD') {
          await markOutboxCorrupted(item.id, error.message);
          failed += 1;
          continue;
        }
        const attempt = Number(item.attempt_count || 0) + 1;
        if (isNetworkError(error)) {
          await markOutboxFailed(item.id, error, attempt);
          failed += 1;
          break;
        }
        if (error?.response?.status === 409) {
          const localOptimistic = parseJson(item.optimistic_json);
          const detail = error.response?.data?.detail;
          const duplicateMatch = (
            item.entity_type === 'patient'
            && isHisPatientRegisterUrl(item.url)
            && detail?.code === 'duplicate_patient'
            && Array.isArray(detail.matches)
            && detail.matches.length === 1
            && detail.matches[0]?.id
            && detail.matches[0]?.patient_number
          ) ? detail.matches[0] : null;
          if (duplicateMatch) {
            // Another device registered this exact patient first. Adopt the
            // canonical dossier and remap queued billing/admission work instead
            // of leaving reception on a permanent provisional identity.
            await markOutboxSynced(item.id, duplicateMatch);
            await reconcilePatientCreate({
              clientRequestId: item.client_request_id,
              localOptimistic,
              serverPatient: duplicateMatch,
            });
            synced += 1;
            continue;
          }
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
