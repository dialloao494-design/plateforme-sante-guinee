export default function LabSampleCollection({ form, loading, onChange, onSave, onToggleType, sampleOther, sampleTypes, savedSampleInfo, setSampleOther, typeOptions }) {
  return (
    <section className="lab-his-workflow-card lab-his-workflow-card--sample" aria-labelledby="lab-sample-title">
      <h3 id="lab-sample-title">Prélèvement</h3>
      <div className="reception-his-form-row reception-his-form-row--4">
        <label>Date de prélèvement<input type="date" name="collection_date" autoComplete="off" value={form.collection_date} onChange={(event) => onChange('collection_date', event.target.value)} /></label>
        <label>Heure de prélèvement<input type="time" name="collection_time" autoComplete="off" value={form.collection_time} onChange={(event) => onChange('collection_time', event.target.value)} /></label>
        <label>Agent de prélèvement<input name="collector" autoComplete="name" value={form.collector} onChange={(event) => onChange('collector', event.target.value)} /></label>
      </div>
      <fieldset className="lab-his-sample-types">
        <legend>Types d&apos;échantillon</legend>
        <div className="lab-his-sample-checkboxes" role="group" aria-label="Types d'échantillon">
          {typeOptions.map((option) => (
            <label key={option.code} className="lab-his-sample-check">
              <input type="checkbox" checked={sampleTypes.includes(option.code)} onChange={() => onToggleType(option.code)} />
              {option.label}
            </label>
          ))}
        </div>
        {sampleTypes.includes('other') && (
          <label className="lab-his-sample-other">Autre échantillon<input name="sample_other" autoComplete="off" value={sampleOther} onChange={(event) => setSampleOther(event.target.value)} placeholder="Ex. liquide pleural…" /></label>
        )}
      </fieldset>
      {savedSampleInfo && (
        <div className="lab-his-saved-sample" aria-live="polite">
          <strong>Prélèvement enregistré</strong>
          <p>{(savedSampleInfo.sample_types || []).join(', ') || '—'}{savedSampleInfo.sample_other ? ` · ${savedSampleInfo.sample_other}` : ''}</p>
          <p className="clinical-hint">{savedSampleInfo.collection_date || '—'} {savedSampleInfo.collection_time || ''}{savedSampleInfo.collector ? ` · ${savedSampleInfo.collector}` : ''}</p>
        </div>
      )}
      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={onSave} disabled={loading}>
        {loading ? 'Enregistrement…' : 'Enregistrer le prélèvement'}
      </button>
    </section>
  );
}
