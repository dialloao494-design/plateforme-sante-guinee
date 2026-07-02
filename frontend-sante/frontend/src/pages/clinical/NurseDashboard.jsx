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

const formatDob = (dob) => {
  if (!dob) return '';
  try {
    return new Date(dob).toLocaleDateString('fr-FR');
  } catch {
    return String(dob);
  }
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
  const [form, setForm] = useState(EMPTY_FORM);

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

  const loadAssessment = async (patientId) => {
    try {
      const { data } = await clinicalApi.nurseGetAssessment(patientId);
      if (!data) {
        setForm(EMPTY_FORM);
        return;
      }
      setForm({
        temperature_c: data.temperature_c ?? '',
        bp_systolic: data.bp_systolic ?? '',
        bp_diastolic: data.bp_diastolic ?? '',
        heart_rate: data.heart_rate ?? '',
        respiratory_rate: data.respiratory_rate ?? '',
        height_cm: data.height_cm ?? '',
        weight_kg: data.weight_kg ?? '',
        vitals_observations: data.vitals_observations ?? '',
        reason_for_consultation: data.reason_for_consultation ?? '',
        history_of_present_illness: data.history_of_present_illness ?? '',
        medical_history: data.medical_history ?? '',
        surgical_history: data.surgical_history ?? '',
        gynecological_history: data.gynecological_history ?? '',
        allergies: data.allergies ?? '',
        current_treatments: data.current_treatments ?? '',
        nurse_notes: data.nurse_notes ?? '',
      });
    } catch {
      setForm(EMPTY_FORM);
    }
  };

  const selectPatient = async (patient) => {
    setSelectedPatient(patient);
    setSearchResults([]);
    setSearchQ('');
    setMessage('');
    setError('');
    try {
      const { data } = await clinicalApi.receptionHisGetPatient(patient.id);
      setSelectedPatient(data);
      await loadAssessment(data.id);
    } catch (err) {
      setError(formatApiError(err, 'Chargement du patient impossible'));
      await loadAssessment(patient.id);
    }
  };

  const updateForm = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const numOrNull = (v) => {
    if (v === '' || v == null) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
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
        nurse_notes: form.nurse_notes || null,
      });
      setMessage('Évaluation infirmière enregistrée — visible par le médecin.');
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    { label: 'Évaluations aujourd\'hui', value: stats?.assessments_today ?? 0, variant: 'success' },
    { label: 'Admissions en attente', value: stats?.pending_admissions_today ?? 0, variant: 'warning' },
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

      <ClinicalStatGrid stats={statCards} />

      {!selectedPatient ? (
        <div className="clinical-card reception-his-empty-state">
          <p>Recherchez un patient pour commencer l&apos;évaluation infirmière.</p>
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
              <DisplayField label="Date de naissance" value={formatDob(selectedPatient.date_of_birth)} />
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
                Fréquence cardiaque (batt/min)
                <input
                  type="number"
                  value={form.heart_rate}
                  onChange={(e) => updateForm({ heart_rate: e.target.value })}
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
