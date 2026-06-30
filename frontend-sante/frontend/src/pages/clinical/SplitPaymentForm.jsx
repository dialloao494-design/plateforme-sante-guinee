import { useMemo } from 'react';
import { formatGNF } from '../../utils/appointmentPresentation.js';

const makeLineId = () =>
  typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `line-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

export const createEmptyPaymentLine = (overrides = {}) => ({
  id: makeLineId(),
  amount_gnf: '',
  payment_method: '',
  reference: '',
  ...overrides,
});

export const createInitialPaymentLines = (remainingBalance = '') => [
  createEmptyPaymentLine({
    amount_gnf: remainingBalance !== '' && remainingBalance != null ? String(remainingBalance) : '',
    payment_method: 'orange_money',
  }),
];

const parseAmount = (value) => {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : 0;
};

export function validateSplitPayments(lines, remainingBalance) {
  if (!lines.length) {
    return 'Ajoutez au moins un paiement.';
  }
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (!line.payment_method) {
      return `Paiement #${i + 1} : sélectionnez un mode de paiement.`;
    }
    if (line.amount_gnf === '' || line.amount_gnf == null) {
      return `Paiement #${i + 1} : indiquez un montant.`;
    }
    if (parseAmount(line.amount_gnf) <= 0) {
      return `Paiement #${i + 1} : le montant doit être supérieur à zéro.`;
    }
  }
  const totalNew = lines.reduce((sum, line) => sum + parseAmount(line.amount_gnf), 0);
  if (totalNew > remainingBalance) {
    return `Le total encaissé (${formatGNF(totalNew)}) dépasse le reste à payer (${formatGNF(remainingBalance)}).`;
  }
  return null;
}

export default function SplitPaymentForm({
  lines,
  onChange,
  methods,
  invoiceTotal,
  alreadyPaid,
  remainingBalance,
  loading,
  disabled,
  onSubmit,
}) {
  const totalNew = useMemo(
    () => lines.reduce((sum, line) => sum + parseAmount(line.amount_gnf), 0),
    [lines],
  );
  const totalReceived = alreadyPaid + totalNew;
  const remainingAfter = Math.max(0, invoiceTotal - totalReceived);
  const validationError = validateSplitPayments(lines, remainingBalance);

  const updateLine = (id, patch) => {
    onChange(lines.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const addLine = () => {
    onChange([...lines, createEmptyPaymentLine()]);
  };

  const removeLine = (id) => {
    if (lines.length <= 1) return;
    onChange(lines.filter((line) => line.id !== id));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validationError) return;
    onSubmit(lines);
  };

  return (
    <form className="reception-split-payment" onSubmit={handleSubmit}>
      <div className="reception-split-payment__summary">
        <div className="reception-split-payment__summary-item">
          <span>Total facture</span>
          <strong>{formatGNF(invoiceTotal)}</strong>
        </div>
        <div className="reception-split-payment__summary-item">
          <span>Total reçu</span>
          <strong>{formatGNF(totalReceived)}</strong>
        </div>
        <div className="reception-split-payment__summary-item">
          <span>Reste à payer</span>
          <strong className={remainingAfter > 0 ? 'reception-split-payment__remaining--due' : ''}>
            {formatGNF(remainingAfter)}
          </strong>
        </div>
      </div>

      <div className="reception-split-payment__lines">
        {lines.map((line, index) => (
          <fieldset key={line.id} className="reception-split-payment__line reception-his-nested-fieldset">
            <legend>Paiement #{index + 1}</legend>
            <div className="reception-his-form-row reception-his-form-row--3">
              <label>
                Mode de paiement *
                <select
                  value={line.payment_method}
                  onChange={(e) => updateLine(line.id, { payment_method: e.target.value })}
                  required
                >
                  <option value="">— Sélectionner —</option>
                  {methods.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Montant *
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={line.amount_gnf}
                  onChange={(e) => updateLine(line.id, { amount_gnf: e.target.value })}
                  placeholder="0"
                  required
                />
              </label>
              <label>
                Référence
                <input
                  value={line.reference}
                  onChange={(e) => updateLine(line.id, { reference: e.target.value })}
                  placeholder="N° transaction, reçu…"
                />
              </label>
            </div>
            {lines.length > 1 && (
              <button
                type="button"
                className="clinical-btn clinical-btn--secondary reception-split-payment__remove"
                onClick={() => removeLine(line.id)}
                disabled={loading}
              >
                Supprimer le paiement
              </button>
            )}
          </fieldset>
        ))}
      </div>

      <div className="reception-split-payment__actions">
        <button
          type="button"
          className="clinical-btn clinical-btn--secondary"
          onClick={addLine}
          disabled={loading || disabled}
        >
          + Ajouter un paiement
        </button>
        <button
          type="submit"
          className="clinical-btn"
          disabled={loading || disabled || Boolean(validationError)}
        >
          Enregistrer les paiements
        </button>
      </div>

      {validationError && (
        <p className="reception-split-payment__validation" role="alert">
          {validationError}
        </p>
      )}
    </form>
  );
}
