import { offlineDb } from './db.js';
import { generateClientRequestId } from './outbox.js';
import { readOfflineOwnerScope } from './sessionScope.js';

/**
 * Last-write-wins: pick newer record by version then timestamp.
 * @returns {'local' | 'remote' | 'tie'}
 */
export function resolveLastWriteWins(local, remote) {
  const localVersion = Number(local?.record_version ?? local?.version ?? 0);
  const remoteVersion = Number(remote?.record_version ?? remote?.version ?? 0);

  if (localVersion > remoteVersion) return 'local';
  if (remoteVersion > localVersion) return 'remote';

  const localTs = Date.parse(local?.updated_at || local?.modified_at || 0) || 0;
  const remoteTs = Date.parse(remote?.updated_at || remote?.modified_at || 0) || 0;

  if (localTs > remoteTs) return 'local';
  if (remoteTs > localTs) return 'remote';
  return 'tie';
}

export function mergeLastWriteWins(local, remote) {
  const winner = resolveLastWriteWins(local, remote);
  if (winner === 'local') return { ...remote, ...local, _conflict_winner: 'local' };
  if (winner === 'remote') return { ...local, ...remote, _conflict_winner: 'remote' };
  return { ...local, ...remote, _conflict_winner: 'tie' };
}

export async function recordConflict({
  clientRequestId,
  entityType,
  entityId,
  localPayload,
  remotePayload,
  resolution = 'pending',
}) {
  const scope = readOfflineOwnerScope();
  const id = await offlineDb.conflicts.add({
    conflict_id: generateClientRequestId(),
    owner_key: scope.ownerKey,
    user_id: scope.userId,
    clinic_id: scope.clinicId,
    client_request_id: clientRequestId,
    entity_type: entityType,
    entity_id: entityId || null,
    local_json: JSON.stringify(localPayload ?? {}),
    remote_json: JSON.stringify(remotePayload ?? {}),
    resolution,
    resolved: resolution !== 'pending',
    created_at: Date.now(),
    resolved_at: resolution !== 'pending' ? Date.now() : null,
  });
  return id;
}

export async function listConflicts({ includeResolved = false } = {}) {
  const scope = readOfflineOwnerScope();
  const rows = await offlineDb.conflicts.orderBy('created_at').reverse().toArray();
  return rows.filter((r) => {
    if (r.owner_key && r.owner_key !== scope.ownerKey) return false;
    if (!includeResolved && r.resolved) return false;
    return true;
  });
}

export async function resolveConflict(conflictId, resolution, mergedPayload = null) {
  const scope = readOfflineOwnerScope();
  const conflict = await offlineDb.conflicts.get(conflictId);
  if (!conflict || conflict.owner_key !== scope.ownerKey) return false;
  if (resolution === 'retry_local' || resolution === 'retry_merged') {
    const row = await offlineDb.outbox
      .where('client_request_id')
      .equals(conflict.client_request_id)
      .first();
    if (row && row.owner_key === scope.ownerKey) {
      const payload = resolution === 'retry_merged' && mergedPayload
        ? mergedPayload
        : JSON.parse(conflict.local_json || '{}');
      await offlineDb.outbox.update(row.id, {
        payload_json: JSON.stringify(payload),
        status: 'pending',
        attempt_count: 0,
        next_retry_at: Date.now(),
        record_version: Number(payload?.record_version || row.record_version || 1) + 1,
        last_error: null,
        updated_at: Date.now(),
      });
    }
  }
  await offlineDb.conflicts.update(conflictId, {
    resolution,
    resolved: true,
    resolved_at: Date.now(),
    merged_json: mergedPayload ? JSON.stringify(mergedPayload) : null,
  });
  return true;
}

export async function detectAndRecordConflict({
  clientRequestId,
  entityType,
  entityId,
  localPayload,
  remotePayload,
}) {
  const winner = resolveLastWriteWins(localPayload, remotePayload);
  if (winner === 'local' && JSON.stringify(localPayload) === JSON.stringify(remotePayload)) {
    return { conflict: false, winner: 'none' };
  }
  if (winner !== 'tie' && JSON.stringify(localPayload) === JSON.stringify(remotePayload)) {
    return { conflict: false, winner };
  }

  const conflictId = await recordConflict({
    clientRequestId,
    entityType,
    entityId,
    localPayload,
    remotePayload,
    resolution: winner === 'tie' ? 'pending' : `auto_${winner}`,
  });

  return {
    conflict: true,
    winner,
    conflictId,
    merged: mergeLastWriteWins(localPayload, remotePayload),
  };
}
