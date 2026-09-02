import { formatGNF } from '../../../../utils/appointmentPresentation.js';

const PEDIATRIC_SPECIALTIES = new Set(['pediatrics', 'pediatric_surgery']);
const ACCOMMODATIONS = {
  hospitalization_shared_room_180: { type: 'shared_room_bed', title: 'Lit salle commune', guidance: 'Tarif journalier : 180 000 GNF' },
  hospitalization_standard: { type: 'standard_bed', title: 'Lit salle commune', guidance: 'Tarif journalier : 200 000 GNF' },
  hospitalization_private_cabin: { type: 'private_cabin', title: 'Cabine VIP', guidance: 'Chambre individuelle' },
  hospitalization_pediatric_cradle: { type: 'pediatric_cradle', title: 'Berceau nouveau-né', guidance: 'Pour un nouveau-né' },
  hospitalization_pediatric_bed: { type: 'pediatric_bed', title: 'Lit pédiatrique standard', guidance: 'Pour un enfant après la période néonatale' },
};

export default function HospitalizationPlan({ form, specialties, options, setForm }) {
  const pediatric = PEDIATRIC_SPECIALTIES.has(form.specialty_code);
  const availableOptions = form.specialty_code
    ? options.filter((option) => pediatric
      ? option.code.startsWith('hospitalization_pediatric_')
      : ['hospitalization_shared_room_180', 'hospitalization_standard', 'hospitalization_private_cabin'].includes(option.code))
    : [];

  const selectAccommodation = (option) => {
    const accommodation = ACCOMMODATIONS[option.code];
    const specialty = specialties.find((item) => item.code === form.specialty_code);
    if (!accommodation || !specialty) return;
    setForm((previous) => ({
      ...previous,
      accommodation_type: accommodation.type,
      catalog_code: option.code,
      charge_type: 'hospitalization',
      unit_price_gnf: option.price_gnf,
      service_name: `${option.label} — ${specialty.label}`,
    }));
  };

  return (
    <fieldset className="reception-his-nested-fieldset hospitalization-plan" data-testid="hospitalization-service-plan">
      <legend>Plan de séjour</legend>
      <p className="clinical-hint">Choisissez le lit et le nombre de jours. Le total est calculé automatiquement.</p>
      <div className="hospitalization-plan__grid">
        <label>Spécialité *
          <select required value={form.specialty_code} onChange={(event) => setForm((previous) => ({
            ...previous,
            specialty_code: event.target.value,
            accommodation_type: '',
            catalog_code: '',
            service_name: '',
            unit_price_gnf: 0,
            charge_type: 'hospitalization',
          }))}>
            <option value="">Choisir une spécialité…</option>
            {specialties.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
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
      {form.specialty_code ? (
        <div className="hospitalization-plan__choices" role="radiogroup" aria-label="Type de lit">
          {availableOptions.map((option) => {
            const accommodation = ACCOMMODATIONS[option.code];
            return <label key={option.code} className={form.accommodation_type === accommodation.type ? 'is-selected' : ''}>
              <input required type="radio" name="hospitalization-accommodation" checked={form.accommodation_type === accommodation.type} onChange={() => selectAccommodation(option)} />
              <span>
                <strong>{accommodation.title}</strong>
                <small>{accommodation.guidance}</small>
                <small><strong>{formatGNF(option.price_gnf)} / jour</strong></small>
              </span>
            </label>;
          })}
        </div>
      ) : <p className="clinical-hint">Choisissez d’abord la spécialité pour afficher les lits disponibles.</p>}
      <div className="hospitalization-plan__total" role="status">
        <span>{form.quantity || 1} jour(s) × {form.accommodation_type ? formatGNF(form.unit_price_gnf || 0) : 'tarif à choisir'}</span>
        <strong>{form.accommodation_type
          ? formatGNF(Number(form.unit_price_gnf || 0) * Number(form.quantity || 1))
          : 'Choisissez un type de lit'}</strong>
      </div>
    </fieldset>
  );
}
