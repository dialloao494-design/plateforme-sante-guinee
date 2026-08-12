/**
 * Temp → server patient ID / dossier-number reconciliation after outbox replay.
 */
import { offlineDb, setMeta, getMeta } from './db.js';
import { remapDependentRecords } from './remapPatientRefs.js';
import { readOfflineOwnerScope } from './sessionScope.js';

const listeners = new Set();

export function onPatientReconciled(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notify(event) {
  for (const fn of listeners) {
    try {
      fn(event);
    } catch {
      /* ignore */
    }
  }
}

export function isTempPatientId(id) {
  return typeof id === 'string' && id.startsWith('offline_');
}

export function buildRegistrationFingerprint(payload = {}) {
  const phone = String(payload.phone || '').replace(/\D/g, '').slice(-9);
  const first = String(payload.first_name || '').trim().toLowerCase();
  const last = String(payload.last_name || '').trim().toLowerCase();
  const dob = String(payload.date_of_birth || '').trim();
  return `reg:${phone}:${first}:${last}:${dob}`;
}

export async function findPendingRegistrationByFingerprint(fingerprint) {
  if (!fingerprint) return null;
  const scope = readOfflineOwnerScope();
  const rows = await offlineDb.outbox
    .where('status')
    .anyOf(['pending', 'failed', 'in_flight'])
    .toArray();
  for (const row of rows) {
    if (row.owner_key !== scope.ownerKey) continue;
    if (row.entity_type !== 'patient') continue;
    if (!/\/clinical\/reception\/his\/patients\/?$/.test(String(row.url || '').split('?')[0])) {
      continue;
    }
    try {
      const payload = JSON.parse(row.payload_json || '{}');
      if (buildRegistrationFingerprint(payload) === fingerprint) {
        return row;
      }
    } catch {
      /* ignore */
    }
  }
  return null;
}

export async function cacheReconciledPatient(serverPatient, { tempId, clientRequestId } = {}) {
  const scope = readOfflineOwnerScope();
  if (!scope.userId || !serverPatient?.id) return;
  const now = Date.now();
  await offlineDb.patients.put({
    owner_key: scope.ownerKey,
    patient_id: serverPatient.id,
    search_key: String(serverPatient.patient_number || serverPatient.id).toLowerCase(),
    payload_json: JSON.stringify(serverPatient),
    temp_id: tempId || null,
    client_request_id: clientRequestId || null,
    cached_at: now,
    expires_at: now + 7 * 24 * 60 * 60 * 1000,
  });
  if (tempId) {
    await setMeta(`idmap:${scope.ownerKey}:${tempId}`, {
      server_id: serverPatient.id,
      patient_number: serverPatient.patient_number,
      client_request_id: clientRequestId,
      reconciled_at: now,
    });
  }
}

export async function lookupIdMap(tempId) {
  if (!tempId) return null;
  const scope = readOfflineOwnerScope();
  return getMeta(`idmap:${scope.ownerKey}:${tempId}`, null);
}

/**
 * Apply server registration response onto a local optimistic patient.
 */
export function mergeReconciledPatient(localOptimistic, serverPatient) {
  if (!serverPatient || typeof serverPatient !== 'object') return localOptimistic;
  return {
    ...localOptimistic,
    ...serverPatient,
    _offline_queued: false,
    offline: false,
    _sync_status: 'synced',
    _temp_id: localOptimistic?.id,
    patient_number: serverPatient.patient_number,
    id: serverPatient.id,
  };
}

/**
 * Called after a patient-create outbox row syncs successfully.
 */
export async function reconcilePatientCreate({
  clientRequestId,
  localOptimistic,
  serverPatient,
}) {
  if (!serverPatient?.patient_number || !serverPatient?.id) {
    return { ok: false, reason: 'missing_server_dossier' };
  }
  const tempId = isTempPatientId(localOptimistic?.id) ? localOptimistic.id : null;
  await cacheReconciledPatient(serverPatient, { tempId, clientRequestId });

  let remap = { rewrittenOutbox: 0, rewrittenCaches: 0 };
  if (tempId) {
    // Rewrite every dependent outbox mutation + cached clinical row that still
    // points at the offline temp id before those rows are replayed.
    remap = await remapDependentRecords(tempId, serverPatient.id, {
      patientNumber: serverPatient.patient_number,
    });
  }

  const merged = mergeReconciledPatient(localOptimistic || {}, serverPatient);
  const event = {
    clientRequestId,
    tempId,
    serverPatient,
    merged,
    remap,
  };
  notify(event);
  return { ok: true, ...event };
}
