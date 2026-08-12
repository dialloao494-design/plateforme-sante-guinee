import { useCallback, useEffect, useRef, useState } from 'react';

import DischargeAuthorizationPrint from '../../components/print/DischargeAuthorizationPrint.jsx';
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
  { key: 'hospitalized_vitals', label: 'Signes vitaux patients hospitalisés', rows: 3 },
  { key: 'post_op_report', label: 'Post-opératoire — Compte rendu', rows: 3 },
  { key: 'discharge_summary_text', label: 'Résumé de sortie', rows: 3 },
  { key: 'discharge_authorization', label: 'Autorisation de sortie', rows: 2 },
  { key: 'discharge_against_advice', label: 'Décharge — Contre avis médical', rows: 2 },
  { key: 'prescription_text', label: 'Ordonnance', rows: 3 },
];

const EMPTY_DISCHARGE_MOTIFS = {
  guerison: false,
  stabilise: false,
  contre_avis: false,
  transfert: false,
  demande_patient: false,
  evacuation: false,
  autre_checked: false,
  autre: '',
  admin_formalities: false,
  invoice_paid: false,
  balance_checked: false,
  balance_remaining: '',
  discharge_date: '',
  discharge_time: '',
  discharge_instructions: '',
  next_appointment: '',
};

// Antécédents sub-fields grouped into one boxed section (mockup page 1).
const ANTECEDENT_FIELDS = [
  { key: 'medical_history', label: 'Antécédents médicaux' },
  { key: 'surgical_history', label: 'Antécédents chirurgicaux' },
  { key: 'gyneco_history', label: 'Antécédents gynéco-obstétricaux' },
  { key: 'allergies', label: 'Allergies' },
  { key: 'current_treatments', label: 'Traitements en cours' },
];

