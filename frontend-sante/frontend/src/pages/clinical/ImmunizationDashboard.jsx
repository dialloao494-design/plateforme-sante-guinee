import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

export default function ImmunizationDashboard() {
  const [schedule, setSchedule] = useState([]);
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState({ due: [], missed: [], upcoming: [] });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [tab, setTab] = useState('missed');
  const [form, setForm] = useState({
    vaccine_code: '',
    vaccine_name: '',
    dose_label: '',
    administered_at: new Date().toISOString().slice(0, 10),
    batch_number: '',
    notes: '',
  });

  useEffect(() => {
    clinicalApi
      .immunizationSchedule()
      .then(({ data }) => setSchedule(data || []))
      .catch(() => {});
  }, []);

  const loadPatientData = useCallback(async (patientId) => {
    try {
      const [histRes, statusRes] = await Promise.all([
        clinicalApi.immunizationHistory(patientId),
        clinicalApi.immunizationStatus(patientId),
      ]);
      setHistory(histRes.data || []);
      setStatus(statusRes.data || { due: [], missed: [], upcoming: [] });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Données PEV indisponibles');
    }
  }, []);

  useEffect(() => {
    if (selectedPatient?.id) {
      loadPatientData(selectedPatient.id);
    }
  }, [selectedPatient, loadPatientData]);

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

  const fillFromSchedule = (item) => {
    setForm((prev) => ({
      ...prev,
      vaccine_code: item.vaccine_code,
      vaccine_name: item.vaccine_name,
      dose_label: item.dose_label,
    }));
  };

  const submitVaccination = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;
    try {
      await clinicalApi.recordImmunization({
        patient_id: selectedPatient.id,
        vaccine_code: form.vaccine_code,
        vaccine_name: form.vaccine_name,
        dose_label: form.dose_label || null,
        administered_at: form.administered_at,
        batch_number: form.batch_number || null,
        notes: form.notes || null,
      });
      setMessage('Vaccination enregistrée');
      setForm({
        vaccine_code: '',
        vaccine_name: '',
        dose_label: '',
        administered_at: new Date().toISOString().slice(0, 10),
        batch_number: '',
        notes: '',
      });
      loadPatientData(selectedPatient.id);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Enregistrement impossible');
    }
  };

  const activeList = status[tab] || [];
  const stats = [
    { label: 'Vaccins manqués', value: status.missed?.length || 0, variant: 'warning' },
    { label: 'À administrer', value: status.due?.length || 0, variant: 'accent' },
    { label: 'À venir', value: status.upcoming?.length || 0 },
    { label: 'Historique', value: history.length, variant: 'success' },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — PEV / Vaccination</h1>
      <p className="clinical-lead">Calendrier vaccinal, historique, rappels et alertes vaccins manqués.</p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

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
            <div className="clinical-tabs">
              {['missed', 'due', 'upcoming'].map((key) => (
                <button
                  key={key}
                  type="button"
                  className={tab === key ? 'clinical-tab active' : 'clinical-tab'}
                  onClick={() => setTab(key)}
                >
                  {key === 'missed' ? 'Manqués' : key === 'due' ? 'Dus' : 'À venir'} ({status[key]?.length || 0})
                </button>
              ))}
            </div>
            {activeList.length === 0 ? (
              <p>Aucun vaccin dans cette catégorie.</p>
            ) : (
              <ul className="clinical-list">
                {activeList.map((v) => (
                  <li key={`${v.vaccine_code}-${v.dose_label}`}>
                    <strong>{v.vaccine_name}</strong> — {v.dose_label} (échéance {v.due_date})
                    <button
                      type="button"
                      className="clinical-btn secondary clinical-btn-sm"
                      onClick={() => fillFromSchedule(v)}
                    >
                      Renseigner
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="clinical-card">
            <h2>Enregistrer une vaccination</h2>
            <form className="clinical-form-grid" onSubmit={submitVaccination}>
              <label>
                Code vaccin
                <input
                  required
                  value={form.vaccine_code}
                  onChange={(e) => setForm({ ...form, vaccine_code: e.target.value })}
                />
              </label>
              <label>
                Nom vaccin
                <input
                  required
                  value={form.vaccine_name}
                  onChange={(e) => setForm({ ...form, vaccine_name: e.target.value })}
                />
              </label>
              <label>
                Dose
                <input value={form.dose_label} onChange={(e) => setForm({ ...form, dose_label: e.target.value })} />
              </label>
              <label>
                Date
                <input
                  type="date"
                  required
                  value={form.administered_at}
                  onChange={(e) => setForm({ ...form, administered_at: e.target.value })}
                />
              </label>
              <label>
                N° lot
                <input value={form.batch_number} onChange={(e) => setForm({ ...form, batch_number: e.target.value })} />
              </label>
              <button type="submit" className="clinical-btn primary">
                Enregistrer
              </button>
            </form>
          </section>

          <section className="clinical-card">
            <h2>Historique vaccinal</h2>
            {history.length === 0 ? (
              <p>Aucune vaccination enregistrée.</p>
            ) : (
              <table className="clinical-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Vaccin</th>
                    <th>Dose</th>
                    <th>Lot</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.id}>
                      <td>{row.administered_at}</td>
                      <td>{row.vaccine_name}</td>
                      <td>{row.dose_label || '—'}</td>
                      <td>{row.batch_number || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}

      <section className="clinical-card">
        <h2>Calendrier PEV national ({schedule.length} entrées)</h2>
        <p className="clinical-stat-hint">Référence pour la planification vaccinale.</p>
      </section>
    </div>
  );
}
