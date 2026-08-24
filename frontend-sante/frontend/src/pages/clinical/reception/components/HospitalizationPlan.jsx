import { formatGNF } from '../../../../utils/appointmentPresentation.js';

export default function HospitalizationPlan({ form, specialties, options, setForm }) {
  const availableSpecialties = specialties.filter((item) => item.code !== 'pediatrics');
  const selectAccommodation = (option) => {
    const type = option.code === 'hospitalization_private_cabin' ? 'private_cabin' : 'standard_bed';
    setForm((previous) => ({ ...previous, accommodation_type: type, catalog_code: option.code,
      charge_type: 'hospitalization', unit_price_gnf: option.price_gnf,
      service_name: previous.specialty_code ? `${option.label} — ${availableSpecialties.find((item) => item.code === previous.specialty_code)?.label || ''}` : option.label }));
  };
  return (
    <fieldset className="reception-his-nested-fieldset hospitalization-plan" data-testid="hospitalization-service-plan">
      <legend>Plan de séjour</legend>
      <p className="clinical-hint">La pédiatrie reste indisponible jusqu’à confirmation de son tarif.</p>
      <div className="hospitalization-plan__grid">
        <label>Spécialité *
          <select required value={form.specialty_code} onChange={(event) => {
            const specialty = availableSpecialties.find((item) => item.code === event.target.value);
            const code = form.accommodation_type === 'private_cabin' ? 'hospitalization_private_cabin' : 'hospitalization_standard';
            const selected = options.find((item) => item.code === code);
            setForm((previous) => ({ ...previous, specialty_code: event.target.value,
              service_name: specialty && selected ? `${selected.label} — ${specialty.label}` : '',
              catalog_code: selected?.code || '', charge_type: 'hospitalization', unit_price_gnf: selected?.price_gnf || 0 }));
          }}>
            <option value="">Choisir une spécialité…</option>
            {availableSpecialties.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
          </select>
        </label>
        <label>Durée *
          <input required type="number" min="1" max="120" value={form.duration_value} onChange={(event) => {
            const duration = Number(event.target.value || 1);
            setForm((previous) => ({ ...previous, duration_value: duration, quantity: previous.duration_unit === 'months' ? duration * 30 : duration }));
          }} />
        </label>
        <label>Unité *
          <select value={form.duration_unit} onChange={(event) => setForm((previous) => ({ ...previous, duration_unit: event.target.value, quantity: event.target.value === 'months' ? Number(previous.duration_value || 1) * 30 : Number(previous.duration_value || 1) }))}>
            <option value="days">Jour(s)</option><option value="months">Mois (30 jours)</option>
          </select>
        </label>
      </div>
      <div className="hospitalization-plan__choices" role="radiogroup" aria-label="Type d’hébergement">
        {options.map((option) => {
          const type = option.code === 'hospitalization_private_cabin' ? 'private_cabin' : 'standard_bed';
          return <label key={option.code} className={form.accommodation_type === type ? 'is-selected' : ''}>
            <input type="radio" name="hospitalization-accommodation" checked={form.accommodation_type === type} onChange={() => selectAccommodation(option)} />
            <span><strong>{type === 'private_cabin' ? 'Cabine privée' : 'Lit standard'}</strong><small>{formatGNF(option.price_gnf)} / jour</small></span>
          </label>;
        })}
      </div>
      <div className="hospitalization-plan__total" role="status">
        <span>{form.quantity || 1} jour(s) facturable(s)</span>
        <strong>{formatGNF(Number(form.unit_price_gnf || 0) * Number(form.quantity || 1))}</strong>
      </div>
    </fieldset>
  );
}
