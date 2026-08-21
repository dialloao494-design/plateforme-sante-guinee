import { remapDependentOutboxReferences } from './remapPatientRefs.js';

const listeners = new Set();

export function onInvoiceReconciled(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notify(event) {
  for (const listener of listeners) {
    try {
      listener(event);
    } catch {
      /* one stale view must not interrupt synchronization */
    }
  }
}

export async function reconcileInvoiceCreate({ clientRequestId, localOptimistic, serverInvoice }) {
  const tempId = String(localOptimistic?.id || '').startsWith('offline_')
    ? localOptimistic.id
    : null;
  if (!tempId || !serverInvoice?.id) return { ok: false, reason: 'missing_invoice_identity' };

  const remap = await remapDependentOutboxReferences(tempId, serverInvoice.id, {
    entity_type: 'billing',
    invoice_number: serverInvoice.invoice_number || null,
    client_request_id: clientRequestId,
  });
  const merged = {
    ...localOptimistic,
    ...serverInvoice,
    _offline_queued: false,
    offline: false,
    _sync_status: 'synced',
    _temp_id: tempId,
  };
  const event = { clientRequestId, tempId, serverInvoice, merged, remap };
  notify(event);
  return { ok: true, ...event };
}
