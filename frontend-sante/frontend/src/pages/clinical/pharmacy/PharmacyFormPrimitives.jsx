import { formatGNF } from '../../../utils/clinicalPresentation.js';

export function ReadOnlyDisplay({ value }) {
  return <div className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}>{value || '—'}</div>;
}

export function DisplayField({ label, value }) {
  return <div className="pharmacy-his-display-field"><span>{label}</span><ReadOnlyDisplay value={value} /></div>;
}

export function AmountDisplay({ amountGnf }) {
  const valid = amountGnf != null && amountGnf !== '' && !Number.isNaN(Number(amountGnf));
  return <ReadOnlyDisplay value={valid ? formatGNF(Number(amountGnf)) : ''} />;
}

export function FormNotice({ children }) {
  return children ? <p className="reception-his-form-notice">{children}</p> : null;
}

export function PaymentMethodRadios({ name, value, onChange, methods, disabled }) {
  return (
    <div className="reception-his-payment-methods" role="radiogroup" aria-label="Mode de paiement">
      {methods.map((method) => (
        <label key={method.value} className="reception-his-payment-option">
          <input type="radio" name={name} checked={value === method.value} onChange={() => onChange(method.value)} disabled={disabled} />
          {method.label}
        </label>
      ))}
    </div>
  );
}
