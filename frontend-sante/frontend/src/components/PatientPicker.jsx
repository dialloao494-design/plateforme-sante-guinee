import { useState } from 'react';

function patientName(patient) {
  return [patient?.first_name, patient?.last_name].filter(Boolean).join(' ') || 'Patient sans nom';
}

export default function PatientPicker({ search, selected, onSelect, label = 'Rechercher un patient' }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    if (query.trim().length < 2) {
      setError('Saisissez au moins deux caractères.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await search(query.trim());
      setResults(response?.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Recherche indisponible.');
      setResults([]);
    } finally {
      setBusy(false);
    }
  };

  if (selected) {
    return (
      <div className="patient-identity-banner" role="status" aria-label="Patient sélectionné">
        <div>
          <strong>{patientName(selected)}</strong>
          <span>
            Dossier {selected.patient_number || 'non attribué'}
            {selected.date_of_birth ? ` · Né(e) le ${selected.date_of_birth}` : ''}
            {selected.phone ? ` · ${selected.phone}` : ''}
          </span>
        </div>
        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => onSelect(null)}>
          Changer de patient
        </button>
      </div>
    );
  }

  return (
    <div>
      <form className="patient-picker-form" role="search" onSubmit={submit}>
        <label htmlFor="patient-picker-query">{label}</label>
        <div className="clinical-actions">
          <input
            id="patient-picker-query"
            name="patient_search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Nom, téléphone ou N° dossier…"
            autoComplete="off"
          />
          <button type="submit" className="clinical-btn" disabled={busy}>
            {busy ? 'Recherche…' : 'Rechercher'}
          </button>
        </div>
      </form>
      {error && <p className="clinical-alert clinical-alert--error" role="alert">{error}</p>}
      {results.length > 0 && (
        <ul className="clinical-queue patient-picker-results" aria-label="Résultats patients">
          {results.map((patient) => (
            <li key={patient.id}>
              <button type="button" className="patient-picker-result" onClick={() => onSelect(patient)}>
                <strong>{patientName(patient)}</strong>
                <span>
                  Dossier {patient.patient_number || 'non attribué'}
                  {patient.date_of_birth ? ` · ${patient.date_of_birth}` : ''}
                  {patient.phone ? ` · ${patient.phone}` : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
