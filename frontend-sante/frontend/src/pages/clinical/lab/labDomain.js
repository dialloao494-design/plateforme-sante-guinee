export const SAMPLE_TYPES = [
  { code: 'blood', label: 'Sang' },
  { code: 'urine', label: 'Urine' },
  { code: 'stool', label: 'Selles' },
  { code: 'lcr', label: 'LCR' },
  { code: 'pus', label: 'Pus' },
  { code: 'other', label: 'Autre' },
];

export const VALIDATION_STATUSES = [
  { value: 'pending', label: 'En attente' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'validated', label: 'Validé' },
  { value: 'rejected', label: 'Rejeté' },
];

export const ORDER_STATUS_MAP = {
  pending: 'ordered',
  in_progress: 'in_analysis',
  validated: 'completed',
  rejected: 'cancelled',
};

export const EMPTY_RESULT_ROW = { parameter: '', result: '', reference: '', unit: '' };

export function parseLabPayload(value) {
  if (!value) return null;
  try {
    const data = typeof value === 'string' ? JSON.parse(value) : value;
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

export function sampleCodesFromLabels(labels = []) {
  return labels.flatMap((label) => {
    const sample = SAMPLE_TYPES.find((item) => item.label === label);
    return sample ? [sample.code] : [];
  });
}

export const todayInputValue = () => new Date().toISOString().slice(0, 10);
export const nowInputValue = () => new Date().toTimeString().slice(0, 5);
