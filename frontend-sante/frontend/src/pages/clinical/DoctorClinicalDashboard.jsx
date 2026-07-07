import { useCallback, useEffect, useRef, useState } from 'react';

import { CLINIC_PRINT_NAME } from '../../constants/clinicBranding.js';
import { useAuth } from '../../contexts/AuthContext.jsx';
import clinicalApi from '../../services/clinicalApi';
import { formatApiError } from '../../utils/apiError.js';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const CONSULT_FIELDS = [
  { key: 'chief_complaint', label: 'Motif de consultation', rows: 2 },
  { key: 'history', label: "Histoire de la maladie", rows: 3 },
  { key: 'medical_history', label: 'Antécédents médicaux', rows: 2 },
  { key: 'surgical_history', label: 'Antécédents chirurgicaux', rows: 2 },
  { key: 'gyneco_history', label: 'Antécédents gynéco-obstétricaux', rows: 2 },
  { key: 'allergies', label: 'Allergies', rows: 2 },
  { key: 'current_treatments', label: 'Traitements en cours', rows: 2 },
  { key: 'examination', label: 'Examen clinique', rows: 3 },
  { key: 'diagnosis', label: 'Diagnostic', rows: 2 },
  { key: 'treatment_plan', label: 'Plan de traitement', rows: 3 },
  { key: 'observations', label: 'Observations / Notes', rows: 2 },
];

const EMPTY_FORM = CONSULT_FIELDS.reduce((acc, f) => ({ ...acc, [f.key]: '' }), {
  target_specialty_code: '',
  target_specialty_other: '',
});

