import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';



const FIELD_LABELS = {

  chief_complaint: 'Motif de consultation',

  history: 'Antécédents',

  examination: 'Examen clinique',

  diagnosis: 'Diagnostic',

  treatment_plan: 'Plan de traitement',

};



export default function DoctorClinicalDashboard() {

  const [queue, setQueue] = useState([]);

  const [consultation, setConsultation] = useState(null);

  const [form, setForm] = useState({

    chief_complaint: '',

    history: '',

    examination: '',

    diagnosis: '',

    treatment_plan: '',

  });

  const [labForm, setLabForm] = useState({ test_code: 'NFS', test_name: 'Numération formule sanguine', priority: 'routine' });

  const [rxForm, setRxForm] = useState({

    medication_name: '',

    dosage: '',

    frequency: '2x/jour',

    duration_days: 7,

  });

  const [recentLabs, setRecentLabs] = useState([]);

  const [recentRx, setRecentRx] = useState([]);

  const [vitalsForm, setVitalsForm] = useState({
    bp_systolic: '',
    bp_diastolic: '',
    heart_rate: '',
    temperature_c: '',
    weight_kg: '',
  });

  const [followUpForm, setFollowUpForm] = useState({
    interval_type: '1m',
    scheduled_date: '',
    reason: '',
    clinical_notes: '',
  });

  const [message, setMessage] = useState('');

  const [error, setError] = useState('');



  const load = useCallback(async () => {

    try {

      const { data } = await clinicalApi.doctorQueue();

      setQueue(data || []);

    } catch (err) {

      setError(err?.response?.data?.detail || 'File médecin indisponible');

    }

  }, []);



  useEffect(() => {

    load();

  }, [load]);



  const startConsultation = async (appointmentId) => {

    setError('');

    try {

      const { data } = await clinicalApi.startConsultation({

        appointment_id: appointmentId,

        chief_complaint: form.chief_complaint || 'Consultation',

      });

      setConsultation(data);

      setRecentLabs([]);

      setRecentRx([]);

      setMessage(`Consultation #${data.id} démarrée`);

      load();

    } catch (err) {

      setError(err?.response?.data?.detail || 'Impossible de démarrer');

    }

  };



  const saveConsultation = async (complete = false) => {

    if (!consultation) return;

    setError('');

    try {

      const { data } = await clinicalApi.updateConsultation(consultation.id, {

        ...form,

        status: complete ? 'completed' : undefined,

      });

      setConsultation(data);

      setMessage(complete ? 'Consultation terminée' : 'Consultation enregistrée');

      if (complete) {

        setConsultation(null);

        load();

      }

    } catch (err) {

      setError(err?.response?.data?.detail || 'Sauvegarde impossible');

    }

  };



  const orderLab = async () => {

    if (!consultation) return;

    try {

      const { data } = await clinicalApi.orderLab(consultation.id, labForm);

      setRecentLabs((prev) => [{ ...labForm, id: data?.id, at: new Date().toISOString() }, ...prev]);

      setMessage(`Examen ${labForm.test_name} prescrit`);

    } catch (err) {

      setError(err?.response?.data?.detail || 'Prescription labo impossible');

    }

  };



  const prescribe = async () => {

    if (!consultation) return;

    try {

      await clinicalApi.prescribe(consultation.id, {

        items: [{ ...rxForm, route: 'oral' }],

      });

      setRecentRx((prev) => [{ ...rxForm, at: new Date().toISOString() }, ...prev]);

      setMessage('Ordonnance transmise à la pharmacie');

      setRxForm({ medication_name: '', dosage: '', frequency: '2x/jour', duration_days: 7 });

    } catch (err) {

      setError(err?.response?.data?.detail || 'Prescription impossible');

    }

  };



  const requestAdmission = async () => {

    if (!consultation) return;

    setError('');

    try {

      const { data } = await clinicalApi.createAdmission({

        consultation_id: consultation.id,

        reason: form.chief_complaint || 'Hospitalisation requise',

        diagnosis_summary: form.diagnosis,

      });

      setMessage(`Admission ${data.admission_number} créée — assignez un lit à l'hospitalisation.`);

    } catch (err) {

      setError(err?.response?.data?.detail || 'Admission impossible');

    }

  };



  const saveVitals = async () => {

    if (!consultation) return;

    try {

      await clinicalApi.recordVitals(consultation.id, {

        bp_systolic: vitalsForm.bp_systolic ? Number(vitalsForm.bp_systolic) : null,

        bp_diastolic: vitalsForm.bp_diastolic ? Number(vitalsForm.bp_diastolic) : null,

        heart_rate: vitalsForm.heart_rate ? Number(vitalsForm.heart_rate) : null,

        temperature_c: vitalsForm.temperature_c ? Number(vitalsForm.temperature_c) : null,

        weight_kg: vitalsForm.weight_kg ? Number(vitalsForm.weight_kg) : null,

      });

      setMessage('Signes vitaux enregistrés');

    } catch (err) {

      setError(err?.response?.data?.detail || 'Enregistrement des signes vitaux impossible');

    }

  };



  const scheduleFollowUp = async () => {

    if (!consultation) return;

    try {

      await clinicalApi.scheduleFollowUp(consultation.id, {

        interval_type: followUpForm.interval_type,

        scheduled_date: followUpForm.interval_type === 'custom' ? followUpForm.scheduled_date : null,

        reason: followUpForm.reason || 'Suivi post-consultation',

        clinical_notes: followUpForm.clinical_notes || null,

        visit_type: 'follow_up',

      });

      setMessage('Suivi planifié');

    } catch (err) {

      setError(err?.response?.data?.detail || 'Planification du suivi impossible');

    }

  };



  const stats = [

    { label: 'Patients en file', value: queue.length, variant: 'accent' },

    { label: 'Consultation active', value: consultation ? `#${consultation.id}` : '—' },

    { label: 'Examens (session)', value: recentLabs.length },

    { label: 'Ordonnances (session)', value: recentRx.length, variant: 'success' },

  ];



  return (

    <div className="clinical-page">

      <h1>Tableau de bord — Médecin</h1>

      <p className="clinical-lead">File d&apos;attente, consultations, prescriptions et demandes d&apos;examens.</p>

      {error && <p className="clinical-error">{String(error)}</p>}

      {message && <p className="clinical-success">{message}</p>}



      <ClinicalStatGrid stats={stats} />



      <nav className="clinical-section-nav" aria-label="Sections médecin">

        <a href="#doctor-queue">File d&apos;attente</a>

        <a href="#doctor-consultation">Consultation</a>

        <a href="#doctor-lab">Examens</a>

        <a href="#doctor-rx">Ordonnances</a>

      </nav>



      <div className="clinical-grid">

        <section id="doctor-queue" className="clinical-card">

          <h2>File d&apos;attente</h2>

          <ul className="clinical-list">

            {queue.map((item) => (

              <li key={item.id}>

                <strong>{item.patient_name}</strong>

                <br />

                {new Date(item.date).toLocaleString('fr-FR')} · <span className="clinical-badge">{item.clinical_status}</span>

                <div className="clinical-actions">

                  <button type="button" className="clinical-btn" onClick={() => startConsultation(item.id)}>

                    Démarrer consultation

                  </button>

                </div>

              </li>

            ))}

            {queue.length === 0 && <li>Aucun patient en attente.</li>}

          </ul>

        </section>



        {consultation ? (

          <section id="doctor-consultation" className="clinical-card">

            <h2>Consultation #{consultation.id}</h2>

            <p><strong>{consultation.patient_name}</strong></p>

            {Object.keys(FIELD_LABELS).map((field) => (

              <div className="clinical-field" key={field}>

                <label>{FIELD_LABELS[field]}</label>

                <textarea

                  rows={2}

                  value={form[field]}

                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}

                />

              </div>

            ))}

            <div className="clinical-actions">

              <button type="button" className="clinical-btn secondary" onClick={() => saveConsultation(false)}>Enregistrer</button>

              <button type="button" className="clinical-btn" onClick={() => saveConsultation(true)}>Terminer</button>

              {consultation && (
                <button type="button" className="clinical-btn secondary" onClick={requestAdmission}>
                  Demander admission
                </button>
              )}

            </div>



            <h3 id="doctor-lab" style={{ marginTop: '1.25rem' }}>Demandes d&apos;examens</h3>

            <div className="clinical-field">

              <label>Code</label>

              <input value={labForm.test_code} onChange={(e) => setLabForm({ ...labForm, test_code: e.target.value })} />

            </div>

            <div className="clinical-field">

              <label>Examen</label>

              <input value={labForm.test_name} onChange={(e) => setLabForm({ ...labForm, test_name: e.target.value })} />

            </div>

            <div className="clinical-field">

              <label>Priorité</label>

              <select value={labForm.priority} onChange={(e) => setLabForm({ ...labForm, priority: e.target.value })}>

                <option value="routine">Routine</option>

                <option value="urgent">Urgent</option>

              </select>

            </div>

            <button type="button" className="clinical-btn" onClick={orderLab}>Envoyer au laboratoire</button>

            {recentLabs.length > 0 && (

              <ul className="clinical-list" style={{ marginTop: '0.75rem' }}>

                {recentLabs.map((lab) => (

                  <li key={`${lab.test_code}-${lab.at}`}>

                    {lab.test_name} ({lab.test_code}) · <span className="clinical-badge">{lab.priority}</span>

                  </li>

                ))}

              </ul>

            )}



            <h3 id="doctor-rx" style={{ marginTop: '1.25rem' }}>Prescriptions</h3>

            <div className="clinical-field">

              <label>Médicament</label>

              <input value={rxForm.medication_name} onChange={(e) => setRxForm({ ...rxForm, medication_name: e.target.value })} />

            </div>

            <div className="clinical-field">

              <label>Posologie</label>

              <input value={rxForm.dosage} onChange={(e) => setRxForm({ ...rxForm, dosage: e.target.value })} placeholder="ex. 500mg" />

            </div>

            <button type="button" className="clinical-btn" onClick={prescribe}>Transmettre à la pharmacie</button>

            {recentRx.length > 0 && (

              <ul className="clinical-list" style={{ marginTop: '0.75rem' }}>

                {recentRx.map((rx) => (

                  <li key={`${rx.medication_name}-${rx.at}`}>

                    {rx.medication_name} {rx.dosage} · {rx.frequency}

                  </li>

                ))}

              </ul>

            )}



            <h3 style={{ marginTop: '1.25rem' }}>Signes vitaux</h3>

            <div className="clinical-field">

              <label>TA systolique / diastolique</label>

              <input placeholder="120" value={vitalsForm.bp_systolic} onChange={(e) => setVitalsForm({ ...vitalsForm, bp_systolic: e.target.value })} style={{ width: '45%', marginRight: '8px' }} />

              <input placeholder="80" value={vitalsForm.bp_diastolic} onChange={(e) => setVitalsForm({ ...vitalsForm, bp_diastolic: e.target.value })} style={{ width: '45%' }} />

            </div>

            <div className="clinical-field">

              <label>FC / Temp / Poids</label>

              <input placeholder="FC" value={vitalsForm.heart_rate} onChange={(e) => setVitalsForm({ ...vitalsForm, heart_rate: e.target.value })} style={{ width: '30%', marginRight: '4px' }} />

              <input placeholder="°C" value={vitalsForm.temperature_c} onChange={(e) => setVitalsForm({ ...vitalsForm, temperature_c: e.target.value })} style={{ width: '30%', marginRight: '4px' }} />

              <input placeholder="kg" value={vitalsForm.weight_kg} onChange={(e) => setVitalsForm({ ...vitalsForm, weight_kg: e.target.value })} style={{ width: '30%' }} />

            </div>

            <button type="button" className="clinical-btn secondary" onClick={saveVitals}>Enregistrer signes vitaux</button>



            <h3 style={{ marginTop: '1.25rem' }}>Planifier un suivi</h3>

            <div className="clinical-field">

              <label>Intervalle</label>

              <select value={followUpForm.interval_type} onChange={(e) => setFollowUpForm({ ...followUpForm, interval_type: e.target.value })}>

                <option value="7d">7 jours</option>

                <option value="15d">15 jours</option>

                <option value="1m">1 mois</option>

                <option value="3m">3 mois</option>

                <option value="6m">6 mois</option>

                <option value="custom">Date personnalisée</option>

              </select>

            </div>

            {followUpForm.interval_type === 'custom' && (

              <div className="clinical-field">

                <label>Date</label>

                <input type="date" value={followUpForm.scheduled_date} onChange={(e) => setFollowUpForm({ ...followUpForm, scheduled_date: e.target.value })} />

              </div>

            )}

            <div className="clinical-field">

              <label>Motif / notes</label>

              <input value={followUpForm.reason} onChange={(e) => setFollowUpForm({ ...followUpForm, reason: e.target.value })} placeholder="Contrôle post-traitement" />

            </div>

            <button type="button" className="clinical-btn" onClick={scheduleFollowUp}>Planifier le suivi</button>

          </section>

        ) : (

          <section className="clinical-card">

            <h2>Consultation</h2>

            <p className="clinical-lead">Sélectionnez un patient dans la file pour démarrer une consultation.</p>

          </section>

        )}

      </div>

    </div>

  );

}


