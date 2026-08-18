import { offlineDb } from './db.js';
import { readOfflineOwnerScope } from './sessionScope.js';

export const OFFLINE_RECOVERY_FORMAT = 'sante-guinee-offline-recovery-v2';

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
  const ownedConflicts = conflicts.filter((row) => row.owner_key === scope.ownerKey);
  const exportedConflicts = ownedConflicts.map((row) => {
    const local = parseForExport(row.local_json);
    const remote = parseForExport(row.remote_json);
    if (!local.valid) integrityWarnings.push(`Conflit ${row.conflict_id}: copie locale illisible`);
    if (!remote.valid) integrityWarnings.push(`Conflit ${row.conflict_id}: copie serveur illisible`);
    return {
      conflict_id: row.conflict_id,
      client_request_id: row.client_request_id,
      entity_type: row.entity_type,
      entity_id: row.entity_id,
      local: local.value,
      remote: remote.value,
      resolution: row.resolution,
      resolved: row.resolved,
      created_at: row.created_at,
    };
  });
  const bundle = {
    format: OFFLINE_RECOVERY_FORMAT,
    exported_at: new Date().toISOString(),
    clinic_id: scope.clinicId,
    user_id: scope.userId,
    warning: 'Contient des données de santé. Remettre uniquement au support autorisé de la clinique.',
    manifest: {
      mutation_count: mutations.length,
      conflict_count: exportedConflicts.length,
      integrity_warning_count: integrityWarnings.length,
    },
    integrity_warnings: integrityWarnings,
    mutations,
    conflicts: exportedConflicts,
  };
  const validation = validateOfflineRecoveryExport(bundle, scope);
  if (!validation.valid) {
    throw new Error(`Export de récupération invalide: ${validation.errors.join(' · ')}`);
  }
  return bundle;
}

/** Validate a recovery file before download or support hand-off. */
export function validateOfflineRecoveryExport(bundle, expectedScope = null) {
  const errors = [];
  if (!bundle || typeof bundle !== 'object' || Array.isArray(bundle)) {
    return { valid: false, errors: ['Le fichier ne contient pas un objet de récupération.'] };
  }
  if (bundle.format !== OFFLINE_RECOVERY_FORMAT) errors.push('Version de fichier non prise en charge.');
  if (!bundle.exported_at || Number.isNaN(Date.parse(bundle.exported_at))) errors.push("Date d'export invalide.");
  if (bundle.clinic_id == null || bundle.user_id == null) errors.push('Clinique ou utilisateur absent.');
  if (!Array.isArray(bundle.mutations) || !Array.isArray(bundle.conflicts)) {
    errors.push('Listes de récupération absentes.');
  }
  if (!Array.isArray(bundle.integrity_warnings)) errors.push("Liste d'intégrité absente.");
  const mutations = Array.isArray(bundle.mutations) ? bundle.mutations : [];
  mutations.forEach((row, index) => {
    if (!row?.client_request_id || !row?.url || !row?.method || !row?.status) {
      errors.push(`Mutation ${index + 1} incomplète.`);
    }
  });
  const manifest = bundle.manifest;
  if (!manifest
      || manifest.mutation_count !== mutations.length
      || manifest.conflict_count !== (Array.isArray(bundle.conflicts) ? bundle.conflicts.length : 0)
      || manifest.integrity_warning_count !== (Array.isArray(bundle.integrity_warnings) ? bundle.integrity_warnings.length : 0)) {
    errors.push('Le manifeste ne correspond pas au contenu exporté.');
  }
  if (expectedScope) {
    if (String(bundle.clinic_id) !== String(expectedScope.clinicId)
        || String(bundle.user_id) !== String(expectedScope.userId)) {
      errors.push("Le fichier n'appartient pas à la session clinique active.");
    }
  }
  return { valid: errors.length === 0, errors };
}

export function recoveryExportFilename(clinicId, now = new Date()) {
  const stamp = now.toISOString().replace(/[:.]/g, '-');
  return `sante-guinee-recuperation-clinique-${clinicId || 'inconnue'}-${stamp}.json`;
}

export async function downloadOfflineRecoveryExport() {
  const bundle = await buildOfflineRecoveryExport();
  const validation = validateOfflineRecoveryExport(bundle, readOfflineOwnerScope());
  if (!validation.valid) throw new Error(`Export bloqué: ${validation.errors.join(' · ')}`);
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = recoveryExportFilename(bundle.clinic_id);
  link.click();
  URL.revokeObjectURL(url);
  return bundle;
}
