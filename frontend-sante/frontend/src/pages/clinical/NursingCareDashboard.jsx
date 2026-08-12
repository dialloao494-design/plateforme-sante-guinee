import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const PROCEDURE_TYPES = [
  { value: 'injection', label: 'Injection' },
  { value: 'perfusion', label: 'Perfusion' },
  { value: 'dressing', label: 'Pansement' },
  { value: 'suture', label: 'Suture' },
  { value: 'other', label: 'Autre' },
];

const TYPE_LABELS = Object.fromEntries(PROCEDURE_TYPES.map((p) => [p.value, p.label]));

export default function NursingCareDashboard() {
  const [view, setView] = useState('record');
  const [dashboard, setDashboard] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [registerRows, setRegisterRows] = useState([]);
  const [reportMonth, setReportMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const [procedures, setProcedures] = useState([]);
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    procedure_type: 'injection',
    procedure_date: new Date().toISOString().slice(0, 10),
    procedure_time: new Date().toTimeString().slice(0, 5),
    nurse_name: '',
    notes: '',
  });

  const loadMonthlyData = useCallback(async (year, month) => {
    try {
      const [reportRes, registerRes] = await Promise.all([
        clinicalApi.nursingMonthlyReport(year, month),
        clinicalApi.nursingRegister(year, month),
      ]);
      setMonthlyReport(reportRes.data);
      setRegisterRows(registerRes.data || []);
    } catch (err) {
      setError(formatApiError(err, 'Registre mensuel indisponible'));
    }
  }, []);

  const load = useCallback(async () => {
    try {
      const now = new Date();
      const [dashRes, procRes] = await Promise.all([
        clinicalApi.nursingDashboard(),
        clinicalApi.nursingProcedures(),
      ]);
      setDashboard(dashRes.data);
      setProcedures(procRes.data || []);
      setError('');
      await loadMonthlyData(now.getFullYear(), now.getMonth() + 1);
    } catch (err) {
      setError(formatApiError(err, 'Module Soins indisponible'));
    }
  }, [loadMonthlyData]);

  useEffect(() => {
    load();
  }, [load]);

  const searchPatients = async () => {
    if (patientSearch.trim().length < 2) return;
    try {
      const { data } = await clinicalApi.searchPatients(patientSearch.trim());
      setPatientMatches(data || []);
    } catch (err) {
      setError(formatApiError(err, 'Recherche impossible'));
    }
  };

  const selectPatient = (patient) => {
    setSelectedPatient(patient);
    setPatientMatches([]);
    setMessage('');
    setError('');
  };

  const submitProcedure = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;
    try {
      await clinicalApi.recordNursingProcedure({
        patient_id: selectedPatient.id,
        procedure_type: form.procedure_type,
        procedure_date: form.procedure_date,
        procedure_time: form.procedure_time || null,
        nurse_name: form.nurse_name || null,
        notes: form.notes || null,
      });
      setMessage('Procédure enregistrée');
      setForm({ ...form, notes: '' });
      load();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    }
  };

  const stats = dashboard
    ? [
        { label: 'Procédures aujourd\'hui', value: dashboard.daily_procedures, variant: 'accent' },
        { label: 'Procédures ce mois', value: dashboard.monthly_procedures },
        { label: 'Injections', value: dashboard.injections, variant: 'success' },
        { label: 'Perfusions', value: dashboard.perfusions },
        { label: 'Pansements', value: dashboard.dressings },
        { label: 'Sutures', value: dashboard.sutures },
      ]
    : [];

  return (
    <div className="clinical-page" data-testid="nursing-care-dashboard">
      <h1>Tableau de bord — Soins infirmiers</h1>
      <p className="clinical-lead">
        Enregistrement des soins : injections, perfusions, pansements, sutures — registre mensuel automatique.
      </p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <div className="clinical-tabs" role="tablist">
        <button type="button" data-testid="nursing-care-tab-record" className={`clinical-tab${view === 'record' ? ' active' : ''}`} onClick={() => setView('record')}>
          Enregistrement
        </button>
        <button type="button" className={`clinical-tab${view === 'register' ? ' active' : ''}`} onClick={() => setView('register')}>
          Registre mensuel
        </button>
        <button type="button" className={`clinical-tab${view === 'report' ? ' active' : ''}`} onClick={() => setView('report')}>
          Statistiques
        </button>
      </div>

      {view === 'record' && (
        <>
      <DepartmentQueuePanel
        department="nursing"
        title="File de visite — Soins"
        onSelectPatient={(item) =>
          setSelectedPatient({
            id: item.patient_id,
            first_name: item.patient_name?.split(' ')[0],
            last_name: item.patient_name?.split(' ').slice(1).join(' '),
          })
        }
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
        <section className="clinical-card">
          <h2>Enregistrer une procédure</h2>
          <form className="clinical-form-grid" onSubmit={submitProcedure}>
            <label>
              Type de soin
              <select
                value={form.procedure_type}
                onChange={(e) => setForm({ ...form, procedure_type: e.target.value })}
              >
                {PROCEDURE_TYPES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </label>
            <label>
              Date
              <input
                type="date"
                required
                value={form.procedure_date}
                onChange={(e) => setForm({ ...form, procedure_date: e.target.value })}
              />
            </label>
            <label>
              Heure
              <input
                type="time"
                value={form.procedure_time}
                onChange={(e) => setForm({ ...form, procedure_time: e.target.value })}
              />
            </label>
            <label>
              Infirmier(ère)
              <input
                value={form.nurse_name}
                onChange={(e) => setForm({ ...form, nurse_name: e.target.value })}
                placeholder="Nom du soignant"
              />
            </label>
            <label className="clinical-form-full">
              Notes
              <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
            </label>
            <button type="submit" className="clinical-btn primary">Enregistrer</button>
          </form>
        </section>
      )}

      <section className="clinical-card">
        <h2>Procédures récentes</h2>
        {procedures.length === 0 ? (
          <p>Aucune procédure enregistrée.</p>
        ) : (
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Patient</th>
                <th>Type</th>
                <th>Infirmier(ère)</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {procedures.slice(0, 50).map((row) => (
                <tr key={row.id}>
                  <td>{row.procedure_date}</td>
                  <td>{row.patient_name || row.patient_id}</td>
                  <td>{TYPE_LABELS[row.procedure_type] || row.procedure_type}</td>
                  <td>{row.nurse_name || '—'}</td>
                  <td>{row.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
        </>
      )}

      {view === 'register' && (
        <section className="clinical-card">
          <h2>Registre mensuel — pointage soins</h2>
          <div className="clinical-inline-form">
            <label>
              Mois
              <input
                type="month"
                value={`${reportMonth.year}-${String(reportMonth.month).padStart(2, '0')}`}
                onChange={(e) => {
                  const [y, m] = e.target.value.split('-').map(Number);
                  setReportMonth({ year: y, month: m });
                  loadMonthlyData(y, m);
                }}
              />
            </label>
          </div>
          {registerRows.length === 0 ? (
            <p>Aucune procédure pour cette période.</p>
          ) : (
            <table className="clinical-table">
              <thead>
                <tr>
                  <th>N°</th>
                  <th>Date</th>
                  <th>Heure</th>
                  <th>Patient</th>
                  <th>Type</th>
                  <th>Infirmier(ère)</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {registerRows.map((row) => (
                  <tr key={row.record?.id || row.line_number}>
                    <td>{row.line_number}</td>
                    <td>{row.record?.procedure_date}</td>
                    <td>{row.record?.procedure_time || '—'}</td>
                    <td>{row.patient?.first_name} {row.patient?.last_name}</td>
                    <td>{TYPE_LABELS[row.record?.procedure_type] || row.record?.procedure_type}</td>
                    <td>{row.record?.nurse_name || '—'}</td>
                    <td>{row.record?.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {view === 'report' && monthlyReport && (
        <section className="clinical-card">
          <h2>Rapport mensuel — {monthlyReport.month}/{monthlyReport.year}</h2>
          <p>Total procédures : <strong>{monthlyReport.total_procedures}</strong></p>
          <ClinicalStatGrid
            stats={Object.entries(monthlyReport.by_type || {}).map(([key, value]) => ({
              label: TYPE_LABELS[key] || key,
              value,
            }))}
          />
          {monthlyReport.daily_tally?.length > 0 && (
            <table className="clinical-table">
              <thead>
                <tr>
                  <th>Jour</th>
                  <th>Injections</th>
                  <th>Perfusions</th>
                  <th>Pansements</th>
                  <th>Sutures</th>
                  <th>Autre</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {monthlyReport.daily_tally.map((row) => (
                  <tr key={row.day}>
                    <td>{row.day}</td>
                    <td>{row.injection || 0}</td>
                    <td>{row.perfusion || 0}</td>
                    <td>{row.dressing || 0}</td>
                    <td>{row.suture || 0}</td>
                    <td>{row.other || 0}</td>
                    <td><strong>{row.total}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