const HOSP_DURATIONS = ['24h', '48h', '72h'];

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
  });

  const [dischargeMotifs, setDischargeMotifs] = useState(EMPTY_DISCHARGE_MOTIFS);
  const [showDischargePrint, setShowDischargePrint] = useState(false);

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
        hospitalized_vitals: consult.hospitalized_vitals || '',
        post_op_report: consult.post_op_report || '',
        discharge_summary_text: consult.discharge_summary_text || '',
        discharge_authorization: consult.discharge_authorization || '',
        discharge_against_advice: consult.discharge_against_advice || '',
        prescription_text: consult.prescription_text || '',
      });
      let motifs = { ...EMPTY_DISCHARGE_MOTIFS };
      if (consult.discharge_form_json) {
        try {
          motifs = { ...EMPTY_DISCHARGE_MOTIFS, ...JSON.parse(consult.discharge_form_json) };
        } catch {
          /* keep defaults */
        }
      }
      setDischargeMotifs(motifs);
      setSelectedLabs([]);
      setLabSearch('');
      setImagingForm({ modality: 'xray', modality_other: '', body_part: '', clinical_indication: '', priority: 'routine' });
      setHosp({ requested: false, reason: '', duration: '24h', custom_days: '' });
      setSearchResults([]);
      setShowDischargePrint(false);

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
    hospitalized_vitals: form.hospitalized_vitals || '',
    post_op_report: form.post_op_report || '',
    discharge_summary_text: form.discharge_summary_text || '',
    discharge_authorization: form.discharge_authorization || '',
    discharge_against_advice: form.discharge_against_advice || '',
    prescription_text: form.prescription_text || '',
    discharge_form_json: JSON.stringify(dischargeMotifs),
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
          clinical_notes: null,
        });
      }
      const joined = selectedLabs.map((t) => t.name).join(', ');
      const serviceName =
        joined.length > 250
          ? `${selectedLabs.length} examens labo : ${joined.slice(0, 220)}…`
          : joined;
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'laboratory',
        service_name: serviceName.slice(0, 255),
      });
      setMessage(`${selectedLabs.length} examen(s) envoyé(s) au laboratoire.`);
      setSelectedLabs([]);
      setLabSearch('');
      refreshServiceRequests();
      loadDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Envoi au laboratoire impossible'));
    } finally {
      setBusy(false);
    }
  };

  const clearImagingForm = () => {
    setImagingForm({
      modality: (catalog.imaging || [])[0]?.modality || 'xray',
      modality_other: '',
      body_part: '',
      clinical_indication: '',
      priority: 'routine',
    });
  };

  const sendImagingRequest = async () => {
    if (!consultation) return;
    const modality =
      imagingForm.modality === 'other'
        ? (imagingForm.modality_other || 'other').slice(0, 32)
        : imagingForm.modality;
    if (!modality || (imagingForm.modality === 'other' && !(imagingForm.modality_other || '').trim())) {
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
      const serviceName = `${label}${imagingForm.body_part ? ' — ' + imagingForm.body_part : ''}`.slice(0, 255);
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'imaging',
        service_name: serviceName,
      });
      setMessage("Demande d'imagerie envoyée.");
      clearImagingForm();
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
      // Persist hospitalization documentation on the consultation first
      const { data: saved } = await clinicalApi.updateConsultation(
        consultation.id,
        buildUpdatePayload()
      );
      setConsultation(saved);
      const durationLabel =
        hosp.duration === 'custom' ? `${hosp.custom_days || '?'} jour(s)` : hosp.duration;
      const reason = hosp.reason || form.chief_complaint || 'Hospitalisation requise';
      const notesParts = [
        `Durée: ${durationLabel}`,
        form.hospitalized_vitals ? `SV hospitalisés: ${form.hospitalized_vitals}` : '',
        form.post_op_report ? `Post-op: ${form.post_op_report}` : '',
        form.discharge_summary_text ? `Résumé sortie: ${form.discharge_summary_text}` : '',
        form.prescription_text ? `Ordonnance: ${form.prescription_text}` : '',
      ].filter(Boolean);
      await clinicalApi.createAdmission({
        consultation_id: consultation.id,
        reason,
        diagnosis_summary: form.diagnosis || null,
        notes: notesParts.join('\n'),
      });
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: 'other',
        service_name: `Hospitalisation (${durationLabel})`.slice(0, 255),
      });
      setHosp({ ...hosp, requested: true });
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
      reception: { category: 'other', label: 'Réception', name: 'Retour à la réception' },
      nurse: { category: 'nursing', label: 'Soins infirmiers', name: 'Soins infirmiers' },
      lab: { category: 'laboratory', label: 'Laboratoire', name: 'Orientation laboratoire' },
      imaging: { category: 'imaging', label: 'Imagerie médicale', name: 'Orientation imagerie' },
    };
    const cfg = map[target];
    setBusy(true);
    setError('');
    try {
      await clinicalApi.doctorCreateServiceRequest({
        patient_id: consultation.patient_id,
        service_category: cfg.category,
        service_name: cfg.name,
      });
      setMessage(`Patient envoyé vers ${cfg.label}.`);
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

  const buildDischargePrintData = () => {
    const specialty =
      form.target_specialty_code === '__other__'
        ? form.target_specialty_other
        : (catalog.specialties || []).find((s) => s.code === form.target_specialty_code)?.label;
    return {
      authorization_number: consultation ? `AS-${consultation.id}` : '',
      patient_number: identity?.patient_number || '',
      full_name: [identity?.last_name, identity?.first_name].filter(Boolean).join(' ') || identity?.full_name || '',
      age: identity?.age ?? identity?.age_years ?? '',
      gender: identity?.gender || '',
      service: specialty || 'Médecine générale',
      doctor_name: user?.full_name || user?.email || '',
      motifs: {
        guerison: dischargeMotifs.guerison,
        stabilise: dischargeMotifs.stabilise,
        contre_avis: dischargeMotifs.contre_avis || Boolean((form.discharge_against_advice || '').trim()),
        transfert: dischargeMotifs.transfert,
        demande_patient: dischargeMotifs.demande_patient,
        evacuation: dischargeMotifs.evacuation,
        autre_checked: dischargeMotifs.autre_checked,
        autre: dischargeMotifs.autre,
      },
      discharge_date: dischargeMotifs.discharge_date || new Date().toLocaleDateString('fr-FR'),
      discharge_time: dischargeMotifs.discharge_time || '',
      discharge_authorization: form.discharge_authorization || form.discharge_summary_text || '',
      discharge_instructions: dischargeMotifs.discharge_instructions || form.discharge_summary_text || '',
      prescription_text: form.prescription_text || '',
      next_appointment: dischargeMotifs.next_appointment || '',
      admin_formalities: dischargeMotifs.admin_formalities,
      invoice_paid: dischargeMotifs.invoice_paid,
      balance_checked: dischargeMotifs.balance_checked,
      balance_remaining: dischargeMotifs.balance_remaining,
      discharge_against_advice: form.discharge_against_advice || '',
      printed_by: (user?.full_name || user?.email || '').toUpperCase(),
    };
  };

  const printDischargeAuthorization = async () => {
    if (!consultation) return;
    setError('');
    try {
      // Persist latest hospitalization/discharge fields before printing
      const { data } = await clinicalApi.updateConsultation(consultation.id, buildUpdatePayload());
      setConsultation(data);
      setShowDischargePrint(true);
      window.setTimeout(() => {
        window.print();
        window.setTimeout(() => setShowDischargePrint(false), 300);
      }, 150);
    } catch (err) {
      setError(formatApiError(err, "Impossible d'imprimer l'autorisation de sortie"));
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

  const labResults = (() => {
    const tests = catalog.lab_tests || [];
    const q = labSearch.trim().toLowerCase();
    const filtered = q
      ? tests.filter(
          (t) =>
            (t.name || '').toLowerCase().includes(q) ||
            (t.category || '').toLowerCase().includes(q) ||
            (t.code || '').toLowerCase().includes(q)
        )
      : tests;
    return filtered.slice(0, 80);
  })();

  return (
    <div className="clinical-page reception-his" data-testid="doctor-dashboard">
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
            <button
              type="button"
              className="clinical-btn"
              data-testid="doctor-patient-search-btn"
              onClick={runSearch}
              disabled={searching || !searchQ.trim()}
            >
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
          <section className="clinical-card doctor-consult" style={{ gridColumn: '1 / -1' }}>
            <div className="doctor-consult-head">
              <h2>Médecin — Consultation #{consultation.id}</h2>
              <span className="clinical-badge">{consultation.status || 'in_progress'}</span>
            </div>

            {/* 1. Identité du patient */}
            <section className="doctor-box">
              <div className="doctor-box-title">Identité du patient</div>
              <div className="doctor-box-body">
                {identity ? (
                  <div className="doctor-identity">
                    <div className="doctor-identity-grid">
                      <div><span>N° dossier</span><strong>{identity.patient_number || '—'}</strong></div>
                      <div><span>Nom complet</span><strong>{identity.full_name}</strong></div>
                      <div><span>Âge</span><strong>{identity.age ?? '—'}</strong></div>
                      <div><span>Sexe</span><strong>{genderLabel(identity.sex)}</strong></div>
                      <div><span>Téléphone</span><strong>{identity.phone || '—'}</strong></div>
                      <div><span>Prise en charge</span><strong>{identity.payer || '—'}</strong></div>
                    </div>
                    {identity.qr_token && (
                      <img className="doctor-identity-qr" src={qrImageUrl(identity.qr_token)} alt="QR patient" width={92} height={92} />
                    )}
                  </div>
                ) : (
                  <p className="clinical-hint">Identité indisponible.</p>
                )}
              </div>
            </section>

            {/* 2. Paramètres vitaux — lecture seule (saisie infirmière) */}
            <section className="doctor-box doctor-box--readonly" aria-readonly="true">
              <div className="doctor-box-title">
                Paramètres vitaux
                <span className="doctor-readonly-badge">Lecture seule — saisie infirmière</span>
              </div>
              <div className="doctor-box-body">
                {nurseAssessment ? (
                  <>
                    <p className="clinical-lead" style={{ marginTop: 0 }}>
                      {nurseAssessment.nurse_name || 'Infirmier(ère)'} · {formatDateTime(nurseAssessment.recorded_at)}
                    </p>
                    <div className="doctor-vitals-grid">
                      <div><span>T°</span><strong>{nurseAssessment.temperature_c ?? '—'} °C</strong></div>
                      <div><span>TA</span><strong>{nurseAssessment.bp_systolic || '—'}/{nurseAssessment.bp_diastolic || '—'}</strong></div>
                      <div><span>FC</span><strong>{nurseAssessment.heart_rate || '—'}</strong></div>
                      <div><span>FR</span><strong>{nurseAssessment.respiratory_rate || '—'}</strong></div>
                      <div><span>Poids</span><strong>{nurseAssessment.weight_kg ?? '—'} kg</strong></div>
                      <div><span>Taille</span><strong>{nurseAssessment.height_cm ?? '—'} cm</strong></div>
                      <div><span>IMC</span><strong>{nurseAssessment.bmi ?? '—'}</strong></div>
                    </div>
                    {nurseAssessment.vitals_observations && <p style={{ marginBottom: 0 }}><strong>Observations :</strong> {nurseAssessment.vitals_observations}</p>}
                    {nurseAssessment.hospitalized_daily_vitals && (
                      <div className="doctor-nurse-readonly-block">
                        <strong>Signes vitaux hospitalisés (soins quotidiens) — infirmier(ère) :</strong>
                        <p>{nurseAssessment.hospitalized_daily_vitals}</p>
                      </div>
                    )}
                    {nurseAssessment.reason_for_consultation && (
                      <p style={{ marginBottom: 0 }}><strong>Motif (infirmière) :</strong> {nurseAssessment.reason_for_consultation}</p>
                    )}
                    {nurseAssessment.prescription && <p style={{ marginBottom: 0 }}><strong>Ordonnance (infirmière) :</strong> {nurseAssessment.prescription}</p>}
                    {nurseAssessment.nurse_notes && <p style={{ marginBottom: 0 }}><strong>Notes infirmières :</strong> {nurseAssessment.nurse_notes}</p>}
                    <p className="clinical-hint" style={{ marginBottom: 0 }}>
                      Le médecin consulte ces paramètres sans pouvoir les modifier. La saisie se fait uniquement côté infirmier.
                    </p>
                  </>
                ) : (
                  <p className="clinical-hint">Aucune évaluation infirmière disponible.</p>
                )}
              </div>
            </section>

            {/* 3. Motif de consultation */}
            <section className="doctor-box">
              <div className="doctor-box-title">Motif de consultation</div>
              <div className="doctor-box-body">
                <textarea rows={2} value={form.chief_complaint} onChange={(e) => setForm({ ...form, chief_complaint: e.target.value })} />
              </div>
            </section>

            {/* 4. Histoire de la maladie */}
            <section className="doctor-box">
              <div className="doctor-box-title">Histoire de la maladie</div>
              <div className="doctor-box-body">
                <textarea rows={3} value={form.history} onChange={(e) => setForm({ ...form, history: e.target.value })} />
              </div>
            </section>

            {/* 5. Antécédents */}
            <section className="doctor-box">
              <div className="doctor-box-title">Antécédents</div>
              <div className="doctor-box-body doctor-antecedents">
                {ANTECEDENT_FIELDS.map((f) => (
                  <div className="doctor-subfield" key={f.key}>
                    <label>{f.label}</label>
                    <textarea rows={2} value={form[f.key]} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
                  </div>
                ))}
              </div>
            </section>

            {/* Examen clinique */}
            <section className="doctor-box">
              <div className="doctor-box-title">Examen clinique</div>
              <div className="doctor-box-body">
                <textarea rows={3} value={form.examination} onChange={(e) => setForm({ ...form, examination: e.target.value })} />
              </div>
            </section>

            {/* 6. Diagnostic */}
            <section className="doctor-box">
              <div className="doctor-box-title">Diagnostic</div>
              <div className="doctor-box-body">
                <textarea rows={2} value={form.diagnosis} onChange={(e) => setForm({ ...form, diagnosis: e.target.value })} />
              </div>
            </section>

            {/* 7. Traitement à suivre */}
            <section className="doctor-box">
              <div className="doctor-box-title">Traitement à suivre</div>
              <div className="doctor-box-body">
                <textarea rows={3} value={form.treatment_plan} onChange={(e) => setForm({ ...form, treatment_plan: e.target.value })} />
              </div>
            </section>

            {/* 8. Service + À hospitaliser (une ligne) */}
            <div className="doctor-decision-row">
              <div className="doctor-decision-field">
                <label>Service</label>
                <select
                  value={form.target_specialty_code}
                  onChange={(e) => setForm({ ...form, target_specialty_code: e.target.value })}
                >
                  <option value="">Consultation générale (toutes spécialités)</option>
                  {(catalog.specialties || []).map((s) => (
                    <option key={s.code} value={s.code}>{s.label}</option>
                  ))}
                  <option value="__other__">Autre (préciser)</option>
                </select>
                {form.target_specialty_code === '__other__' && (
                  <input
                    style={{ marginTop: '0.4rem' }}
                    placeholder="Préciser la spécialité"
                    value={form.target_specialty_other}
                    onChange={(e) => setForm({ ...form, target_specialty_other: e.target.value })}
                  />
                )}
              </div>
              <div className="doctor-decision-field">
                <label>À hospitaliser</label>
                <div className="doctor-toggle">
                  <label className={hosp.requested ? 'is-active' : ''}>
                    <input
                      type="radio"
                      name="hospitalize"
                      checked={hosp.requested}
                      onChange={() => setHosp({ ...hosp, requested: true })}
                    />
                    Oui
                  </label>
                  <label className={!hosp.requested ? 'is-active' : ''}>
                    <input
                      type="radio"
                      name="hospitalize"
                      checked={!hosp.requested}
                      onChange={() => setHosp({ ...hosp, requested: false })}
                    />
                    Non
                  </label>
                </div>
              </div>
            </div>

            {/* 9. Observation */}
            <section className="doctor-box">
              <div className="doctor-box-title">Observation</div>
              <div className="doctor-box-body">
                <textarea rows={2} value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} />
              </div>
            </section>

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

            {/* ===== Page 2 : Demande de service ===== */}
            <section className="doctor-box doctor-service-box">
              <div className="doctor-box-title">Demande de service</div>
              <div className="doctor-box-body">

                {/* Laboratoire */}
                <div className="doctor-service-block">
                  <h4>Orientation laboratoire — sélectionner un ou plusieurs examens</h4>
                  <input
                    className="doctor-service-search"
                    value={labSearch}
                    onChange={(e) => setLabSearch(e.target.value)}
                    placeholder="Rechercher un examen (nom ou code)…"
                    aria-label="Rechercher examen laboratoire"
                  />
                  {(catalog.lab_tests || []).length === 0 ? (
                    <p className="clinical-hint">Catalogue d&apos;examens indisponible. Réessayez ou contactez l&apos;administrateur.</p>
                  ) : (
                    <ul className="doctor-service-options">
                      {labResults.map((t) => (
                        <li key={t.code || t.name}>
                          <label>
                            <input
                              type="checkbox"
                              checked={Boolean(selectedLabs.find((x) => x.code === t.code))}
                              onChange={() => toggleLab(t)}
                            />
                            {t.name} <span className="clinical-badge">{t.category || '—'}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                  {!labSearch.trim() && (catalog.lab_tests || []).length > labResults.length && (
                    <p className="clinical-hint">Affichage des {labResults.length} premiers examens — affinez la recherche pour les autres.</p>
                  )}
                  {labSearch.trim() && labResults.length === 0 && (
                    <p className="clinical-hint">Aucun examen ne correspond à « {labSearch} ».</p>
                  )}
                  {selectedLabs.length > 0 && (
                    <p className="clinical-hint">
                      Sélectionnés ({selectedLabs.length}) : {selectedLabs.map((t) => t.name).join(', ')}
                      {' '}
                      <button type="button" className="clinical-btn secondary doctor-inline-clear" onClick={() => setSelectedLabs([])}>
                        Effacer la sélection
                      </button>
                    </p>
                  )}
                  <button type="button" className="clinical-btn" onClick={sendLabRequest} disabled={busy || selectedLabs.length === 0}>
                    Envoyer au laboratoire
                  </button>
                </div>

                {/* Imagerie médicale */}
                <div className="doctor-service-block">
                  <h4>Imagerie médicale — examen</h4>
                  <label className="doctor-field-label">Type d&apos;examen</label>
                  <div className="doctor-imaging-row">
                    <select
                      value={imagingForm.modality}
                      onChange={(e) => setImagingForm({ ...imagingForm, modality: e.target.value })}
                      aria-label="Type d'examen d'imagerie"
                    >
                      {(catalog.imaging || []).map((i) => (
                        <option key={i.code || i.modality} value={i.modality}>{i.label}</option>
                      ))}
                      <option value="other">Autre (préciser)</option>
                    </select>
                  </div>
                  {imagingForm.modality === 'other' && (
                    <input
                      className="doctor-service-search"
                      placeholder="Préciser l'examen (ex. Doppler)…"
                      value={imagingForm.modality_other}
                      onChange={(e) => setImagingForm({ ...imagingForm, modality_other: e.target.value })}
                    />
                  )}
                  <label className="doctor-field-label" htmlFor="imaging-body-part">Région / partie du corps</label>
                  <div className="doctor-imaging-body-row">
                    <input
                      id="imaging-body-part"
                      className="doctor-service-search"
                      placeholder="Ex. thorax, abdomen, genou droit…"
                      value={imagingForm.body_part}
                      onChange={(e) => setImagingForm({ ...imagingForm, body_part: e.target.value })}
                    />
                    <button
                      type="button"
                      className="clinical-btn secondary"
                      onClick={() => setImagingForm({ ...imagingForm, body_part: '' })}
                      disabled={!imagingForm.body_part}
                    >
                      Effacer
                    </button>
                  </div>
                  <label className="doctor-field-label" htmlFor="imaging-indication">Indication clinique</label>
                  <input
                    id="imaging-indication"
                    className="doctor-service-search"
                    placeholder="Indication clinique…"
                    value={imagingForm.clinical_indication}
                    onChange={(e) => setImagingForm({ ...imagingForm, clinical_indication: e.target.value })}
                  />
                  <div className="clinical-actions" style={{ marginTop: '0.5rem' }}>
                    <button type="button" className="clinical-btn" onClick={sendImagingRequest} disabled={busy}>
                      Envoyer à l&apos;imagerie
                    </button>
                    <button type="button" className="clinical-btn secondary" onClick={clearImagingForm} disabled={busy}>
                      Effacer le formulaire
                    </button>
                  </div>
                </div>

                {/* Hospitalisation */}
                <div className="doctor-service-block">
                  <h4>Hospitalisation</h4>
                  <p className="doctor-hosp-label">À hospitaliser pour :</p>
                  <div className="doctor-duration-pills">
                    {HOSP_DURATIONS.map((d) => (
                      <button
                        type="button"
                        key={d}
                        className={`doctor-pill ${hosp.duration === d ? 'is-active' : ''}`}
                        onClick={() => setHosp({ ...hosp, requested: true, duration: d })}
                      >
                        {d.toUpperCase()}
                      </button>
                    ))}
                    <span className="doctor-duration-custom">
                      <input
                        type="number"
                        min="1"
                        placeholder="jours"
                        value={hosp.custom_days}
                        onChange={(e) => setHosp({ ...hosp, requested: true, duration: 'custom', custom_days: e.target.value })}
                      />
                    </span>
                  </div>
                  <input
                    className="doctor-service-search"
                    placeholder="Motif d'hospitalisation…"
                    value={hosp.reason}
                    onChange={(e) => setHosp({ ...hosp, reason: e.target.value })}
                  />

                  <div className="doctor-hosp-doc-fields">
                    <label>
                      Signes vitaux patients hospitalisés
                      <textarea
                        rows={3}
                        value={form.hospitalized_vitals}
                        onChange={(e) => setForm({ ...form, hospitalized_vitals: e.target.value })}
                        placeholder="Suivi quotidien des signes vitaux (médecin)…"
                      />
                    </label>
                    {nurseAssessment?.hospitalized_daily_vitals && (
                      <p className="doctor-nurse-readonly-block">
                        <strong>Dernière saisie infirmière (lecture seule) :</strong>{' '}
                        {nurseAssessment.hospitalized_daily_vitals}
                      </p>
                    )}
                    <label>
                      Post-opératoire — Compte rendu
                      <textarea
                        rows={3}
                        value={form.post_op_report}
                        onChange={(e) => setForm({ ...form, post_op_report: e.target.value })}
                      />
                    </label>
                    <label>
                      Résumé de sortie
                      <textarea
                        rows={3}
                        value={form.discharge_summary_text}
                        onChange={(e) => setForm({ ...form, discharge_summary_text: e.target.value })}
                      />
                    </label>
                    <label>
                      Autorisation de sortie
                      <textarea
                        rows={2}
                        value={form.discharge_authorization}
                        onChange={(e) => setForm({ ...form, discharge_authorization: e.target.value })}
                      />
                    </label>
                    <label>
                      Décharge — Contre avis médical
                      <textarea
                        rows={2}
                        value={form.discharge_against_advice}
                        onChange={(e) => setForm({ ...form, discharge_against_advice: e.target.value })}
                      />
                    </label>
                    <label>
                      Ordonnance
                      <textarea
                        rows={3}
                        value={form.prescription_text}
                        onChange={(e) => setForm({ ...form, prescription_text: e.target.value })}
                      />
                    </label>

                    <fieldset className="doctor-discharge-motifs">
                      <legend>Motif de la sortie (autorisation)</legend>
                      <label><input type="checkbox" checked={dischargeMotifs.guerison} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, guerison: e.target.checked })} /> Guérison / Fin de traitement</label>
                      <label><input type="checkbox" checked={dischargeMotifs.stabilise} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, stabilise: e.target.checked })} /> État de santé stabilisé</label>
                      <label><input type="checkbox" checked={dischargeMotifs.contre_avis} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, contre_avis: e.target.checked })} /> Sortie contre avis médical</label>
                      <label><input type="checkbox" checked={dischargeMotifs.transfert} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, transfert: e.target.checked })} /> Transfert vers un autre établissement</label>
                      <label><input type="checkbox" checked={dischargeMotifs.demande_patient} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, demande_patient: e.target.checked })} /> À la demande du patient ou de la famille</label>
                      <label><input type="checkbox" checked={dischargeMotifs.evacuation} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, evacuation: e.target.checked })} /> Évacuation</label>
                      <label className="doctor-discharge-autre">
                        <input type="checkbox" checked={dischargeMotifs.autre_checked} onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, autre_checked: e.target.checked })} /> Autre
                        <input
                          type="text"
                          value={dischargeMotifs.autre}
                          onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, autre: e.target.value, autre_checked: true })}
                          placeholder="Préciser…"
                        />
                      </label>
                      <label>
                        Consignes de sortie
                        <input
                          type="text"
                          value={dischargeMotifs.discharge_instructions}
                          onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, discharge_instructions: e.target.value })}
                        />
                      </label>
                      <label>
                        Prochain rendez-vous
                        <input
                          type="text"
                          value={dischargeMotifs.next_appointment}
                          onChange={(e) => setDischargeMotifs({ ...dischargeMotifs, next_appointment: e.target.value })}
                          placeholder="JJ/MM/AAAA à HH h MM"
                        />
                      </label>
                    </fieldset>
                  </div>

                  <div className="clinical-actions" style={{ marginTop: '0.75rem' }}>
                    <button type="button" className="clinical-btn" onClick={requestHospitalization} disabled={busy}>
                      Créer la demande d&apos;hospitalisation
                    </button>
                    <button type="button" className="clinical-btn secondary" onClick={printDischargeAuthorization} disabled={busy}>
                      Imprimer autorisation de sortie
                    </button>
                  </div>
                </div>

              </div>
            </section>

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
                      <th>Statut</th>
                      <th>Créée le</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serviceRequests.map((s) => (
                      <tr key={s.id}>
                        <td>{s.service_name || '—'}</td>
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
                            onClick={() =>
                              clinicalApi
                                .downloadConsultationPdf(h.id, `consultation_${h.id}.pdf`)
                                .catch(() => setError("Impossible de télécharger le PDF de consultation."))
                            }
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

      {showDischargePrint && (
        <div className="doctor-discharge-print-root" aria-hidden={!showDischargePrint}>
          <DischargeAuthorizationPrint data={buildDischargePrintData()} />
        </div>
      )}
    </div>
  );
}
