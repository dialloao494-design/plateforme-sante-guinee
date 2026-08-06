import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { CLINIC_PRINT_NAME } from '../../constants/clinicBranding.js';
import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

const EMPTY_FORM = {
  temperature_c: '',
  bp_systolic: '',
  bp_diastolic: '',
  heart_rate: '',
  respiratory_rate: '',
  spo2_percent: '',
  muac_cm: '',
  head_circumference_cm: '',
  height_cm: '',
  weight_kg: '',
  vitals_observations: '',
  reason_for_consultation: '',
  history_of_present_illness: '',
  medical_history: '',
  surgical_history: '',
  gynecological_history: '',
  allergies: '',
  current_treatments: '',
  hospitalized_daily_vitals: '',
  prescription: '',
  nurse_notes: '',
};

const calcAge = (dob) => {
  if (!dob) return '';
  const b = new Date(dob);
  if (Number.isNaN(b.getTime())) return '';
  const n = new Date();
  let age = n.getFullYear() - b.getFullYear();
  const m = n.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && n.getDate() < b.getDate())) age -= 1;
  return age >= 0 ? String(age) : '';
};

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(token)}` : '';

const genderLabel = (gender) => {
  if (gender === 'F') return 'Féminin';
  if (gender === 'M') return 'Masculin';
  if (gender === 'Autre') return 'Autre';
  return gender || '';
};

const patientFullName = (p) => (p ? `${p.last_name || ''} ${p.first_name || ''}`.trim() : '');

const patientAge = (p) => {
  if (!p) return '';
  if (p.date_of_birth) return calcAge(p.date_of_birth);
  if (p.age != null && p.age !== '') return String(p.age);
  return '';
};

const formatDob = (dob, precision) => {
  if (!dob) return '';
  if (precision === 'year') return String(dob).slice(0, 4);
  try {
    return new Date(dob).toLocaleDateString('fr-FR');
  } catch {
    return String(dob);
  }
};

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(value);
  }
};

const BUCKET_TITLES = {
  assessments_today: 'Évaluations aujourd\'hui',
  pending_admissions: 'Admissions en attente',
};

const calcBmi = (weightKg, heightCm) => {
  const w = Number(weightKg);
  const h = Number(heightCm);
  if (!w || !h || h <= 0) return '';
  const hm = h / 100;
  return (w / (hm * hm)).toFixed(1);
};

const ReadOnlyDisplay = ({ value }) => (
  <div
    className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}
    aria-live="polite"
  >
    {value || ''}
  </div>
);

const DisplayField = ({ label, value }) => (
  <label>
    {label}
    <ReadOnlyDisplay value={value} />
  </label>
);

const TextAreaField = ({ label, value, onChange, rows = 4 }) => (
  <label className="nurse-his-textarea-field">
    {label}
    <textarea rows={rows} value={value} onChange={onChange} />
  </label>
);

export default function NurseDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [activeStatBucket, setActiveStatBucket] = useState(null);
  const [queueRows, setQueueRows] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [patientAssessments, setPatientAssessments] = useState([]);
  const [loadingPatientHistory, setLoadingPatientHistory] = useState(false);
  const [showPatientHistory, setShowPatientHistory] = useState(false);

  const bmi = useMemo(() => calcBmi(form.weight_kg, form.height_cm), [form.weight_kg, form.height_cm]);

  const loadDashboard = useCallback(async () => {
    try {
      const { data } = await clinicalApi.nurseDashboard();
      setStats(data);
    } catch {
      setStats(null);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const runPatientSearch = async () => {
    const q = searchQ.trim();
    if (!q) return;
    setSearching(true);
    setError('');
    try {
      const { data } = await clinicalApi.nurseSearchPatients(q);
      setSearchResults(data || []);
    } catch (err) {
      setSearchResults([]);
      setError(formatApiError(err, 'Recherche patient impossible'));
    } finally {
      setSearching(false);
    }
  };

  const loadPatientHistory = async (patientId) => {
    if (!patientId) return;
    setLoadingPatientHistory(true);
    try {
      const { data } = await clinicalApi.nurseListAssessments(patientId);
      setPatientAssessments(data || []);
    } catch {
      setPatientAssessments([]);
    } finally {
      setLoadingPatientHistory(false);
    }
  };

  const selectPatient = async (patient) => {
    if (!patient?.id) return;
    setSelectedPatient(patient);
    setSearchResults([]);
    setSearchQ('');
    setMessage('');
    setError('');
    setForm(EMPTY_FORM);
    setPatientAssessments([]);
    setShowPatientHistory(false);
    setAssessmentLoading(true);
    try {
      const { data } = await clinicalApi.nurseGetPatient(patient.id);
      setSelectedPatient(data);
      await loadPatientHistory(data.id);
    } catch (err) {
      setError(formatApiError(err, 'Chargement du patient impossible'));
      await loadPatientHistory(patient.id);
    } finally {
      setAssessmentLoading(false);
    }
  };

  const openPatientById = async (patientId) => {
    if (!patientId) return;
    setError('');
    try {
      const { data } = await clinicalApi.nurseGetPatient(patientId);
      await selectPatient(data);
    } catch (err) {
      setError(formatApiError(err, 'Ouverture du patient impossible'));
    }
  };

  const loadQueueBucket = async (bucket) => {
    if (activeStatBucket === bucket) {
      setActiveStatBucket(null);
      setQueueRows([]);
      return;
    }
    setActiveStatBucket(bucket);
    setLoadingQueue(true);
    setError('');
    try {
      if (bucket === 'assessments_today') {
        const { data } = await clinicalApi.nurseQueueAssessmentsToday();
        setQueueRows(data || []);
      } else if (bucket === 'pending_admissions') {
        const { data } = await clinicalApi.nurseQueuePendingAdmissions();
        setQueueRows(data || []);
      } else {
        setQueueRows([]);
      }
    } catch (err) {
      setQueueRows([]);
      setError(formatApiError(err, 'Impossible de charger la liste'));
    } finally {
      setLoadingQueue(false);
    }
  };

  const updateForm = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const numOrNull = (v) => {
    if (v === '' || v == null) return null;
    const n = Number(v);
    if (!Number.isFinite(n) || n === 0) return null;
    return n;
  };

  const saveAssessment = async () => {
    if (!selectedPatient?.id) {
      setError('Recherchez et sélectionnez un patient avant d\'enregistrer.');
      return;
    }
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await clinicalApi.nurseSaveAssessment({
        patient_id: selectedPatient.id,
        temperature_c: numOrNull(form.temperature_c),
        bp_systolic: numOrNull(form.bp_systolic),
        bp_diastolic: numOrNull(form.bp_diastolic),
        heart_rate: numOrNull(form.heart_rate),
        respiratory_rate: numOrNull(form.respiratory_rate),
        spo2_percent: numOrNull(form.spo2_percent),
        muac_cm: numOrNull(form.muac_cm),
        head_circumference_cm: numOrNull(form.head_circumference_cm),
        height_cm: numOrNull(form.height_cm),
        weight_kg: numOrNull(form.weight_kg),
        vitals_observations: form.vitals_observations || null,
        reason_for_consultation: form.reason_for_consultation || null,
        history_of_present_illness: form.history_of_present_illness || null,
        medical_history: form.medical_history || null,
        surgical_history: form.surgical_history || null,
        gynecological_history: form.gynecological_history || null,
        allergies: form.allergies || null,
        current_treatments: form.current_treatments || null,
        hospitalized_daily_vitals: form.hospitalized_daily_vitals || null,
        prescription: form.prescription || null,
        nurse_notes: form.nurse_notes || null,
      });
      setMessage('Évaluation infirmière enregistrée — visible par le médecin. Historique actualisé.');
      setForm(EMPTY_FORM);
      // Keep patient selected so history remains available after save.
      setShowPatientHistory(true);
      await loadPatientHistory(selectedPatient.id);
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    { key: 'assessments_today', label: 'Évaluations aujourd\'hui', value: stats?.assessments_today ?? 0, variant: 'success' },
    { key: 'pending_admissions', label: 'Admissions en attente', value: stats?.pending_admissions_today ?? 0, variant: 'warning' },
    { label: 'Patient actif', value: selectedPatient ? patientFullName(selectedPatient) : '—', variant: 'accent' },
  ];

  return (
    <div className="clinical-page reception-his nurse-his">
      <header className="reception-his-header nurse-his-header">
        <div>
          <p className="nurse-his-clinic-name">{CLINIC_PRINT_NAME}</p>
          <h1>Tableau de bord — Infirmier(ère)</h1>
          <p className="clinical-lead">Évaluation patient · Signes vitaux · Transmission au médecin</p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Infirmier(ère)'}</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="nurse-patient-search">Recherche patient</label>
          <div className="reception-his-search-inline">
            <input
              id="nurse-patient-search"
              ref={searchRef}
              type="search"
              placeholder="N° dossier, nom, téléphone, QR…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runPatientSearch();
                }
              }}
              autoComplete="off"
            />
            <button
              type="button"
              className="clinical-btn"
              onClick={runPatientSearch}
              disabled={searching || !searchQ.trim()}
            >
              {searching ? '…' : 'Rechercher'}
            </button>
          </div>
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results reception-his-search-results--inline">
              {searchResults.map((p) => (
                <li key={p.id}>
                  <button type="button" onClick={() => selectPatient(p)}>
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>N° {p.patient_number || '—'} · {p.phone || '—'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {error && <p className="clinical-error">{error}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={statCards} onStatClick={loadQueueBucket} activeKey={activeStatBucket} />

      {activeStatBucket && (
        <section className="lab-his-queue-panel nurse-his-queue-panel" aria-live="polite">
          <h3>{BUCKET_TITLES[activeStatBucket] || 'Liste'}</h3>
          {loadingQueue ? (
            <p className="clinical-hint">Chargement…</p>
          ) : queueRows.length === 0 ? (
            <p className="clinical-hint">Aucun élément dans cette liste.</p>
          ) : activeStatBucket === 'assessments_today' ? (
            <div className="lab-his-results-wrap">
              <table className="lab-his-queue-table">
                <thead>
                  <tr>
                    <th>N° dossier</th>
                    <th>Patient</th>
                    <th>Statut</th>
                    <th>Infirmier(ère)</th>
                    <th>Date / heure</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {queueRows.map((row) => (
                    <tr key={row.assessment_id}>
                      <td>{row.patient_number || row.patient_id}</td>
                      <td>{row.patient_name}</td>
                      <td>{row.status}</td>
                      <td>{row.nurse_name || '—'}</td>
                      <td>{formatDateTime(row.recorded_at)}</td>
                      <td>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openPatientById(row.patient_id)}>
                          Ouvrir patient
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="lab-his-results-wrap">
              <table className="lab-his-queue-table">
                <thead>
                  <tr>
                    <th>N° dossier</th>
                    <th>Patient</th>
                    <th>Date / heure admission</th>
                    <th>Service</th>
                    <th>Priorité</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {queueRows.map((row) => (
                    <tr key={row.admission_id}>
                      <td>{row.patient_number || row.patient_id}</td>
                      <td>{row.patient_name}</td>
                      <td>{formatDateTime(row.admitted_at)}</td>
                      <td>{(row.services || []).join(', ') || row.department || '—'}</td>
                      <td>{row.priority}</td>
                      <td>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openPatientById(row.patient_id)}>
                          Ouvrir patient
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {!selectedPatient ? (
        <div className="clinical-card reception-his-empty-state">
          <p>Recherchez un patient pour commencer l&apos;évaluation infirmière.</p>
        </div>
      ) : assessmentLoading ? (
        <div className="clinical-card reception-his-empty-state">
          <p>Chargement de l&apos;évaluation infirmière…</p>
        </div>
      ) : (
        <form
          className="clinical-card reception-his-form-sheet nurse-his-form-sheet"
          onSubmit={(e) => {
            e.preventDefault();
            saveAssessment();
          }}
        >
          <fieldset className="nurse-his-patient-header">
            <legend>En-tête patient</legend>
            <div className="nurse-his-header-grid">
              <div className="nurse-his-header-fields">
                <div className="reception-his-form-row reception-his-form-row--4">
                  <DisplayField label="N° dossier patient" value={selectedPatient.patient_number || ''} />
                  <DisplayField label="Nom et prénom" value={patientFullName(selectedPatient)} />
                  <DisplayField label="Âge" value={patientAge(selectedPatient)} />
                  <DisplayField label="Sexe" value={genderLabel(selectedPatient.gender)} />
                </div>
              </div>
              {selectedPatient.qr_token && (
                <div className="reception-his-qr-block">
                  <img src={qrImageUrl(selectedPatient.qr_token)} alt="QR patient" width={100} height={100} />
                </div>
              )}
            </div>
          </fieldset>

          <fieldset>
            <legend>Identité</legend>
            <div className="reception-his-form-row reception-his-form-row--3">
              <DisplayField label="Date de naissance" value={formatDob(selectedPatient.date_of_birth, selectedPatient.date_of_birth_precision)} />
              <DisplayField label="Lieu de naissance" value={selectedPatient.place_of_birth || ''} />
              <DisplayField label="Nationalité" value={selectedPatient.nationality || ''} />
              <DisplayField label="État civil" value={selectedPatient.marital_status || ''} />
              <DisplayField label="Profession" value={selectedPatient.profession || ''} />
              <DisplayField label="Langue" value={selectedPatient.preferred_language || ''} />
              <DisplayField label="Téléphone" value={selectedPatient.phone || ''} />
              <DisplayField label="Tél. secondaire" value={selectedPatient.phone_secondary || ''} />
              <DisplayField label="Email" value={selectedPatient.email || ''} />
              <DisplayField label="Adresse" value={selectedPatient.address || ''} />
              <DisplayField label="Commune / ville" value={selectedPatient.commune || selectedPatient.city || ''} />
              <DisplayField label="Région" value={selectedPatient.region || ''} />
            </div>
          </fieldset>

          <fieldset>
            <legend>Signes vitaux</legend>
            <div className="reception-his-form-row reception-his-form-row--4">
              <label>
                Température (°C)
                <input
                  type="number"
                  step="0.1"
                  min="30"
                  max="45"
                  value={form.temperature_c}
                  onChange={(e) => updateForm({ temperature_c: e.target.value })}
                />
              </label>
              <label>
                Pouls / FC (batt/min)
                <input
                  type="number"
                  value={form.heart_rate}
                  onChange={(e) => updateForm({ heart_rate: e.target.value })}
                />
              </label>
              <label>
                SpO2 (%)
                <input
                  type="number"
                  step="0.1"
                  min="50"
                  max="100"
                  value={form.spo2_percent}
                  onChange={(e) => updateForm({ spo2_percent: e.target.value })}
                />
              </label>
              <label>
                Tension artérielle (mmHg)
                <div className="nurse-his-bp-pair">
                  <input
                    type="number"
                    placeholder="Syst."
                    value={form.bp_systolic}
                    onChange={(e) => updateForm({ bp_systolic: e.target.value })}
                  />
                  <span>/</span>
                  <input
                    type="number"
                    placeholder="Diast."
                    value={form.bp_diastolic}
                    onChange={(e) => updateForm({ bp_diastolic: e.target.value })}
                  />
                </div>
              </label>
              <label>
                PB — périmètre brachial (cm)
                <input
                  type="number"
                  step="0.1"
                  min="5"
                  max="60"
                  value={form.muac_cm}
                  onChange={(e) => updateForm({ muac_cm: e.target.value })}
                />
              </label>
              <label>
                PC — périmètre crânien (cm)
                <input
                  type="number"
                  step="0.1"
                  min="20"
                  max="70"
                  value={form.head_circumference_cm}
                  onChange={(e) => updateForm({ head_circumference_cm: e.target.value })}
                />
              </label>
              <label>
                Fréquence respiratoire (resp/min)
                <input
                  type="number"
                  value={form.respiratory_rate}
                  onChange={(e) => updateForm({ respiratory_rate: e.target.value })}
                />
              </label>
              <label>
                Taille (cm)
                <input
                  type="number"
                  step="0.1"
                  value={form.height_cm}
                  onChange={(e) => updateForm({ height_cm: e.target.value })}
                />
              </label>
              <label>
                Poids (kg)
                <input
                  type="number"
                  step="0.1"
                  value={form.weight_kg}
                  onChange={(e) => updateForm({ weight_kg: e.target.value })}
                />
              </label>
              <label>
                IMC (calculé)
                <ReadOnlyDisplay value={bmi} />
              </label>
            </div>
            <TextAreaField
              label="Observations générales"
              rows={3}
              value={form.vitals_observations}
              onChange={(e) => updateForm({ vitals_observations: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Motif de consultation</legend>
            <TextAreaField
              label=""
              rows={4}
              value={form.reason_for_consultation}
              onChange={(e) => updateForm({ reason_for_consultation: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Histoire de la maladie actuelle</legend>
            <TextAreaField
              label=""
              rows={5}
              value={form.history_of_present_illness}
              onChange={(e) => updateForm({ history_of_present_illness: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Antécédents</legend>
            <TextAreaField
              label="Antécédents médicaux"
              rows={3}
              value={form.medical_history}
              onChange={(e) => updateForm({ medical_history: e.target.value })}
            />
            <TextAreaField
              label="Antécédents chirurgicaux"
              rows={3}
              value={form.surgical_history}
              onChange={(e) => updateForm({ surgical_history: e.target.value })}
            />
            <TextAreaField
              label="Antécédents gynéco-obstétricaux"
              rows={3}
              value={form.gynecological_history}
              onChange={(e) => updateForm({ gynecological_history: e.target.value })}
            />
            <TextAreaField
              label="Allergies"
              rows={2}
              value={form.allergies}
              onChange={(e) => updateForm({ allergies: e.target.value })}
            />
            <TextAreaField
              label="Traitements en cours"
              rows={3}
              value={form.current_treatments}
              onChange={(e) => updateForm({ current_treatments: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Prescription</legend>
            <TextAreaField
              label="Prescription"
              rows={4}
              value={form.prescription}
              onChange={(e) => updateForm({ prescription: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Signes vitaux des patients hospitalisés (soins quotidiens)</legend>
            <TextAreaField
              label="Signes vitaux des patients hospitalisés (soins quotidiens)"
              rows={3}
              value={form.hospitalized_daily_vitals}
              onChange={(e) => updateForm({ hospitalized_daily_vitals: e.target.value })}
            />
          </fieldset>

          <fieldset>
            <legend>Notes infirmières</legend>
            <TextAreaField
              label=""
              rows={5}
              value={form.nurse_notes}
              onChange={(e) => updateForm({ nurse_notes: e.target.value })}
            />
          </fieldset>

          <div className="nurse-his-save-row">
            <button type="submit" className="clinical-btn" disabled={loading}>
              {loading ? 'Enregistrement…' : 'Enregistrer l\'évaluation'}
            </button>
          </div>
        </form>
      )}

      {selectedPatient && (
        <section className="clinical-card nurse-his-patient-history">
          <div className="nurse-his-history-header">
            <div>
              <h2>Historique des évaluations du patient</h2>
              <p className="clinical-hint">
                Les anciennes évaluations restent consultables ici et ne préremplissent pas la nouvelle saisie.
              </p>
            </div>
            <button
              type="button"
              className="clinical-btn clinical-btn--secondary"
              onClick={() => {
                setShowPatientHistory((prev) => !prev);
                if (!showPatientHistory) loadPatientHistory(selectedPatient.id);
              }}
            >
              {showPatientHistory ? 'Masquer l\'historique' : 'Consulter l\'historique'}
            </button>
          </div>
          {showPatientHistory && (
            loadingPatientHistory ? (
              <p className="clinical-hint">Chargement de l&apos;historique…</p>
            ) : patientAssessments.length === 0 ? (
              <p className="clinical-hint">Aucune ancienne évaluation pour ce patient.</p>
            ) : (
              <div className="nurse-his-history-list">
                {patientAssessments.map((row) => (
                  <article key={row.id} className="nurse-his-history-card">
                    <h3>Évaluation #{row.id}</h3>
                    <p>
                      <strong>{row.nurse_name || 'Infirmier(ère)'}</strong>
                      {' · '}
                      {formatDateTime(row.recorded_at)}
                    </p>
                    <dl>
                      <div><dt>Température</dt><dd>{row.temperature_c ?? '—'} °C</dd></div>
                      <div><dt>Pouls / FC</dt><dd>{row.heart_rate ?? '—'}</dd></div>
                      <div><dt>SpO2</dt><dd>{row.spo2_percent != null ? `${row.spo2_percent} %` : '—'}</dd></div>
                      <div><dt>TA</dt><dd>{row.bp_systolic || '—'}/{row.bp_diastolic || '—'}</dd></div>
                      <div><dt>PB</dt><dd>{row.muac_cm != null ? `${row.muac_cm} cm` : '—'}</dd></div>
                      <div><dt>PC</dt><dd>{row.head_circumference_cm != null ? `${row.head_circumference_cm} cm` : '—'}</dd></div>
                      <div><dt>Motif</dt><dd>{row.reason_for_consultation || '—'}</dd></div>
                      <div><dt>Allergies</dt><dd>{row.allergies || '—'}</dd></div>
                      <div><dt>Traitements en cours</dt><dd>{row.current_treatments || '—'}</dd></div>
                      <div><dt>Ordonnance</dt><dd>{row.prescription || '—'}</dd></div>
                      <div><dt>SV hospitalisés</dt><dd>{row.hospitalized_daily_vitals || '—'}</dd></div>
                      <div><dt>Notes infirmières</dt><dd>{row.nurse_notes || '—'}</dd></div>
                    </dl>
                  </article>
                ))}
              </div>
            )
          )}
        </section>
      )}

      {(stats?.recent_assessments || []).length > 0 && (
        <section className="clinical-card nurse-his-recent">
          <h2>Évaluations récentes</h2>
          <table className="clinical-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>N° dossier</th>
                <th>Infirmier(ère)</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_assessments.map((row) => (
                <tr key={row.id}>
                  <td>{row.patient_name || '—'}</td>
                  <td>{row.patient_number || '—'}</td>
                  <td>{row.nurse_name || '—'}</td>
                  <td>{new Date(row.recorded_at).toLocaleString('fr-FR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
