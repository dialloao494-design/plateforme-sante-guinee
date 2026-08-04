import { offlineDb } from './db.js';
import { classifyRequest } from './entityTypes.js';

export const OUTBOX_STATUS = {
  PENDING: 'pending',
  IN_FLIGHT: 'in_flight',
  SYNCED: 'synced',
  FAILED: 'failed',
  DEAD: 'dead',
};

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
  return {
    id: tempId,
    offline: true,
    entity_type: entityType,
    created_at: now,
    updated_at: now,
    record_version: 1,
    ...((typeof payload === 'object' && payload !== null) ? payload : {}),
  };
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

  const optimistic = buildOptimisticResponse(data, type);
  const now = Date.now();

  await offlineDb.outbox.add({
    client_request_id: reqId,
    entity_type: type,
    operation: op,
    method: String(method).toUpperCase(),
    url: String(url),
    payload_json: JSON.stringify(data ?? {}),
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

  return { client_request_id: reqId, optimistic };
}

export async function getPendingOutbox(limit = 50) {
  const now = Date.now();
  const rows = await offlineDb.outbox
    .where('status')
    .anyOf([OUTBOX_STATUS.PENDING, OUTBOX_STATUS.FAILED])
    .toArray();
  return rows
    .filter((r) => !r.next_retry_at || r.next_retry_at <= now)
    .sort((a, b) => a.created_at - b.created_at)
    .slice(0, limit);
}

export async function listOutboxByStatus(status) {
  return offlineDb.outbox.where('status').equals(status).toArray();
}

export async function countPendingOutbox() {
  const pending = await offlineDb.outbox.where('status').equals(OUTBOX_STATUS.PENDING).count();
  const failed = await offlineDb.outbox.where('status').equals(OUTBOX_STATUS.FAILED).count();
  const inFlight = await offlineDb.outbox.where('status').equals(OUTBOX_STATUS.IN_FLIGHT).count();
  return pending + failed + inFlight;
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

export async function resetOutboxForRetry(id) {
  await offlineDb.outbox.update(id, {
    status: OUTBOX_STATUS.PENDING,
    next_retry_at: Date.now(),
    updated_at: Date.now(),
  });
}
