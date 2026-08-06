/**
 * Build a server-safe invoice line payload.
 * Catalog lines omit unit_price_gnf unless an explicit override reason is provided.
 */
export function buildInvoiceItemPayload(line) {
  const payload = {
    charge_type: line.charge_type,
    description: line.description,
    quantity: Number(line.quantity || 1),
    source_type: line.source_type || 'reception',
  };

  if (line.catalog_code) {
    payload.catalog_code = line.catalog_code;
  }
  if (line.source_ref) {
    payload.source_ref = line.source_ref;
  }

  const overrideReason = (line.price_override_reason || '').trim();
  if (overrideReason) {
    payload.price_override_reason = overrideReason;
    if (line.unit_price_gnf != null && line.unit_price_gnf !== '') {
      payload.unit_price_gnf = Number(line.unit_price_gnf);
    }
  } else if (!line.catalog_code && line.source_type !== 'service_request') {
    payload.unit_price_gnf = Number(line.unit_price_gnf || 0);
  }

  return payload;
}
