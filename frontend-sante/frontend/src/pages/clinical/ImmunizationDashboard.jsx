import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

export default function ImmunizationDashboard() {
  const [schedule, setSchedule] = useState([]);
  const [clinicStats, setClinicStats] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
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
    dose_number: '',
    administered_at: new Date().toISOString().slice(0, 10),
    next_appointment_date: '',
    vaccinator_name: '',
    batch_number: '',
    notes: '',
  });

  useEffect(() => {
    const now = new Date();
    Promise.all([
      clinicalApi.immunizationSchedule(),
      clinicalApi.immunizationDashboard(),
      clinicalApi.immunizationMonthlyReport(now.getFullYear(), now.getMonth() + 1),
    ])
      .then(([schedRes, dashRes, reportRes]) => {
        setSchedule(schedRes.data || []);
        setClinicStats(dashRes.data);
        setMonthlyReport(reportRes.data);
      })
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
        dose_number: form.dose_number ? Number(form.dose_number) : null,
        administered_at: form.administered_at,
        next_appointment_date: form.next_appointment_date || null,
        vaccinator_name: form.vaccinator_name || null,
        batch_number: form.batch_number || null,
        notes: form.notes || null,
      });
      setMessage('Vaccination enregistrée');
      setForm({
        vaccine_code: '',
        vaccine_name: '',
        dose_label: '',
        dose_number: '',
        administered_at: new Date().toISOString().slice(0, 10),
        next_appointment_date: '',
        vaccinator_name: '',
        batch_number: '',
        notes: '',
      });
      loadPatientData(selectedPatient.id);
      clinicalApi.immunizationDashboard().then(({ data }) => setClinicStats(data)).catch(() => {});
    } catch (err) {
      setError(err?.response?.data?.detail || 'Enregistrement impossible');
    }
  };

  const activeList = status[tab] || [];
  const stats = clinicStats
    ? [
        { label: 'Vaccinations aujourd\'hui', value: clinicStats.daily_vaccinations, variant: 'accent' },
        { label: 'Vaccinations ce mois', value: clinicStats.monthly_vaccinations },
        { label: 'Vaccins manqués (patient)', value: status.missed?.length || 0, variant: 'warning' },
        { label: 'Historique patient', value: history.length, variant: 'success' },
      ]
    : [
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

      <DepartmentQueuePanel
        department="pev"
        title="File de visite — PEV / Vaccination"
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
                N° dose
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={form.dose_number}
                  onChange={(e) => setForm({ ...form, dose_number: e.target.value })}
                />
              </label>
              <label>
                Date vaccination
                <input
                  type="date"
                  required
                  value={form.administered_at}
                  onChange={(e) => setForm({ ...form, administered_at: e.target.value })}
                />
              </label>
              <label>
                Prochain RDV
                <input
                  type="date"
                  value={form.next_appointment_date}
                  onChange={(e) => setForm({ ...form, next_appointment_date: e.target.value })}
                />
              </label>
              <label>
                Vaccinateur
                <input
                  value={form.vaccinator_name}
                  onChange={(e) => setForm({ ...form, vaccinator_name: e.target.value })}
                  placeholder="Nom du vaccinateur"
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
                    <th>Prochain RDV</th>
                    <th>Vaccinateur</th>
                    <th>Lot</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.id}>
                      <td>{row.administered_at}</td>
                      <td>{row.vaccine_name}</td>
                      <td>{row.dose_label || row.dose_number || '—'}</td>
                      <td>{row.next_appointment_date || '—'}</td>
                      <td>{row.vaccinator_name || '—'}</td>
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

      {clinicStats && (
        <section className="clinical-card">
          <h2>Répartition ce mois</h2>
          <ClinicalStatGrid
            stats={[
              ...Object.entries(clinicStats.by_vaccine_type || {}).slice(0, 4).map(([label, value]) => ({
                label,
                value,
              })),
              ...Object.entries(clinicStats.by_age_group || {}).map(([label, value]) => ({
                label: `Âge: ${label}`,
                value,
              })),
            ]}
          />
        </section>
      )}

      {monthlyReport && (
        <section className="clinical-card">
          <h2>Rapport mensuel PEV — {monthlyReport.month}/{monthlyReport.year}</h2>
          <p>Total vaccinations : <strong>{monthlyReport.total_vaccinations}</strong></p>
        </section>
      )}
    </div>
  );
}
