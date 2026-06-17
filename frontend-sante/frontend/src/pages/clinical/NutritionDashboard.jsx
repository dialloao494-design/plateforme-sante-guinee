import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const STATUS_LABELS = {
  normal: 'Normal',
  moderate_malnutrition: 'Malnutrition modérée',
  severe_malnutrition: 'Malnutrition sévère',
};

export default function NutritionDashboard() {
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    weight_kg: '',
    height_cm: '',
    muac_cm: '',
    age_months: '',
    notes: '',
  });

  const loadHistory = useCallback(async (patientId) => {
    try {
      const { data } = await clinicalApi.nutritionHistory(patientId);
      setHistory(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Historique nutrition indisponible');
    }
  }, []);

  useEffect(() => {
    if (selectedPatient?.id) {
      loadHistory(selectedPatient.id);
    }
  }, [selectedPatient, loadHistory]);

  const searchPatients = async () => {
    if (patientSearch.trim().length < 2) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Recherche impossible');
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient);
    setPatientMatches([]);
    setMessage('');
    setError('');
  };

  const submitAssessment = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;
    try {
      await clinicalApi.recordNutritionAssessment({
        patient_id: selectedPatient.id,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        muac_cm: form.muac_cm ? Number(form.muac_cm) : null,
        age_months: form.age_months ? Number(form.age_months) : null,
        notes: form.notes || null,
      });
      setMessage('Mesures enregistrées');
      setForm({ weight_kg: '', height_cm: '', muac_cm: '', age_months: '', notes: '' });
      loadHistory(selectedPatient.id);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Enregistrement impossible');
    }
  };

  const latest = history[0];
  const stats = [
    { label: 'Mesures enregistrées', value: history.length, variant: 'accent' },
    {
      label: 'Dernier poids (kg)',
      value: latest?.weight_kg ?? '—',
    },
    {
      label: 'Dernière taille (cm)',
      value: latest?.height_cm ?? '—',
    },
    {
      label: 'Statut MUAC',
      value: latest?.nutritional_status ? STATUS_LABELS[latest.nutritional_status] || latest.nutritional_status : '—',
      variant: latest?.nutritional_status?.includes('malnutrition') ? 'warning' : 'success',
    },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Nutrition</h1>
      <p className="clinical-lead">Suivi de la croissance : poids, taille, périmètre brachial (MUAC).</p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <DepartmentQueuePanel
        department="nutrition"
        title="File de visite — Nutrition"
        onSelectPatient={(item) => setSelectedPatient({ id: item.patient_id, first_name: item.patient_name?.split(' ')[0], last_name: item.patient_name?.split(' ').slice(1).join(' ') })}
      />

      <section className="clinical-card">
        <h2>Rechercher un patient</h2>
        <div className="clinical-inline-form">
          <input
            type="search"
            placeholder="Nom ou téléphone (min. 2 caractères)"
            value={patientSearch}
            onChange={(e) => setPatientSearch(e.target.value)}
          />
          <button type="button" className="clinical-btn secondary" onClick={searchPatients}>
            Rechercher
          </button>
        </div>
        {patientMatches.length > 0 && (
          <ul className="clinical-list">
            {patientMatches.map((p) => (
              <li key={p.id}>
                <button type="button" className="clinical-link-btn" onClick={() => selectPatient(p)}>
                  {p.first_name} {p.last_name} — {p.phone || 'sans téléphone'}
                </button>
              </li>
            ))}
          </ul>
        )}
        {selectedPatient && (
          <p className="clinical-selected-patient">
            Patient sélectionné : <strong>{selectedPatient.first_name} {selectedPatient.last_name}</strong>
          </p>
        )}
      </section>

      {selectedPatient && (
        <>
          <section className="clinical-card">
            <h2>Nouvelle mesure</h2>
            <form className="clinical-form-grid" onSubmit={submitAssessment}>
              <label>
                Poids (kg)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.weight_kg}
                  onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
                />
              </label>
              <label>
                Taille (cm)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.height_cm}
                  onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
                />
              </label>
              <label>
                MUAC (cm)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={form.muac_cm}
                  onChange={(e) => setForm({ ...form, muac_cm: e.target.value })}
                />
              </label>
              <label>
                Âge (mois)
                <input
                  type="number"
                  min="0"
                  value={form.age_months}
                  onChange={(e) => setForm({ ...form, age_months: e.target.value })}
                />
              </label>
              <label className="clinical-span-2">
                Notes
                <textarea
                  rows={2}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </label>
              <button type="submit" className="clinical-btn primary">
                Enregistrer
              </button>
            </form>
          </section>

          <section className="clinical-card">
            <h2>Historique nutrition</h2>
            {history.length === 0 ? (
              <p>Aucune mesure enregistrée.</p>
            ) : (
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Poids</th>
                    <th>Taille</th>
                    <th>MUAC</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.id}>
                      <td>{new Date(row.recorded_at).toLocaleDateString('fr-FR')}</td>
                      <td>{row.weight_kg ?? '—'}</td>
                      <td>{row.height_cm ?? '—'}</td>
                      <td>{row.muac_cm ?? '—'}</td>
                      <td>{STATUS_LABELS[row.nutritional_status] || row.nutritional_status || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}
