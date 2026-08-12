/**
 * Rewrite temp offline patient IDs → server patient IDs across outbox + caches.
 *
 * A patient created offline gets an `offline_*` temp id. Downstream mutations
 * (admission, billing, lab, pharmacy, nursing, etc.) may queue against that
 * temp id before connectivity returns. After registration syncs, every
 * dependent payload/URL/cache row must remap to the real server id so foreign
 * keys stay intact without duplication or data loss.
 */
import { offlineDb, getMeta, setMeta } from './db.js';
import { isHisPatientRegisterUrl } from './entityTypes.js';
import { readOfflineOwnerScope } from './sessionScope.js';

// Local status literals avoid a circular import with outbox.js.
const OUTBOX_PENDING = 'pending';
const OUTBOX_FAILED = 'failed';
const OUTBOX_IN_FLIGHT = 'in_flight';

function isTempPatientId(id) {
  return typeof id === 'string' && id.startsWith('offline_');
}

/** JSON keys that hold a patient primary key reference. */
export const PATIENT_REF_KEYS = new Set([
  'patient_id',
  'patientId',
  'patientID',
]);

const TEMP_ID_RE = /offline_[A-Za-z0-9_-]+/g;

/**
 * Deep-rewrite a JSON-compatible value, replacing tempId with serverId.
 * Also rewrites URL/path strings that embed the temp id.
 */
export function rewritePatientRefs(value, tempId, serverId) {
  if (tempId == null || serverId == null) return value;
  const temp = String(tempId);
  const server = serverId;

  if (value === tempId || value === temp) {
    return server;
  }

  if (typeof value === 'string') {
    if (value === temp) return server;
    if (value.includes(temp)) {
      return value.split(temp).join(String(server));
    }
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => rewritePatientRefs(item, tempId, serverId));
  }

  if (value && typeof value === 'object') {
    const out = {};
    for (const [key, child] of Object.entries(value)) {
      if (PATIENT_REF_KEYS.has(key) && (child === tempId || child === temp || String(child) === temp)) {
        out[key] = server;
      } else {
        out[key] = rewritePatientRefs(child, tempId, serverId);
      }
    }
    return out;
  }

  return value;
}

/** Collect distinct `offline_*` tokens from a JSON-compatible value / URL. */
export function collectTempPatientIds(value, into = new Set()) {
  if (value == null) return into;
  if (typeof value === 'string') {
    if (isTempPatientId(value)) into.add(value);
    const matches = value.match(TEMP_ID_RE);
    if (matches) {
      for (const m of matches) into.add(m);
    }
    return into;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectTempPatientIds(item, into);
    return into;
  }
  if (typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      if (PATIENT_REF_KEYS.has(key) && isTempPatientId(child)) {
        into.add(String(child));
      }
      collectTempPatientIds(child, into);
    }
  }
  return into;
}

export function outboxItemTempPatientIds(item) {
  const ids = new Set();
  try {
    collectTempPatientIds(item?.url, ids);
    collectTempPatientIds(JSON.parse(item?.payload_json || '{}'), ids);
    if (item?.params_json) {
      collectTempPatientIds(JSON.parse(item.params_json), ids);
    }
    if (item?.optimistic_json) {
      const optimistic = JSON.parse(item.optimistic_json);
      if (PATIENT_REF_KEYS.has('patient_id') && isTempPatientId(optimistic?.patient_id)) {
        ids.add(String(optimistic.patient_id));
      }
      // Do not treat the row's own optimistic entity id as a patient dependency
      // unless this is a non-patient mutation referencing patient_id.
      collectTempPatientIds(optimistic?.patient_id, ids);
    }
  } catch {
    /* ignore parse errors */
  }
  return [...ids];
}

export function isPatientRegistrationOutboxItem(item) {
  return (
    item?.entity_type === 'patient'
    && isHisPatientRegisterUrl(item?.url || '')
  );
}

/**
 * Sort pending outbox so patient registration creates flush before dependents.
 * Among equal priority, preserve FIFO by created_at.
 */
export function sortOutboxForPatientDependencies(rows) {
  return [...rows].sort((a, b) => {
    const aReg = isPatientRegistrationOutboxItem(a) ? 0 : 1;
    const bReg = isPatientRegistrationOutboxItem(b) ? 0 : 1;
    if (aReg !== bReg) return aReg - bReg;
    return (a.created_at || 0) - (b.created_at || 0);
  });
}

