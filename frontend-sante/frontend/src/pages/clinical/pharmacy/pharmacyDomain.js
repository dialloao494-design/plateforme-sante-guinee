export const PAYMENT_METHODS = [
  { value: 'cash', label: 'Espèces' }, { value: 'orange_money', label: 'Orange Money' },
  { value: 'bank_transfer', label: 'Virement' }, { value: 'card', label: 'Carte bancaire' },
  { value: 'insurance', label: 'Assurance' },
];

export const PATIENT_NOTICE = 'Recherchez et sélectionnez un patient enregistré à la réception.';
export const BILLING_NOTICE = 'Enregistrez la demande de service pour activer la facturation.';
export const EMPTY_PAYMENT = { amount_gnf: '', payment_method: 'orange_money', reference: '' };

const id = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
export const emptyPaymentLine = () => ({ id: id('pay'), ...EMPTY_PAYMENT });
export const emptyMedicationLine = () => ({ id: id('line'), designation: '', quantity: '', unit_price_gnf: '', inventory_item_id: null });
export const initialMedicationLines = () => Array.from({ length: 4 }, emptyMedicationLine);

export const paymentMethodLabel = (value) => PAYMENT_METHODS.find((method) => method.value === value)?.label || value || '—';

export function medicationLineTotal(line) {
  const quantity = Number(line.quantity);
  const unitPrice = Number(line.unit_price_gnf);
  return Number.isFinite(quantity) && Number.isFinite(unitPrice) && quantity >= 1 && unitPrice >= 0
    ? quantity * unitPrice
    : 0;
}
