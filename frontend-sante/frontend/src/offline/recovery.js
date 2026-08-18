import { offlineDb } from './db.js';
import { readOfflineOwnerScope } from './sessionScope.js';

function parseForExport(raw) {
  if (raw == null) return { value: null, valid: true };
  try {
    return { value: JSON.parse(raw), valid: true };
  } catch {
    return { value: raw, valid: false };
  }
}

/** Build a clinic-scoped recovery bundle. Authentication headers are excluded. */
export async function buildOfflineRecoveryExport() {
  const scope = readOfflineOwnerScope();
  if (!scope.userId) throw new Error('Aucune session clinique active.');
  const [outboxRows, conflicts] = await Promise.all([
    offlineDb.outbox.toArray(),
    offlineDb.conflicts.toArray(),
  ]);
  const ownedOutbox = outboxRows.filter((row) => row.owner_key === scope.ownerKey);
  const integrityWarnings = [];
  const mutations = ownedOutbox.map((row) => {
    const payload = parseForExport(row.payload_json);
    const params = parseForExport(row.params_json);
    if (!payload.valid) integrityWarnings.push(`Mutation ${row.client_request_id}: contenu illisible`);
    if (!params.valid) integrityWarnings.push(`Mutation ${row.client_request_id}: paramètres illisibles`);
    return {
      local_row_id: row.id,
      client_request_id: row.client_request_id,
      entity_type: row.entity_type,
      operation: row.operation,
      method: row.method,
      url: row.url,
      payload: payload.value,
      params: params.value,
      status: row.status,
      attempt_count: row.attempt_count,
      created_at: row.created_at,
      updated_at: row.updated_at,
      last_error: row.last_error,
    };
  });
  return {
    format: 'sante-guinee-offline-recovery-v1',
    exported_at: new Date().toISOString(),
    clinic_id: scope.clinicId,
    user_id: scope.userId,
    warning: 'Contient des données de santé. Remettre uniquement au support autorisé de la clinique.',
    integrity_warnings: integrityWarnings,
    mutations,
    conflicts: conflicts
      .filter((row) => row.owner_key === scope.ownerKey)
      .map((row) => ({
        conflict_id: row.conflict_id,
        client_request_id: row.client_request_id,
        entity_type: row.entity_type,
        entity_id: row.entity_id,
        local: parseForExport(row.local_json).value,
        remote: parseForExport(row.remote_json).value,
        resolution: row.resolution,
        resolved: row.resolved,
        created_at: row.created_at,
      })),
  };
}

export function recoveryExportFilename(clinicId, now = new Date()) {
  const stamp = now.toISOString().replace(/[:.]/g, '-');
  return `sante-guinee-recuperation-clinique-${clinicId || 'inconnue'}-${stamp}.json`;
}

export async function downloadOfflineRecoveryExport() {
  const bundle = await buildOfflineRecoveryExport();
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = recoveryExportFilename(bundle.clinic_id);
  link.click();
  URL.revokeObjectURL(url);
  return bundle;
}