function parseJson(raw, fallback) {
  try {
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Persist + apply temp→server remap across pending/failed outbox rows and
 * domain caches owned by the current session.
 */
export async function remapDependentRecords(tempId, serverId, { patientNumber } = {}) {
  if (!isTempPatientId(tempId) || serverId == null) {
    return { rewrittenOutbox: 0, rewrittenCaches: 0 };
  }
  const scope = readOfflineOwnerScope();
  if (!scope.userId) {
    return { rewrittenOutbox: 0, rewrittenCaches: 0 };
  }

  await setMeta(`idmap:${scope.ownerKey}:${tempId}`, {
    server_id: serverId,
    patient_number: patientNumber || null,
    reconciled_at: Date.now(),
  });

  const rewrittenOutbox = await rewritePendingOutboxForPatient(tempId, serverId, scope.ownerKey);
  const rewrittenCaches = await rewriteCachedEntitiesForPatient(tempId, serverId, scope.ownerKey);
  return { rewrittenOutbox, rewrittenCaches };
}

export async function rewritePendingOutboxForPatient(tempId, serverId, ownerKey) {
  const scopeOwner = ownerKey || readOfflineOwnerScope().ownerKey;
  const rows = await offlineDb.outbox
    .where('status')
    .anyOf([OUTBOX_PENDING, OUTBOX_FAILED, OUTBOX_IN_FLIGHT])
    .toArray();

  let rewritten = 0;
  for (const row of rows) {
    if (row.owner_key !== scopeOwner) continue;
    // Never rewrite the registration row's own optimistic entity id into the
    // payload — that row already synced (or is syncing). Dependents only.
    if (isPatientRegistrationOutboxItem(row)) continue;

    const temps = outboxItemTempPatientIds(row);
    if (!temps.includes(String(tempId))) continue;

    const payload = rewritePatientRefs(parseJson(row.payload_json, {}), tempId, serverId);
    const params = row.params_json
      ? rewritePatientRefs(parseJson(row.params_json, null), tempId, serverId)
      : null;
    const optimistic = row.optimistic_json
      ? rewritePatientRefs(parseJson(row.optimistic_json, {}), tempId, serverId)
      : null;
    const url = rewritePatientRefs(row.url, tempId, serverId);

    await offlineDb.outbox.update(row.id, {
      url: String(url),
      payload_json: JSON.stringify(payload ?? {}),
      params_json: params == null ? null : JSON.stringify(params),
      optimistic_json: optimistic == null ? null : JSON.stringify(optimistic),
      updated_at: Date.now(),
      last_error: row.last_error,
    });
    rewritten += 1;
  }
  return rewritten;
}

const DOMAIN_TABLES = ['consultations', 'billing', 'pharmacy', 'lab', 'patients'];

export async function rewriteCachedEntitiesForPatient(tempId, serverId, ownerKey) {
  const scopeOwner = ownerKey || readOfflineOwnerScope().ownerKey;
  let rewritten = 0;
  const temp = String(tempId);
  const serverStr = String(serverId);

  for (const tableName of DOMAIN_TABLES) {
    const table = offlineDb[tableName];
    if (!table) continue;
    const rows = await table.toArray();
    for (const row of rows) {
      if (row.owner_key && row.owner_key !== scopeOwner) continue;
      const payload = parseJson(row.payload_json, null);
      const patientIdMatches = row.patient_id != null && String(row.patient_id) === temp;
      const searchMatches = row.search_key === `id:${temp}`;
      const payloadHasTemp = payload
        ? collectTempPatientIds(payload).has(temp)
        : false;
      if (!patientIdMatches && !searchMatches && !payloadHasTemp) continue;

      const next = {
        updated_at: Date.now(),
      };
      if (patientIdMatches) next.patient_id = serverStr;
      if (searchMatches) next.search_key = `id:${serverStr}`;
      if (tableName === 'patients' && String(row.patient_id) === temp) {
        next.patient_id = serverId;
      }
      if (payload) {
        next.payload_json = JSON.stringify(rewritePatientRefs(payload, tempId, serverId));
      }
      if (row.temp_id === temp) next.temp_id = null;
      await table.update(row.id, next);
      rewritten += 1;
    }
  }
  return rewritten;
}

/**
 * Resolve any remaining temp patient refs on an outbox item using idmap meta.
 * Returns { item, blockedTempIds } — blocked means no map yet (must wait).
 */
export async function resolveOutboxItemPatientRefs(item) {
  if (!item || isPatientRegistrationOutboxItem(item)) {
    return { item, blockedTempIds: [], remapped: false };
  }
  const scope = readOfflineOwnerScope();
  const temps = outboxItemTempPatientIds(item);
  if (!temps.length) {
    return { item, blockedTempIds: [], remapped: false };
  }

  let url = item.url;
  let payload = parseJson(item.payload_json, {});
  let params = item.params_json ? parseJson(item.params_json, null) : null;
  let optimistic = item.optimistic_json ? parseJson(item.optimistic_json, null) : null;
  const blocked = [];
  let remapped = false;

  for (const tempId of temps) {
    const mapped = await getMeta(`idmap:${scope.ownerKey}:${tempId}`, null);
    if (!mapped?.server_id) {
      blocked.push(tempId);
      continue;
    }
    const serverId = mapped.server_id;
    url = rewritePatientRefs(url, tempId, serverId);
    payload = rewritePatientRefs(payload, tempId, serverId);
    if (params != null) params = rewritePatientRefs(params, tempId, serverId);
    if (optimistic != null) optimistic = rewritePatientRefs(optimistic, tempId, serverId);
    remapped = true;
  }

  if (!remapped) {
    return { item, blockedTempIds: blocked, remapped: false };
  }

  const next = {
    ...item,
    url: String(url),
    payload_json: JSON.stringify(payload ?? {}),
    params_json: params == null ? null : JSON.stringify(params),
    optimistic_json: optimistic == null ? null : JSON.stringify(optimistic),
  };

  // Persist rewrite so subsequent flushes / UI see the server id.
  if (item.id != null && blocked.length === 0) {
    await offlineDb.outbox.update(item.id, {
      url: next.url,
      payload_json: next.payload_json,
      params_json: next.params_json,
      optimistic_json: next.optimistic_json,
      updated_at: Date.now(),
    });
  }

  return { item: next, blockedTempIds: blocked, remapped: true };
}
