export default function AdmissionPlacement({ form, updateAdmission }) {
  return (
    <fieldset className="reception-admission-placement" data-testid="admission-placement">
      <legend>Affectation d’hébergement</legend>
      <p>Choisissez un seul emplacement pour éviter une double affectation.</p>
      <div className="reception-admission-placement__choice" role="radiogroup" aria-label="Type d’hébergement">
        <label className={form.accommodation_type === 'standard_bed' ? 'is-selected' : ''}>
          <input type="radio" name="admission-accommodation" checked={form.accommodation_type === 'standard_bed'} onChange={() => updateAdmission({ accommodation_type: 'standard_bed', cabin_number: '' })} />
          <span><strong>Lit standard</strong><small>Lits numérotés de 1 à 12</small></span>
        </label>
        <label className={form.accommodation_type === 'private_cabin' ? 'is-selected' : ''}>
          <input type="radio" name="admission-accommodation" checked={form.accommodation_type === 'private_cabin'} onChange={() => updateAdmission({ accommodation_type: 'private_cabin', bed_number: '' })} />
          <span><strong>Cabine privée</strong><small>Cabines 1 et 2</small></span>
        </label>
      </div>
      {form.accommodation_type === 'private_cabin' ? (
        <label>Numéro de cabine *
          <select required value={form.cabin_number} onChange={(event) => updateAdmission({ cabin_number: event.target.value })}>
            <option value="">Choisir une cabine…</option><option value="1">Cabine n° 1</option><option value="2">Cabine n° 2</option>
          </select>
        </label>
      ) : (
        <label>Numéro de lit *
          <select required value={form.bed_number} onChange={(event) => updateAdmission({ bed_number: event.target.value })}>
            <option value="">Choisir un lit…</option>{Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={String(index + 1)}>Lit n° {index + 1}</option>)}
          </select>
        </label>
      )}
    </fieldset>
  );
}
