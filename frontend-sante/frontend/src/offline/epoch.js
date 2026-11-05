import { offlineDb, buildOwnerKey } from './db.js';

export function profileEpoch(profile) {
  const epoch = Number(profile?.offline_data_epoch ?? 1);
  return Number.isSafeInteger(epoch) && epoch > 0 ? epoch : 1;
}

// Keep original mutations exportable, but never replay a pre-reset generation.
export async function applyOfflineEpoch(profile) {
  if (!profile?.id || profile.clinic_id == null) return;
  const owner = buildOwnerKey(profile.id, profile.clinic_id);
  const epoch = profileEpoch(profile);
  const key = `offline_epoch:${owner}`;
  await offlineDb.transaction('rw', offlineDb.tables, async () => {
    const previous = await offlineDb.meta.get(key);
    if (previous?.value === epoch) return;
    if (epoch > 1 || previous) {
      for (const table of offlineDb.tables) {
        if (['outbox', 'conflicts', 'meta'].includes(table.name)) continue;
        await table.filter((row) => row.owner_key === owner).delete();
      }
      await offlineDb.meta.filter((row) => row.key.startsWith(`get:${owner}:`) || row.key.startsWith(`idmap:${owner}:`)).delete();
    }
    await offlineDb.outbox.filter((row) => row.owner_key === owner
      && profileEpoch(row) !== epoch && row.status !== 'synced').modify({
      status: 'dead', attempt_count: 12, next_retry_at: null,
      last_error: 'Clinique remise à zéro : ancienne opération conservée pour export, envoi interdit.',
      updated_at: Date.now(),
    });
    await offlineDb.meta.put({ key, value: epoch, updated_at: Date.now() });
  });
}

// Storage failure must not prevent an online login. Replay and cache reads also
// validate each row's generation, so stale records remain unusable if cleanup fails.
export async function prepareOfflineEpoch(profile) {
  try { await applyOfflineEpoch(profile); }
  catch { console.warn('[Offline] Stockage indisponible; anciennes opérations conservées.'); }
}
