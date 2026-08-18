export default function VaccinationEntryForm({ form, injectionSites, strategies, onChange, onSubmit }) {
  const field = (name) => (event) => onChange(name, event.target.value);

  return (
    <section className="clinical-card" aria-labelledby="pev-entry-title">
      <h2 id="pev-entry-title">Fiche vaccination</h2>
      <p className="clinical-hint">Renseignez les informations du carnet et du lot avant l&apos;enregistrement.</p>
      <form className="clinical-form-grid pev-form-grid" onSubmit={onSubmit}>
        <label>
          Code vaccin *
          <input required name="vaccine_code" autoComplete="off" value={form.vaccine_code} onChange={field('vaccine_code')} />
        </label>
        <label>
          Antigène / vaccin *
          <input required name="vaccine_name" autoComplete="off" value={form.vaccine_name} onChange={field('vaccine_name')} />
        </label>
        <label>
          Dose
          <input name="dose_label" autoComplete="off" value={form.dose_label} onChange={field('dose_label')} />
        </label>
        <label>
          N° dose
          <input type="number" inputMode="numeric" name="dose_number" autoComplete="off" min="1" max="10" value={form.dose_number} onChange={field('dose_number')} />
        </label>
        <label>
          Date vaccination *
          <input type="date" required name="administered_at" autoComplete="off" value={form.administered_at} onChange={field('administered_at')} />
        </label>
        <label>
          N° lot
          <input name="batch_number" autoComplete="off" value={form.batch_number} onChange={field('batch_number')} />
        </label>
        <label>
          Date péremption vaccin
          <input type="date" name="vaccine_expiry_date" autoComplete="off" value={form.vaccine_expiry_date} onChange={field('vaccine_expiry_date')} />
        </label>
        <label>
          Site d&apos;injection
          <select name="injection_site" autoComplete="off" value={form.injection_site} onChange={field('injection_site')}>
            {injectionSites.map((site) => <option key={site.code} value={site.code}>{site.label}</option>)}
          </select>
        </label>
        <label>
          Stratégie
          <select name="vaccination_strategy" autoComplete="off" value={form.vaccination_strategy} onChange={field('vaccination_strategy')}>
            {strategies.map((strategy) => <option key={strategy.code} value={strategy.code}>{strategy.label}</option>)}
          </select>
        </label>
        <label>
          Vaccinateur
          <input name="vaccinator_name" autoComplete="name" value={form.vaccinator_name} onChange={field('vaccinator_name')} />
        </label>
        <label>
          Prochain RDV
          <input type="date" name="next_appointment_date" autoComplete="off" value={form.next_appointment_date} onChange={field('next_appointment_date')} />
        </label>
        <label className="pev-form-wide">
          Observations
          <textarea name="notes" rows="2" value={form.notes} onChange={field('notes')} />
        </label>
        <label className="pev-form-wide">
          EIAS / réactions (AEFI)
          <textarea name="aefi_notes" rows="2" value={form.aefi_notes} onChange={field('aefi_notes')} />
        </label>
        <button type="submit" className="clinical-btn primary">Enregistrer la vaccination</button>
      </form>
    </section>
  );
}
