/** Demo stock catalog — visible inventory for pharmacy operations (no backend stock module yet). */
export const PHARMACY_STOCK_CATALOG = [
  { sku: 'PARA-500', name: 'Paracétamol 500mg', qty: 240, unit: 'cp', threshold: 50 },
  { sku: 'AMOX-500', name: 'Amoxicilline 500mg', qty: 86, unit: 'cp', threshold: 30 },
  { sku: 'IBU-400', name: 'Ibuprofène 400mg', qty: 120, unit: 'cp', threshold: 40 },
  { sku: 'ORS-1L', name: 'SRO (sachets)', qty: 18, unit: 'sachets', threshold: 25 },
  { sku: 'ARTE-50', name: 'Artéméther-Luméfantrine', qty: 42, unit: 'cp', threshold: 20 },
];

const STORAGE_KEY = 'clinical_pharmacy_stock_qty';

export function loadStockLevels() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return Object.fromEntries(PHARMACY_STOCK_CATALOG.map((item) => [item.sku, item.qty]));
}

export function saveStockLevels(levels) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(levels));
}

export function deductStock(sku, amount = 1) {
  const levels = loadStockLevels();
  if (levels[sku] == null) return levels;
  levels[sku] = Math.max(0, levels[sku] - amount);
  saveStockLevels(levels);
  return levels;
}

export function stockWithLevels() {
  const levels = loadStockLevels();
  return PHARMACY_STOCK_CATALOG.map((item) => ({
    ...item,
    qty: levels[item.sku] ?? item.qty,
    low: (levels[item.sku] ?? item.qty) <= item.threshold,
  }));
}