const BUCKET_TITLES = {
  patients_waiting: 'Patients en attente',
  consultations_today: "Consultations aujourd'hui",
  hospitalized_patients: 'Patients hospitalisés',
  lab_pending: 'Résultats labo en attente',
  imaging_pending: 'Imagerie en attente',
  completed_consultations: 'Consultations terminées',
};

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=110x110&data=${encodeURIComponent(token)}` : '';

const genderLabel = (g) => {
  if (g === 'F' || g === 'Féminin' || g === 'f') return 'Féminin';
  if (g === 'M' || g === 'Masculin' || g === 'm') return 'Masculin';
  return g || '—';
};

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(value);
  }
};

export default function DoctorClinicalDashboard() {
  const { user } = useAuth();
  const searchRef = useRef(null);

  const [stats, setStats] = useState(null);
  const [queue, setQueue] = useState([]);
  const [activeBucket, setActiveBucket] = useState(null);
  const [bucketRows, setBucketRows] = useState([]);
  const [loadingBucket, setLoadingBucket] = useState(false);

  const [searchQ, setSearchQ] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const [identity, setIdentity] = useState(null);
  const [consultation, setConsultation] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [nurseAssessment, setNurseAssessment] = useState(null);
  const [history, setHistory] = useState([]);
  const [serviceRequests, setServiceRequests] = useState([]);

  const [catalog, setCatalog] = useState({ specialties: [], imaging: [], lab_tests: [] });

  // Lab request
  const [labSearch, setLabSearch] = useState('');
  const [selectedLabs, setSelectedLabs] = useState([]);
  const [labNotes, setLabNotes] = useState('');

  // Imaging request
  const [imagingForm, setImagingForm] = useState({
    modality: 'xray',
    modality_other: '',
    body_part: '',
    clinical_indication: '',
    priority: 'routine',
  });

  // Hospitalization decision
  const [hosp, setHosp] = useState({
    requested: false,
    reason: '',
    duration: '24h',
    custom_days: '',
    notes: '',
  });

  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const [statsRes, queueRes] = await Promise.all([
        clinicalApi.doctorDashboard(),
        clinicalApi.doctorQueue(),
      ]);
      setStats(statsRes.data || null);
      setQueue(queueRes.data || []);
    } catch (err) {
      setError(formatApiError(err, 'Chargement du tableau de bord impossible'));
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    clinicalApi
      .doctorCatalog()
      .then(({ data }) => setCatalog(data || { specialties: [], imaging: [], lab_tests: [] }))
      .catch(() => {});
  }, [loadDashboard]);

  const loadBucket = async (bucket) => {
    if (activeBucket === bucket) {
      setActiveBucket(null);
      setBucketRows([]);
      return;
    }
    setActiveBucket(bucket);
    setLoadingBucket(true);
    try {
      const { data } = await clinicalApi.doctorDashboardQueue(bucket);
      setBucketRows(data || []);
    } catch (err) {
      setBucketRows([]);
      setError(formatApiError(err, 'Liste indisponible'));
    } finally {
      setLoadingBucket(false);
    }
  };

  const runSearch = async () => {
    const q = searchQ.trim();
    if (!q) return;
    setSearching(true);
    setError('');
    try {
      const { data } = await clinicalApi.doctorSearchPatients(q);
      setSearchResults(data || []);
      if ((data || []).length === 0) setMessage('Aucun patient trouvé.');
    } catch (err) {
      setError(formatApiError(err, 'Recherche impossible'));
    } finally {
      setSearching(false);
    }
  };

  const openPatient = async (patientId, chiefComplaint) => {
    if (!patientId) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { data: consult } = await clinicalApi.doctorOpenConsultation({
        patient_id: patientId,
        chief_complaint: chiefComplaint || undefined,
      });
      setConsultation(consult);
      setForm({
        ...EMPTY_FORM,
        chief_complaint: consult.chief_complaint || '',
        history: consult.history || '',
        examination: consult.examination || '',
        diagnosis: consult.diagnosis || '',
        treatment_plan: consult.treatment_plan || '',
        medical_history: consult.medical_history || '',
        surgical_history: consult.surgical_history || '',
        gyneco_history: consult.gyneco_history || '',
        allergies: consult.allergies || '',
        current_treatments: consult.current_treatments || '',
        observations: consult.observations || '',
        target_specialty_code: consult.target_specialty_code || '',
        target_specialty_other: consult.target_specialty_other || '',
      });
      setSelectedLabs([]);
      setLabNotes('');
      setHosp({ requested: false, reason: '', duration: '24h', custom_days: '', notes: '' });
      setSearchResults([]);

      const [idRes, assessRes, histRes] = await Promise.allSettled([
        clinicalApi.doctorPatientIdentity(patientId),
        clinicalApi.nurseGetAssessment(patientId),
        clinicalApi.doctorPatientConsultations(patientId),
      ]);
      if (idRes.status === 'fulfilled') setIdentity(idRes.value.data);
      setNurseAssessment(assessRes.status === 'fulfilled' ? assessRes.value.data || null : null);
      setHistory(histRes.status === 'fulfilled' ? histRes.value.data || [] : []);
      refreshServiceRequests(patientId);
      setMessage(`Consultation #${consult.id} ouverte`);
      loadDashboard();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setError(formatApiError(err, "Impossible d'ouvrir la consultation"));
    } finally {
      setBusy(false);
    }
  };

  const refreshServiceRequests = (patientId) => {
    const pid = patientId || consultation?.patient_id;
    if (!pid) return;
    clinicalApi
      .doctorListServiceRequests(pid)
      .then(({ data }) => setServiceRequests(data || []))
      .catch(() => {});
  };

  const buildUpdatePayload = () => ({
    chief_complaint: form.chief_complaint,
    history: form.history,
    examination: form.examination,
    diagnosis: form.diagnosis,
    treatment_plan: form.treatment_plan,
    medical_history: form.medical_history,
    surgical_history: form.surgical_history,
    gyneco_history: form.gyneco_history,
    allergies: form.allergies,
    current_treatments: form.current_treatments,
    observations: form.observations,
    target_specialty_code: form.target_specialty_code || null,
    target_specialty_other:
      form.target_specialty_code === '__other__' ? form.target_specialty_other : null,
  });

  const saveConsultation = async (complete = false) => {
    if (!consultation) return;
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { data } = await clinicalApi.updateConsultation(consultation.id, {
        ...buildUpdatePayload(),
        status: complete ? 'completed' : undefined,
      });
      setConsultation(data);
      setMessage(complete ? 'Consultation validée et terminée.' : 'Consultation enregistrée.');
      if (consultation.patient_id) {
        clinicalApi
          .doctorPatientConsultations(consultation.patient_id)
          .then(({ data: h }) => setHistory(h || []))
          .catch(() => {});
      }
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Sauvegarde impossible'));
    } finally {
      setBusy(false);
    }
  };

  const toggleLab = (test) => {
    setSelectedLabs((prev) =>
      prev.find((t) => t.code === test.code)
        ? prev.filter((t) => t.code !== test.code)
        : [...prev, test]
    );
  };

  const sendLabRequest = async () => {
    if (!consultation) return;
    if (selectedLabs.length === 0) {
      setError('Sélectionnez au moins un examen de laboratoire.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      for (const t of selectedLabs) {
        await clinicalApi.orderLab(consultation.id, {
          test_code: t.code || t.name,
          test_name: t.name,
          priority: 'routine',
          clinical_notes: labNotes || null,
        });
      }
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'laboratory',
        service_name: selectedLabs.map((t) => t.name).join(', '),
        department: 'Laboratoire',
        notes: labNotes || null,
      });
      setMessage(`${selectedLabs.length} examen(s) envoyé(s) au laboratoire.`);
      setSelectedLabs([]);
      setLabNotes('');
      setLabSearch('');
      refreshServiceRequests();
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Envoi au laboratoire impossible'));
    } finally {
      setBusy(false);
    }
  };

  const sendImagingRequest = async () => {
    if (!consultation) return;
    const modality =
      imagingForm.modality === 'other'
        ? (imagingForm.modality_other || 'other').slice(0, 32)
        : imagingForm.modality;
    if (!modality) {
      setError("Précisez l'examen d'imagerie.");
      return;
    }
    setBusy(true);
    setError('');
    try {
      await clinicalApi.orderImaging(consultation.id, {
        modality,
        body_part: imagingForm.body_part || null,
        clinical_indication: imagingForm.clinical_indication || null,
        priority: imagingForm.priority,
      });
      const label =
        (catalog.imaging || []).find((i) => i.modality === modality)?.label ||
        imagingForm.modality_other ||
        modality;
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'imaging',
        service_name: `${label}${imagingForm.body_part ? ' — ' + imagingForm.body_part : ''}`,
        department: 'Imagerie médicale',
        notes: imagingForm.clinical_indication || null,
      });
      setMessage("Demande d'imagerie envoyée.");
      setImagingForm({ modality: 'xray', modality_other: '', body_part: '', clinical_indication: '', priority: 'routine' });
      refreshServiceRequests();
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, "Envoi de l'imagerie impossible"));
    } finally {
      setBusy(false);
    }
  };

  const requestHospitalization = async () => {
    if (!consultation) return;
    setBusy(true);
    setError('');
    try {
      const durationLabel =
        hosp.duration === 'custom' ? `${hosp.custom_days || '?'} jour(s)` : hosp.duration;
      const reason = hosp.reason || form.chief_complaint || 'Hospitalisation requise';
      await clinicalApi.createAdmission({
        consultation_id: consultation.id,
        reason,
        diagnosis_summary: form.diagnosis || null,
        notes: `Durée: ${durationLabel}${hosp.notes ? ' — ' + hosp.notes : ''}`,
      });
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'other',
        service_name: `Hospitalisation (${durationLabel})`,
        department: 'Hospitalisation',
        notes: `${reason}${hosp.notes ? ' — ' + hosp.notes : ''}`,
      });
      setMessage("Demande d'hospitalisation créée — assignez un lit à l'hospitalisation.");
      refreshServiceRequests();
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Demande d\'hospitalisation impossible'));
    } finally {
      setBusy(false);
    }
  };

  const sendTo = async (target) => {
    if (!consultation) return;
    const map = {
      reception: { category: 'other', department: 'Réception', name: 'Retour à la réception' },
      nurse: { category: 'nursing', department: 'Soins infirmiers', name: 'Soins infirmiers' },
      lab: { category: 'laboratory', department: 'Laboratoire', name: 'Orientation laboratoire' },
      imaging: { category: 'imaging', department: 'Imagerie médicale', name: 'Orientation imagerie' },
    };
    const cfg = map[target];
    setBusy(true);
    setError('');
    try {
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: cfg.category,
        service_name: cfg.name,
        department: cfg.department,
        notes: form.diagnosis || null,
      });
      setMessage(`Patient envoyé vers ${cfg.department}.`);
      refreshServiceRequests();
    } catch (err) {
      setError(formatApiError(err, 'Envoi impossible'));
    } finally {
      setBusy(false);
    }
  };

  const printReport = async () => {
    if (!consultation) return;
    setError('');
    try {
      await clinicalApi.downloadConsultationPdf(
        consultation.id,
        `consultation_${consultation.id}.pdf`
      );
    } catch (err) {
      setError(formatApiError(err, 'Impression impossible'));
    }
  };

  const statCards = [
    { key: 'patients_waiting', label: 'Patients en attente', value: stats?.patients_waiting ?? 0, variant: 'accent' },
    { key: 'consultations_today', label: "Consultations aujourd'hui", value: stats?.consultations_today ?? 0 },
    { key: 'hospitalized_patients', label: 'Patients hospitalisés', value: stats?.hospitalized_patients ?? 0, variant: 'warning' },
    { key: 'lab_pending', label: 'Résultats labo en attente', value: stats?.lab_pending ?? 0 },
    { key: 'imaging_pending', label: 'Imagerie en attente', value: stats?.imaging_pending ?? 0 },
    { key: 'completed_consultations', label: 'Consultations terminées', value: stats?.completed_consultations ?? 0, variant: 'success' },
  ];

  const labResults = (catalog.lab_tests || []).filter((t) => {
    const q = labSearch.trim().toLowerCase();
    if (!q) return false;
    return (
      (t.name || '').toLowerCase().includes(q) ||
      (t.category || '').toLowerCase().includes(q) ||
      (t.code || '').toLowerCase().includes(q)
    );
  }).slice(0, 25);

  return (
    <div className="clinical-page reception-his">
      <header className="reception-his-header">
        <div>
          <p className="nurse-his-clinic-name">{CLINIC_PRINT_NAME}</p>
          <h1>Tableau de bord — Médecin</h1>
          <p className="clinical-lead">Consultation · Examens · Imagerie · Hospitalisation</p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Médecin'}</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="doctor-patient-search">Recherche patient</label>
          <div className="reception-his-search-inline">
            <input
              id="doctor-patient-search"
              ref={searchRef}
              type="search"
              placeholder="N° dossier, nom, téléphone, QR…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runSearch();
                }
              }}
              autoComplete="off"
            />
            <button type="button" className="clinical-btn" onClick={runSearch} disabled={searching || !searchQ.trim()}>
              {searching ? '…' : 'Rechercher'}
            </button>
          </div>
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results reception-his-search-results--inline">
              {searchResults.map((p) => (
                <li key={p.patient_id}>
                  <button type="button" onClick={() => openPatient(p.patient_id)}>
                    <strong>{p.full_name}</strong>
                    <span>N° {p.patient_number || '—'} · {p.phone || '—'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={statCards} onStatClick={loadBucket} activeKey={activeBucket} />

      {activeBucket && (
        <section className="lab-his-queue-panel" aria-live="polite">
          <h3>{BUCKET_TITLES[activeBucket] || 'Liste'}</h3>
          {loadingBucket ? (
            <p className="clinical-hint">Chargement…</p>
          ) : bucketRows.length === 0 ? (
            <p className="clinical-hint">Aucun élément dans cette liste.</p>
          ) : (
            <div className="lab-his-results-wrap">
              <table className="lab-his-queue-table">
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Détail</th>
                    <th>Statut</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {bucketRows.map((r, idx) => (
                    <tr key={`${activeBucket}-${idx}`}>
                      <td>{r.patient_name || '—'}</td>
                      <td>
                        {r.test_name || r.modality || r.diagnosis || r.clinical_status || r.department || '—'}
                      </td>
                      <td><span className="clinical-badge">{r.status || r.clinical_status || '—'}</span></td>
                      <td>
                        {r.patient_id && (
                          <button type="button" className="clinical-btn secondary" onClick={() => openPatient(r.patient_id)}>
                            Ouvrir
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <DepartmentQueuePanel department="doctor" title="File de visite — Médecin" />

      <div className="clinical-grid">
        <section className="clinical-card">
          <h2>File d&apos;attente</h2>
          <ul className="clinical-list">
            {queue.map((item) => (
              <li key={item.id}>
                <strong>{item.patient_name}</strong>
                <br />
                {formatDateTime(item.date)} · <span className="clinical-badge">{item.clinical_status}</span>
                <div className="clinical-actions">
                  <button type="button" className="clinical-btn" onClick={() => openPatient(item.patient_id, item.chief_complaint)} disabled={busy}>
                    Ouvrir le dossier
                  </button>
                </div>
              </li>
            ))}
            {queue.length === 0 && <li>Aucun patient en attente.</li>}
          </ul>
        </section>

        {consultation ? (
          <section className="clinical-card" style={{ gridColumn: '1 / -1' }}>
            <h2>Consultation #{consultation.id}</h2>

            {/* Patient identity */}
            {identity && (
              <div className="clinical-panel" style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                  <div className="nurse-doctor-vitals-grid" style={{ flex: 1 }}>
                    <div><strong>N° dossier</strong> {identity.patient_number || '—'}</div>
                    <div><strong>Nom</strong> {identity.full_name}</div>
                    <div><strong>Âge</strong> {identity.age ?? '—'}</div>
                    <div><strong>Sexe</strong> {genderLabel(identity.sex)}</div>
                    <div><strong>Téléphone</strong> {identity.phone || '—'}</div>
                    <div><strong>Prise en charge</strong> {identity.payer || '—'}</div>
                  </div>
                  {identity.qr_token && (
                    <img src={qrImageUrl(identity.qr_token)} alt="QR patient" width={90} height={90} style={{ alignSelf: 'flex-start' }} />
                  )}
                </div>
              </div>
            )}

            {/* Nurse vitals */}
            {nurseAssessment ? (
              <div className="clinical-panel nurse-doctor-panel" style={{ marginBottom: '1rem' }}>
                <h3>Évaluation infirmière</h3>
                <p className="clinical-lead" style={{ marginTop: 0 }}>
                  {nurseAssessment.nurse_name || 'Infirmier(ère)'} · {formatDateTime(nurseAssessment.recorded_at)}
                </p>
                <div className="nurse-doctor-vitals-grid">
                  <div><strong>T°</strong> {nurseAssessment.temperature_c ?? '—'} °C</div>
                  <div><strong>TA</strong> {nurseAssessment.bp_systolic || '—'}/{nurseAssessment.bp_diastolic || '—'}</div>
                  <div><strong>FC</strong> {nurseAssessment.heart_rate || '—'}</div>
                  <div><strong>FR</strong> {nurseAssessment.respiratory_rate || '—'}</div>
                  <div><strong>Poids</strong> {nurseAssessment.weight_kg ?? '—'} kg</div>
                  <div><strong>Taille</strong> {nurseAssessment.height_cm ?? '—'} cm</div>
                  <div><strong>IMC</strong> {nurseAssessment.bmi ?? '—'}</div>
                </div>
                {nurseAssessment.vitals_observations && <p><strong>Observations :</strong> {nurseAssessment.vitals_observations}</p>}
                {nurseAssessment.nurse_notes && <p><strong>Notes infirmières :</strong> {nurseAssessment.nurse_notes}</p>}
              </div>
            ) : (
              <p className="clinical-hint" style={{ marginBottom: '1rem' }}>Aucune évaluation infirmière disponible.</p>
            )}

            {/* Consultation form */}
            <h3>Dossier de consultation</h3>
            {CONSULT_FIELDS.map((f) => (
              <div className="clinical-field" key={f.key}>
                <label>{f.label}</label>
                <textarea rows={f.rows} value={form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
              </div>
            ))}

            {/* Service decision */}
            <div className="clinical-field">
              <label>Service / Spécialité</label>
              <select
                value={form.target_specialty_code}
                onChange={(e) => setForm({ ...form, target_specialty_code: e.target.value })}
              >
                <option value="">Consultation générale</option>
                {(catalog.specialties || []).map((s) => (
                  <option key={s.code} value={s.code}>{s.label}</option>
                ))}
                <option value="__other__">Autre (préciser)</option>
              </select>
            </div>
            {form.target_specialty_code === '__other__' && (
              <div className="clinical-field">
                <label>Préciser la spécialité</label>
                <input value={form.target_specialty_other} onChange={(e) => setForm({ ...form, target_specialty_other: e.target.value })} />
              </div>
            )}

            <div className="clinical-actions">
              <button type="button" className="clinical-btn secondary" onClick={() => saveConsultation(false)} disabled={busy}>Enregistrer</button>
              <button type="button" className="clinical-btn" onClick={() => saveConsultation(true)} disabled={busy}>Valider la consultation</button>
              <button type="button" className="clinical-btn secondary" onClick={printReport} disabled={busy}>Imprimer le compte rendu</button>
            </div>
            <div className="clinical-actions" style={{ marginTop: '0.5rem' }}>
              <button type="button" className="clinical-btn secondary" onClick={() => sendTo('reception')} disabled={busy}>Envoyer à la réception</button>
              <button type="button" className="clinical-btn secondary" onClick={() => sendTo('nurse')} disabled={busy}>Envoyer à l&apos;infirmerie</button>
              <button type="button" className="clinical-btn secondary" onClick={() => sendTo('lab')} disabled={busy}>Orienter labo</button>
              <button type="button" className="clinical-btn secondary" onClick={() => sendTo('imaging')} disabled={busy}>Orienter imagerie</button>
            </div>

            {/* Laboratory request */}
            <h3 style={{ marginTop: '1.5rem' }}>Demande de laboratoire</h3>
            <div className="clinical-field">
              <label>Rechercher un examen</label>
              <input value={labSearch} onChange={(e) => setLabSearch(e.target.value)} placeholder="Nom ou catégorie de l'examen…" />
            </div>
            {labResults.length > 0 && (
              <ul className="clinical-list" style={{ maxHeight: 180, overflowY: 'auto' }}>
                {labResults.map((t) => (
                  <li key={t.code}>
                    <label style={{ cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(selectedLabs.find((x) => x.code === t.code))}
                        onChange={() => toggleLab(t)}
                        style={{ marginRight: 8 }}
                      />
                      {t.name} <span className="clinical-badge">{t.category || '—'}</span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            {selectedLabs.length > 0 && (
              <p className="clinical-hint">Sélectionnés : {selectedLabs.map((t) => t.name).join(', ')}</p>
            )}
            <div className="clinical-field">
              <label>Notes</label>
              <input value={labNotes} onChange={(e) => setLabNotes(e.target.value)} />
            </div>
            <button type="button" className="clinical-btn" onClick={sendLabRequest} disabled={busy || selectedLabs.length === 0}>Envoyer au laboratoire</button>

            {/* Imaging request */}
            <h3 style={{ marginTop: '1.5rem' }}>Demande d&apos;imagerie</h3>
            <div className="clinical-field">
              <label>Examen</label>
              <select value={imagingForm.modality} onChange={(e) => setImagingForm({ ...imagingForm, modality: e.target.value })}>
                {(catalog.imaging || []).map((i) => (
                  <option key={i.code} value={i.modality}>{i.label}</option>
                ))}
                <option value="other">Autre (préciser)</option>
              </select>
            </div>
            {imagingForm.modality === 'other' && (
              <div className="clinical-field">
                <label>Préciser l&apos;examen</label>
                <input value={imagingForm.modality_other} onChange={(e) => setImagingForm({ ...imagingForm, modality_other: e.target.value })} />
              </div>
            )}
            <div className="clinical-field">
              <label>Région / partie du corps</label>
              <input value={imagingForm.body_part} onChange={(e) => setImagingForm({ ...imagingForm, body_part: e.target.value })} />
            </div>
            <div className="clinical-field">
              <label>Indication clinique</label>
              <input value={imagingForm.clinical_indication} onChange={(e) => setImagingForm({ ...imagingForm, clinical_indication: e.target.value })} />
            </div>
            <button type="button" className="clinical-btn" onClick={sendImagingRequest} disabled={busy}>Envoyer à l&apos;imagerie</button>

            {/* Hospitalization decision */}
            <h3 style={{ marginTop: '1.5rem' }}>Hospitalisation</h3>
            <div className="clinical-field">
              <label>Hospitaliser le patient ?</label>
              <select value={hosp.requested ? 'yes' : 'no'} onChange={(e) => setHosp({ ...hosp, requested: e.target.value === 'yes' })}>
                <option value="no">Non</option>
                <option value="yes">Oui</option>
              </select>
            </div>
            {hosp.requested && (
              <>
                <div className="clinical-field">
                  <label>Motif d&apos;hospitalisation</label>
                  <input value={hosp.reason} onChange={(e) => setHosp({ ...hosp, reason: e.target.value })} />
                </div>
                <div className="clinical-field">
                  <label>Durée</label>
                  <select value={hosp.duration} onChange={(e) => setHosp({ ...hosp, duration: e.target.value })}>
                    <option value="24h">24 heures</option>
                    <option value="48h">48 heures</option>
                    <option value="72h">72 heures</option>
                    <option value="custom">Nombre de jours personnalisé</option>
                  </select>
                </div>
                {hosp.duration === 'custom' && (
                  <div className="clinical-field">
                    <label>Nombre de jours</label>
                    <input type="number" min="1" value={hosp.custom_days} onChange={(e) => setHosp({ ...hosp, custom_days: e.target.value })} />
                  </div>
                )}
                <div className="clinical-field">
                  <label>Notes</label>
                  <input value={hosp.notes} onChange={(e) => setHosp({ ...hosp, notes: e.target.value })} />
                </div>
                <button type="button" className="clinical-btn" onClick={requestHospitalization} disabled={busy}>Créer la demande d&apos;hospitalisation</button>
              </>
            )}

            {/* Service requests created for this patient */}
            <h3 style={{ marginTop: '1.5rem' }}>Demandes de services envoyées</h3>
            {serviceRequests.length === 0 ? (
              <p className="clinical-hint">Aucune demande de service pour ce patient.</p>
            ) : (
              <div className="lab-his-results-wrap">
                <table className="lab-his-queue-table">
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Département</th>
                      <th>Statut</th>
                      <th>Créée le</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serviceRequests.map((s) => (
                      <tr key={s.id}>
                        <td>{s.service_name || '—'}</td>
                        <td>{s.department || '—'}</td>
                        <td><span className="clinical-badge">{s.status || '—'}</span></td>
                        <td>{formatDateTime(s.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Consultation history */}
            <h3 style={{ marginTop: '1.5rem' }}>Historique des consultations</h3>
            {history.length === 0 ? (
              <p className="clinical-hint">Aucune consultation antérieure.</p>
            ) : (
              <div className="lab-his-results-wrap">
                <table className="lab-his-queue-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Médecin</th>
                      <th>Diagnostic</th>
                      <th>Services</th>
                      <th aria-label="Actions" />
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => (
                      <tr key={h.id}>
                        <td>{formatDateTime(h.date)}</td>
                        <td>{h.doctor_name || '—'}</td>
                        <td>{h.diagnosis || '—'}</td>
                        <td>{h.requested_services || '—'}</td>
                        <td>
                          <button
                            type="button"
                            className="clinical-btn secondary"
                            onClick={() => clinicalApi.downloadConsultationPdf(h.id, `consultation_${h.id}.pdf`).catch(() => {})}
                          >
                            Imprimer
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        ) : (
          <section className="clinical-card">
            <h2>Consultation</h2>
            <p className="clinical-lead">Recherchez un patient ou sélectionnez-le dans la file pour démarrer une consultation.</p>
          </section>
        )}
      </div>
    </div>
  );
}
