import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import PatientSafetyStrip from '../../components/clinical/PatientSafetyStrip.jsx';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { useClinicalPatientRoute } from '../../hooks/useClinicalPatientRoute.js';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';
import './pev.css';

const INJECTION_SITE_FALLBACK = {
  deltoide_d: 'Deltoïde droit',
  deltoide_g: 'Deltoïde gauche',
  cuisse_d: 'Cuisse droite',
  cuisse_g: 'Cuisse gauche',
  fesse: 'Fesse',
  oral: 'Voie orale',
  autre: 'Autre',
};

const STRATEGY_FALLBACK = {
  routine: 'Routine',
  campagne: 'Campagne',
  riposte: 'Riposte / Urgence',
};

const GENDER_LABELS = { M: 'M', F: 'F', male: 'M', female: 'F', other: '—' };

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('fr-FR');
}

function RegisterTable({ rows, title }) {
  if (!rows?.length) {
    return (
      <section className="clinical-card">
        <h2>{title}</h2>
        <p>Aucune vaccination enregistrée pour cette période.</p>
      </section>
    );
  }
  return (
    <section className="clinical-card pev-register-card">
      <h2>{title}</h2>
      <div className="pev-register-scroll">
        <table className="clinical-table pev-register-table">
          <thead>
            <tr>
              <th>N°</th>
              <th>Date</th>
              <th>Nom enfant</th>
              <th>Sexe</th>
              <th>Date naiss.</th>
              <th>Âge</th>
              <th>Mère / tuteur</th>
              <th>Quartier</th>
              <th>Vaccin</th>
              <th>Dose</th>
              <th>Lot</th>
              <th>Péremption</th>
              <th>Site</th>
              <th>Stratégie</th>
              <th>Vaccinateur</th>
              <th>Proch. RDV</th>
              <th>Observations</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const rec = row.record;
              const pat = row.patient;
              const age =
                rec.age_at_vaccination_months != null
                  ? `${rec.age_at_vaccination_months} mois`
                  : pat.age_display || '—';
              return (
                <tr key={rec.id}>
                  <td>{row.line_number}</td>
                  <td>{formatDate(rec.administered_at)}</td>
                  <td>
                    {pat.first_name} {pat.last_name}
                  </td>
                  <td>{GENDER_LABELS[pat.gender] || pat.gender || '—'}</td>
                  <td>{formatDate(pat.date_of_birth)}</td>
                  <td>{age}</td>
                  <td>{pat.mother_or_guardian || '—'}</td>
                  <td>{pat.address || '—'}</td>
                  <td>{rec.vaccine_name}</td>
                  <td>{rec.dose_label || rec.dose_number || '—'}</td>
                  <td>{rec.batch_number || '—'}</td>
                  <td>{formatDate(rec.vaccine_expiry_date)}</td>
                  <td>{INJECTION_SITE_FALLBACK[rec.injection_site] || rec.injection_site || '—'}</td>
                  <td>{STRATEGY_FALLBACK[rec.vaccination_strategy] || rec.vaccination_strategy || 'Routine'}</td>
                  <td>{rec.vaccinator_name || '—'}</td>
                  <td>{formatDate(rec.next_appointment_date)}</td>
                  <td>{rec.notes || rec.aefi_notes || '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function ImmunizationDashboard() {
  const { user } = useAuth();
  const { patientId: routePatientId, setPatientId: setRoutePatientId } = useClinicalPatientRoute();
  const closingPatientIdRef = useRef('');
  const [view, setView] = useState('record');
  const [schedule, setSchedule] = useState([]);
  const [fieldOptions, setFieldOptions] = useState({ injection_sites: [], strategies: [] });
  const [clinicStats, setClinicStats] = useState(null);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [registerRows, setRegisterRows] = useState([]);
  const [reportMonth, setReportMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const [patientSearch, setPatientSearch] = useState('');
  const [patientMatches, setPatientMatches] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientJourney, setPatientJourney] = useState(null);
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
    vaccinator_name: user?.email?.split('@')[0] || '',
    batch_number: '',
    vaccine_expiry_date: '',
    injection_site: 'deltoide_d',
    vaccination_strategy: 'routine',
    notes: '',
    aefi_notes: '',
  });

  const loadMonthlyData = useCallback(async (year, month) => {
    try {
      const [reportRes, registerRes] = await Promise.all([
        clinicalApi.immunizationMonthlyReport(year, month),
        clinicalApi.immunizationRegister(year, month),
      ]);
      setMonthlyReport(reportRes.data);
      setRegisterRows(registerRes.data || []);
    } catch (err) {
      setError(formatApiError(err, 'Rapport mensuel indisponible'));
    }
  }, []);

  useEffect(() => {
    const now = new Date();
    Promise.all([
      clinicalApi.immunizationSchedule(),
      clinicalApi.immunizationDashboard(),
      clinicalApi.immunizationFieldOptions(),
      clinicalApi.immunizationMonthlyReport(now.getFullYear(), now.getMonth() + 1),
      clinicalApi.immunizationRegister(now.getFullYear(), now.getMonth() + 1),
    ])
      .then(([schedRes, dashRes, optsRes, reportRes, registerRes]) => {
        setSchedule(schedRes.data || []);
        setClinicStats(dashRes.data);
        setFieldOptions(optsRes.data || { injection_sites: [], strategies: [] });
        setMonthlyReport(reportRes.data);
        setRegisterRows(registerRes.data || []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (view === 'register') {
      loadMonthlyData(reportMonth.year, reportMonth.month);
    }
  }, [view, reportMonth, loadMonthlyData]);

  const loadPatientData = useCallback(async (patientId) => {
    try {
      const [histRes, statusRes, journeyRes] = await Promise.all([
        clinicalApi.immunizationHistory(patientId),
        clinicalApi.immunizationStatus(patientId),
        clinicalApi.patientJourney(patientId),
      ]);
      setHistory(histRes.data || []);
      setStatus(statusRes.data || { due: [], missed: [], upcoming: [] });
      setPatientJourney(journeyRes.data || null);
    } catch (err) {
      setError(formatApiError(err, 'Données PEV indisponibles'));
    }
  }, []);

  useEffect(() => {
    if (!routePatientId) return;
    if (closingPatientIdRef.current === routePatientId || String(selectedPatient?.id || '') === routePatientId) return;
    clinicalApi.patientTimeline(routePatientId)
      .then(({ data }) => {
        setSelectedPatient(data?.patient || null);
        return loadPatientData(routePatientId);
      })
      .catch((err) => setError(formatApiError(err, 'Patient indisponible')));
  }, [routePatientId, selectedPatient?.id, loadPatientData]);

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
    closingPatientIdRef.current = '';
    setSelectedPatient(patient);
    setRoutePatientId(patient.id);
    setPatientMatches([]);
    setMessage('');
    setError('');
    loadPatientData(patient.id);
  };

  const closePatient = () => {
    closingPatientIdRef.current = String(selectedPatient?.id || routePatientId || '');
    setSelectedPatient(null);
    setHistory([]);
    setPatientJourney(null);
    setStatus({ due: [], missed: [], upcoming: [] });
    setRoutePatientId('');
  };

  const fillFromSchedule = (item) => {
    setForm((prev) => ({
      ...prev,
      vaccine_code: item.vaccine_code,
      vaccine_name: item.vaccine_name,
      dose_label: item.dose_label,
    }));
  };

  const refreshClinicStats = () => {
    clinicalApi.immunizationDashboard().then(({ data }) => setClinicStats(data)).catch(() => {});
    const now = new Date();
    loadMonthlyData(now.getFullYear(), now.getMonth() + 1);
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
        vaccine_expiry_date: form.vaccine_expiry_date || null,
        injection_site: form.injection_site || null,
        vaccination_strategy: form.vaccination_strategy || 'routine',
        notes: form.notes || null,
        aefi_notes: form.aefi_notes || null,
      });
      setMessage('Vaccination enregistrée dans le registre PEV');
      setForm((prev) => ({
        ...prev,
        vaccine_code: '',
        vaccine_name: '',
        dose_label: '',
        dose_number: '',
        batch_number: '',
        vaccine_expiry_date: '',
        notes: '',
        aefi_notes: '',
      }));
      loadPatientData(selectedPatient.id);
      refreshClinicStats();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    }
  };

  const activeList = status[tab] || [];
  const injectionSites = fieldOptions.injection_sites?.length
    ? fieldOptions.injection_sites
    : Object.entries(INJECTION_SITE_FALLBACK).map(([code, label]) => ({ code, label }));
  const strategies = fieldOptions.strategies?.length
    ? fieldOptions.strategies
    : Object.entries(STRATEGY_FALLBACK).map(([code, label]) => ({ code, label }));

  const stats = useMemo(() => {
    if (clinicStats) {
      return [
        { label: "Vaccinations aujourd'hui", value: clinicStats.daily_vaccinations, variant: 'accent' },
        { label: 'Vaccinations ce mois', value: clinicStats.monthly_vaccinations },
        { label: 'Vaccins manqués (patient)', value: status.missed?.length || 0, variant: 'warning' },
        { label: 'Lignes registre', value: registerRows.length, variant: 'success' },
      ];
    }
    return [
      { label: 'Vaccins manqués', value: status.missed?.length || 0, variant: 'warning' },
      { label: 'À administrer', value: status.due?.length || 0, variant: 'accent' },
      { label: 'À venir', value: status.upcoming?.length || 0 },
      { label: 'Historique', value: history.length, variant: 'success' },
    ];
  }, [clinicStats, status, registerRows.length, history.length]);

  const patientAgeDisplay = selectedPatient?.date_of_birth
    ? formatDate(selectedPatient.date_of_birth)
    : selectedPatient?.age != null
      ? `${selectedPatient.age} an(s)`
      : '—';

  return (
    <div className="clinical-page pev-page" data-testid="pev-dashboard">
      <h1>PEV / Vaccination — Registre Centre de Santé Koloma</h1>
      <p className="clinical-lead">
        Registre mensuel numérique aligné sur le carnet PEV : un seul dossier patient central, toutes les vaccinations
        ajoutées à l&apos;historique commun.
      </p>
      <ClinicalFeedback error={error} message={message} />

      <div className="clinical-tabs pev-view-tabs">
        {[
          ['record', 'Enregistrement'],
          ['register', 'Registre mensuel'],
          ['schedule', 'Calendrier PEV'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            data-testid={`pev-tab-${key}`}
            className={view === key ? 'clinical-tab active' : 'clinical-tab'}
            onClick={() => setView(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <ClinicalStatGrid stats={stats} />
      <PatientSafetyStrip patient={selectedPatient} onClose={closePatient} contextLabel="Patient actif au PEV" />

      {view === 'record' && (
        <>
          <DepartmentQueuePanel
            department="pev"
            title="File de visite — PEV / Vaccination"
            onSelectPatient={(item) =>
              selectPatient({
                id: item.patient_id,
                first_name: item.patient_name?.split(' ')[0],
                last_name: item.patient_name?.split(' ').slice(1).join(' '),
              })
            }
          />

          <section className="clinical-card">
            <h2>Rechercher un patient (dossier central unique)</h2>
            <div className="clinical-inline-form">
              <input
                type="search"
                name="patient_search"
                aria-label="Rechercher un patient par nom ou téléphone"
                autoComplete="off"
                placeholder="Nom ou téléphone · 2 caractères minimum…"
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
              <div className="pev-patient-banner">
                <p className="clinical-selected-patient">
                  Patient : <strong>{selectedPatient.first_name} {selectedPatient.last_name}</strong>
                  {' · '}
                  ID #{selectedPatient.id}
                </p>
                <div className="pev-patient-meta">
                  <span>Sexe : {GENDER_LABELS[selectedPatient.gender] || selectedPatient.gender || '—'}</span>
                  <span>Naissance : {patientAgeDisplay}</span>
                  <span>Mère/tuteur : {selectedPatient.emergency_contact || '—'}</span>
                  <span>Quartier : {selectedPatient.address || '—'}</span>
                  <span>Tél. : {selectedPatient.phone || '—'}</span>
                </div>
                {patientJourney?.immunizations?.length > 0 && (
                  <p className="clinical-stat-hint">
                    Historique central : {patientJourney.immunizations.length} vaccination(s) liée(s) au même dossier.
                  </p>
                )}
              </div>
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
                <h2>Fiche vaccination (registre papier)</h2>
                <form className="clinical-form-grid pev-form-grid" onSubmit={submitVaccination}>
                  <label>
                    Code vaccin *
                    <input
                      required
                      value={form.vaccine_code}
                      onChange={(e) => setForm({ ...form, vaccine_code: e.target.value })}
                    />
                  </label>
                  <label>
                    Antigène / vaccin *
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
                    Date vaccination *
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
                  <label>
                    Date péremption vaccin
                    <input
                      type="date"
                      value={form.vaccine_expiry_date}
                      onChange={(e) => setForm({ ...form, vaccine_expiry_date: e.target.value })}
                    />
                  </label>
                  <label>
                    Site d&apos;injection
                    <select
                      value={form.injection_site}
                      onChange={(e) => setForm({ ...form, injection_site: e.target.value })}
                    >
                      {injectionSites.map((s) => (
                        <option key={s.code} value={s.code}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Stratégie
                    <select
                      value={form.vaccination_strategy}
                      onChange={(e) => setForm({ ...form, vaccination_strategy: e.target.value })}
                    >
                      {strategies.map((s) => (
                        <option key={s.code} value={s.code}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Vaccinateur
                    <input
                      value={form.vaccinator_name}
                      onChange={(e) => setForm({ ...form, vaccinator_name: e.target.value })}
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
                  <label className="pev-form-wide">
                    Observations
                    <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                  </label>
                  <label className="pev-form-wide">
                    EIAS / réactions (AEFI)
                    <input value={form.aefi_notes} onChange={(e) => setForm({ ...form, aefi_notes: e.target.value })} />
                  </label>
                  <button type="submit" className="clinical-btn primary">
                    Enregistrer dans le registre
                  </button>
                </form>
              </section>

              <section className="clinical-card">
                <h2>Historique vaccinal du patient</h2>
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
                        <th>Site</th>
                        <th>Stratégie</th>
                        <th>Vaccinateur</th>
                        <th>Proch. RDV</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((row) => (
                        <tr key={row.id}>
                          <td>{formatDate(row.administered_at)}</td>
                          <td>{row.vaccine_name}</td>
                          <td>{row.dose_label || row.dose_number || '—'}</td>
                          <td>{row.batch_number || '—'}</td>
                          <td>{INJECTION_SITE_FALLBACK[row.injection_site] || row.injection_site || '—'}</td>
                          <td>{STRATEGY_FALLBACK[row.vaccination_strategy] || 'Routine'}</td>
                          <td>{row.vaccinator_name || '—'}</td>
                          <td>{formatDate(row.next_appointment_date)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>
            </>
          )}
        </>
      )}

      {view === 'register' && (
        <>
          <section className="clinical-card">
            <h2>Période du registre</h2>
            <div className="clinical-inline-form">
              <label>
                Mois
                <input
                  type="number"
                  min="1"
                  max="12"
                  value={reportMonth.month}
                  onChange={(e) =>
                    setReportMonth((prev) => ({ ...prev, month: Number(e.target.value) || 1 }))
                  }
                />
              </label>
              <label>
                Année
                <input
                  type="number"
                  min="2020"
                  max="2100"
                  value={reportMonth.year}
                  onChange={(e) =>
                    setReportMonth((prev) => ({ ...prev, year: Number(e.target.value) || prev.year }))
                  }
                />
              </label>
              <button
                type="button"
                className="clinical-btn secondary"
                onClick={() => loadMonthlyData(reportMonth.year, reportMonth.month)}
              >
                Actualiser
              </button>
            </div>
            {monthlyReport && (
              <div className="pev-report-summary">
                <p>
                  Total : <strong>{monthlyReport.total_vaccinations}</strong>
                  {' · '}
                  Par vaccin :{' '}
                  {Object.entries(monthlyReport.by_vaccine_type || {})
                    .map(([k, v]) => `${k} (${v})`)
                    .join(', ') || '—'}
                </p>
                <p>
                  Par tranche d&apos;âge :{' '}
                  {Object.entries(monthlyReport.by_age_group || {})
                    .map(([k, v]) => `${k} (${v})`)
                    .join(', ') || '—'}
                </p>
                <p>
                  Par stratégie :{' '}
                  {Object.entries(monthlyReport.by_strategy || {})
                    .map(([k, v]) => `${k} (${v})`)
                    .join(', ') || '—'}
                </p>
              </div>
            )}
          </section>
          <RegisterTable
            rows={monthlyReport?.register_rows || registerRows}
            title={`Registre mensuel PEV — ${reportMonth.month}/${reportMonth.year}`}
          />
        </>
      )}

      {view === 'schedule' && (
        <section className="clinical-card">
          <h2>Calendrier vaccinal national ({schedule.length} entrées)</h2>
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Vaccin</th>
                <th>Dose</th>
                <th>Âge (mois)</th>
              </tr>
            </thead>
            <tbody>
              {schedule.map((item) => (
                <tr key={item.id}>
                  <td>{item.vaccine_code}</td>
                  <td>{item.vaccine_name}</td>
                  <td>{item.dose_label}</td>
                  <td>{item.age_months}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {clinicStats && view === 'record' && (
        <section className="clinical-card">
          <h2>Statistiques du mois en cours</h2>
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
    </div>
  );
}
