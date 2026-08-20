import { offlineDb } from './db.js';
import { classifyRequest } from './entityTypes.js';
import { sortOutboxForPatientDependencies } from './remapPatientRefs.js';
import { readOfflineOwnerScope } from './sessionScope.js';

export const OUTBOX_STATUS = {
  PENDING: 'pending',
  IN_FLIGHT: 'in_flight',
  SYNCED: 'synced',
  FAILED: 'failed',
  DEAD: 'dead',
};

export function normalizeQueuedPayload(data) {
  if (typeof data !== 'string') return data ?? {};
  try {
    return JSON.parse(data);
  } catch {
    return data;
  }
}

/** @returns {string} */
export function generateClientRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `cr_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

/** Exponential backoff in ms (pure, unit-testable). */
export function computeBackoffMs(attempt, baseMs = 2000, maxMs = 300_000) {
  const exp = Math.min(maxMs, baseMs * 2 ** Math.max(0, attempt - 1));
  return Math.floor(exp);
}

export function buildOptimisticResponse(payload, entityType) {
  const now = new Date().toISOString();
  const tempId = `offline_${generateClientRequestId().slice(0, 8)}`;
  const base = {
    id: tempId,
    offline: true,
    entity_type: entityType,
    created_at: now,
    updated_at: now,
    record_version: 1,
    _sync_status: 'queued',
    ...((typeof payload === 'object' && payload !== null) ? payload : {}),
  };
  // Never invent a server dossier number offline — UI shows pending sync state.
  if (entityType === 'patient') {
    base.patient_number = null;
    base._pending_dossier = true;
  }
  return base;
}

/**
 * Enqueue a durable mutation (idempotent on client_request_id).
 * @returns {Promise<{ client_request_id: string, optimistic: object }>}
 */
export async function enqueueMutation({
  method,
  url,
  data,
  params,
  headers = {},
  clientRequestId,
  entityType,
  operation,
  recordVersion = 1,
  optimisticData,
}) {
  const reqId = clientRequestId || generateClientRequestId();
  const classified = classifyRequest(url, method);
  const type = entityType || classified.entityType;
  const op = operation || classified.operation;

  const existing = await offlineDb.outbox
    .where('client_request_id')
    .equals(reqId)
    .first();
  if (existing) {
    return {
      client_request_id: reqId,
      optimistic: existing.optimistic_json ? JSON.parse(existing.optimistic_json) : null,
      duplicate: true,
    };
  }

  const normalizedData = normalizeQueuedPayload(data);
  // Keep the replay payload server-safe while allowing the UI to preserve
  // locally known prices/totals that the server normally calculates.
  const optimistic = buildOptimisticResponse(
    optimisticData == null ? normalizedData : normalizeQueuedPayload(optimisticData),
    type,
  );
  const now = Date.now();
  const scope = readOfflineOwnerScope();

  await offlineDb.outbox.add({
    client_request_id: reqId,
    owner_key: scope.ownerKey,
    user_id: scope.userId,
    clinic_id: scope.clinicId,
    entity_type: type,
    operation: op,
    method: String(method).toUpperCase(),
    url: String(url),
    payload_json: JSON.stringify(normalizedData),
    params_json: params ? JSON.stringify(params) : null,
    headers_json: JSON.stringify(headers),
    record_version: recordVersion,
    optimistic_json: JSON.stringify(optimistic),
    status: OUTBOX_STATUS.PENDING,
    attempt_count: 0,
    created_at: now,
    updated_at: now,
    next_retry_at: now,
    last_error: null,
  });

  // Cache provisional patient so offline search/select can use the temp id
  // before connectivity returns; remap rewrites this row after sync.
  if (type === 'patient' && optimistic?.id) {
    try {
      const { cachePatientRecord } = await import('./cache.js');
      await cachePatientRecord({
        ...optimistic,
        full_name: [optimistic.first_name, optimistic.last_name].filter(Boolean).join(' '),
        phone: optimistic.phone,
      });
    } catch {
      /* non-fatal */
    }
  }

  return { client_request_id: reqId, optimistic };
}

export async function getPendingOutbox(limit = 50, { ownerKey, includeDeferred = false } = {}) {
  const now = Date.now();
  const scope = ownerKey ? { ownerKey } : readOfflineOwnerScope();
  const rows = await offlineDb.outbox
    .where('status')
    .anyOf([OUTBOX_STATUS.PENDING, OUTBOX_STATUS.FAILED])
    .toArray();
  const filtered = rows.filter((r) => {
    if (r.owner_key && r.owner_key !== scope.ownerKey) return false;
    // Legacy unscoped rows must never replay under another session.
    if (!r.owner_key) return false;
    return includeDeferred || !r.next_retry_at || r.next_retry_at <= now;
  });
  // Patient registration must sync before dependents that still reference
  // offline_* temp patient ids (admission, billing, lab, pharmacy, …).
  return sortOutboxForPatientDependencies(filtered).slice(0, limit);
}

export async function listOutboxByStatus(status) {
  return offlineDb.outbox.where('status').equals(status).toArray();
}

export async function countPendingOutbox({ ownerKey } = {}) {
  const scope = ownerKey ? { ownerKey } : readOfflineOwnerScope();
  const rows = await offlineDb.outbox
    .where('status')
    .anyOf([OUTBOX_STATUS.PENDING, OUTBOX_STATUS.FAILED, OUTBOX_STATUS.IN_FLIGHT])
    .toArray();
  return rows.filter((r) => r.owner_key && r.owner_key === scope.ownerKey).length;
}

export async function listDeadOutbox({ ownerKey } = {}) {
  const scope = ownerKey ? { ownerKey } : readOfflineOwnerScope();
  const rows = await offlineDb.outbox.where('status').equals(OUTBOX_STATUS.DEAD).toArray();
  return rows.filter((r) => r.owner_key && r.owner_key === scope.ownerKey);
}

export async function retryDeadOutbox(id) {
  const scope = readOfflineOwnerScope();
  const row = await offlineDb.outbox.get(id);
  if (!row || row.owner_key !== scope.ownerKey) return false;
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.PENDING,
    attempt_count: 0,
    next_retry_at: Date.now(),
    last_error: null,
    updated_at: Date.now(),
  });
  return true;
}

export async function recoverStaleInFlight(maxAgeMs = 60_000) {
  const scope = readOfflineOwnerScope();
  if (!scope.userId) return 0;
  const cutoff = Date.now() - maxAgeMs;
  const rows = await offlineDb.outbox.where('status').equals(OUTBOX_STATUS.IN_FLIGHT).toArray();
  const stale = rows.filter(
    (row) => row.owner_key === scope.ownerKey && Number(row.updated_at || 0) <= cutoff,
  );
  await offlineDb.transaction('rw', offlineDb.outbox, async () => {
    for (const row of stale) {
      await offlineDb.outbox.update(row.id, {
        status: OUTBOX_STATUS.PENDING,
        next_retry_at: Date.now(),
        last_error: 'Recovered after interrupted synchronization',
        updated_at: Date.now(),
      });
    }
  });
  return stale.length;
}

export async function markOutboxInFlight(id) {
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.IN_FLIGHT,
    updated_at: Date.now(),
  });
}

export async function markOutboxSynced(id, serverResponse = null) {
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.SYNCED,
    synced_at: Date.now(),
    updated_at: Date.now(),
    server_response_json: serverResponse ? JSON.stringify(serverResponse) : null,
    last_error: null,
  });
}

export async function markOutboxFailed(id, error, attemptCount) {
  const nextRetry = Date.now() + computeBackoffMs(attemptCount);
  const status = attemptCount >= 12 ? OUTBOX_STATUS.DEAD : OUTBOX_STATUS.FAILED;
  await offlineDb.outbox.update(id, {
    status,
    attempt_count: attemptCount,
    last_error: String(error?.message || error || 'sync failed'),
    next_retry_at: status === OUTBOX_STATUS.DEAD ? null : nextRetry,
    updated_at: Date.now(),
  });
}

export async function markOutboxCorrupted(id, detail = 'Corrupted offline payload') {
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.DEAD,
    attempt_count: 12,
    last_error: String(detail),
    next_retry_at: null,
    updated_at: Date.now(),
  });
}

export async function resetOutboxForRetry(id) {
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.PENDING,
    next_retry_at: Date.now(),
    updated_at: Date.now(),
  });
}
