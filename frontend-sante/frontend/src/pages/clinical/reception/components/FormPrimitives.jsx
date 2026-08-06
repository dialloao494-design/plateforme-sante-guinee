import { formatGNF } from '../../../../utils/appointmentPresentation.js';

export const ReadOnlyDisplay = ({ value, hint }) => (
  <div className="reception-his-readonly-wrap">
    <div
      className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}
      aria-live="polite"
    >
      {value || ''}
    </div>
    {hint && !value ? <span className="reception-his-field-hint">{hint}</span> : null}
  </div>
);

export const AmountDisplay = ({ amountGnf, hint }) => {
  const hasAmount = amountGnf != null && amountGnf !== '' && !Number.isNaN(Number(amountGnf));
  return (
    <ReadOnlyDisplay
      value={hasAmount ? formatGNF(Number(amountGnf)) : ''}
      hint={hint}
    />
  );
};

export const DisplayField = ({ label, value, hint }) => (
  <label>
    {label}
    <ReadOnlyDisplay value={value} hint={hint} />
  </label>
);

export const FormNotice = ({ children }) => (
  children ? <p className="reception-his-form-notice">{children}</p> : null
);

export const GeneratedIdBanner = ({ label, value }) => {
  if (!value) return null;
  return (
    <div className="reception-his-generated-id">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
};

export const PaymentMethodRadios = ({ name, value, onChange, methods }) => (
  <div className="reception-his-payment-methods" role="radiogroup" aria-label="Mode de paiement">
    {methods.map((m) => (
      <label key={m.value} className="reception-his-payment-option">
        <input
          type="radio"
          name={name}
          value={m.value}
          checked={value === m.value}
          onChange={() => onChange(m.value)}
        />
        {m.label}
      </label>
    ))}
  </div>
);
