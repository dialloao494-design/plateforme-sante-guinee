/** Pharmacy workstation helpers — labels, alerts, local movement log. */

export const PHARMACY_STATUS = {
  pending: { label: 'En attente', tone: 'warning' },
  preparing: { label: 'Préparé', tone: 'accent' },
  ready: { label: 'Prêt', tone: 'accent' },
  partially_dispensed: { label: 'Partiellement délivré', tone: 'info' },
  dispensed: { label: 'Délivré', tone: 'success' },
  cancelled: { label: 'Annulé', tone: 'muted' },
};

export function statusMeta(status) {
  return PHARMACY_STATUS[status] || { label: status || '—', tone: 'muted' };
}

const MOVEMENTS_KEY = 'pharmacy_dispense_movements';

export function loadMovements() {
  try {
    const raw = localStorage.getItem(MOVEMENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveMovement(entry) {
  const next = [{ ...entry, id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}` }, ...loadMovements()];
  localStorage.setItem(MOVEMENTS_KEY, JSON.stringify(next.slice(0, 100)));
  return next;
}

export function daysUntil(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  d.setHours(0, 0, 0, 0);
  return Math.round((d - today) / (1000 * 60 * 60 * 24));
}

export function computeStockAlerts(stock) {
  const out = [];
  const low = [];
  const expiring = [];
  const expired = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (const item of stock) {
    if (item.quantity <= 0) {
      out.push(item);
    } else if (item.low_stock || item.quantity <= item.reorder_level) {
      low.push(item);
    }
    if (item.expiry_date) {
      const exp = new Date(item.expiry_date);
      exp.setHours(0, 0, 0, 0);
      const diff = Math.round((exp - today) / (1000 * 60 * 60 * 24));
      if (diff < 0) expired.push({ ...item, days: diff });
      else if (diff <= 30) expiring.push({ ...item, days: diff });
    }
  }
  return { out, low, expiring, expired };
}

export function totalStockValue(stock) {
  return stock.reduce((sum, i) => sum + (i.quantity || 0) * (i.unit_price_gnf || 0), 0);
}

export function filterStock(stock, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return stock;
  return stock.filter(
    (i) =>
      i.medication_name?.toLowerCase().includes(q) ||
      i.sku?.toLowerCase().includes(q) ||
      i.supplier?.toLowerCase().includes(q) ||
      i.batch_number?.toLowerCase().includes(q)
  );
}

export function filterOrders(orders, { status, query }) {
  let list = orders;
  if (status && status !== 'all') {
    list = list.filter((o) => o.status === status);
  }
  const q = String(query || '').trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    (o) =>
      o.patient_name?.toLowerCase().includes(q) ||
      o.doctor_name?.toLowerCase().includes(q) ||
      o.medications?.toLowerCase().includes(q)
  );
}
