import { offlineDb } from './db.js';
import { generateClientRequestId } from './outbox.js';

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
  const id = await offlineDb.conflicts.add({
    conflict_id: generateClientRequestId(),
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
  const rows = await offlineDb.conflicts.orderBy('created_at').reverse().toArray();
  if (includeResolved) return rows;
  return rows.filter((r) => !r.resolved);
}

export async function resolveConflict(conflictId, resolution, mergedPayload = null) {
  await offlineDb.conflicts.update(conflictId, {
    resolution,
    resolved: true,
    resolved_at: Date.now(),
    merged_json: mergedPayload ? JSON.stringify(mergedPayload) : null,
  });
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
