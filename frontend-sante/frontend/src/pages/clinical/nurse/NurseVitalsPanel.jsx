import { ReadOnlyDisplay, TextAreaField } from './NurseFormPrimitives.jsx';

const numberField = (label, key, options = {}) => ({ label, key, ...options });

const VITAL_FIELDS = [
  numberField('Température', 'temperature_c', { step: '0.1', min: '30', max: '45', unit: '°C' }),
  numberField('Pouls', 'heart_rate', { min: '20', max: '250', unit: '/min' }),
  numberField('SpO₂', 'oxygen_saturation', { min: '50', max: '100', unit: '%' }),
  numberField('Respiration', 'respiratory_rate', { min: '5', max: '60', unit: '/min' }),
  numberField('Douleur', 'pain_score', { min: '0', max: '10', unit: '/10' }),
  numberField('Poids', 'weight_kg', { step: '0.1', min: '0.5', max: '500', unit: 'kg' }),
  numberField('Taille', 'height_cm', { step: '0.1', min: '30', max: '250', unit: 'cm' }),
  numberField('Périmètre brachial', 'arm_circumference_cm', { step: '0.1', min: '5', max: '80', unit: 'cm' }),
  numberField('Périmètre crânien', 'head_circumference_cm', { step: '0.1', min: '20', max: '80', unit: 'cm' }),
];

export default function NurseVitalsPanel({ form, bmi, alerts, onChange }) {
  return (
    <fieldset className="nurse-observation-block" data-testid="nurse-vitals-first">
      <legend>1 · Signes vitaux</legend>
      <p className="clinical-hint">Saisissez les paramètres observés. Les valeurs inhabituelles sont signalées sans établir de diagnostic.</p>
      {alerts.length > 0 && (
        <div className="nurse-alert-banner" role="alert">
          <strong>Revue clinique nécessaire</strong>
          <span>{alerts.join(' · ')}</span>
        </div>
      )}
      <div className="nurse-vitals-grid">
        <label className="nurse-vital-field">
          <span>Tension artérielle</span>
          <span className="nurse-his-bp-pair">
            <input aria-label="Tension systolique" name="bp_systolic" autoComplete="off" type="number" min="40" max="300" placeholder="Syst.…" value={form.bp_systolic} onChange={(event) => onChange({ bp_systolic: event.target.value })} />
            <span aria-hidden="true">/</span>
            <input aria-label="Tension diastolique" name="bp_diastolic" autoComplete="off" type="number" min="20" max="200" placeholder="Diast.…" value={form.bp_diastolic} onChange={(event) => onChange({ bp_diastolic: event.target.value })} />
            <small>mmHg</small>
          </span>
        </label>
        {VITAL_FIELDS.map(({ label, key, unit, ...inputProps }) => (
          <label className="nurse-vital-field" key={key}>
            <span>{label}</span>
            <span className="nurse-vital-input">
              <input type="number" name={key} autoComplete="off" value={form[key]} onChange={(event) => onChange({ [key]: event.target.value })} {...inputProps} />
              <small>{unit}</small>
            </span>
          </label>
        ))}
        <label className="nurse-vital-field">
          <span>Conscience</span>
          <select name="consciousness_level" value={form.consciousness_level} onChange={(event) => onChange({ consciousness_level: event.target.value })}>
            <option value="alert">Alerte</option>
            <option value="voice">Réagit à la voix</option>
            <option value="pain">Réagit à la douleur</option>
            <option value="unresponsive">Sans réaction</option>
          </select>
        </label>
        <label className="nurse-vital-field">
          <span>IMC</span>
          <ReadOnlyDisplay value={bmi || '—'} />
        </label>
      </div>
      <TextAreaField label="Observations associées" rows={2} value={form.vitals_observations} onChange={(event) => onChange({ vitals_observations: event.target.value })} />
    </fieldset>
  );
}
