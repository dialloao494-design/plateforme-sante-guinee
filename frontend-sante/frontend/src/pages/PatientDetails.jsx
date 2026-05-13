import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { appointmentsAPI, patientsAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatGNF, getConsultationTypeLabel, getStatusMeta } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort } from '../utils/formatDateTime.js';
import { getConsultationSummary } from '../utils/clinicalStorage.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './PatientDetails.css';

const PatientDetails = () => {
  const { user } = useAuth();
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [patient, setPatient] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [notes, setNotes] = useState('');
  const [savedMessage, setSavedMessage] = useState('');

  const notesKey = `doctor_notes_${id}`;

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    return err?.message || fallback;
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const { data } = await appointmentsAPI.getAll();
      const list = Array.isArray(data) ? data : [];
      const patientAppointments = list
        .filter((appointment) => Number(appointment.patient_id) === Number(id))
        .sort((a, b) => new Date(b.date) - new Date(a.date));

      setAppointments(patientAppointments);

      if (patientAppointments.length > 0) {
        setPatient(patientAppointments[0].patient || null);
      } else {
        try {
          const patientResponse = await patientsAPI.getById(id);
          setPatient(patientResponse.data || null);
        } catch {
          setPatient(null);
        }
      }

      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger le dossier patient.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setNotes(localStorage.getItem(notesKey) || '');
    loadData();
  }, [id]);

  const patientName = useMemo(() => {
    if (!patient) return 'Patient';
    return `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || `Patient #${id}`;
  }, [patient, id]);

  const backHref = user?.role === 'admin' ? '/patients' : '/doctor/appointments';

  const handleSaveNotes = () => {
    localStorage.setItem(notesKey, notes);
    setSavedMessage('Notes enregistrées.');
    toast.success('Notes enregistrées localement');
    setTimeout(() => setSavedMessage(''), 1800);
  };

  const initials = useMemo(() => {
    if (!patient?.first_name && !patient?.last_name) return '?';
    const a = String(patient?.first_name || '').charAt(0);
    const b = String(patient?.last_name || '').charAt(0);
    return `${a}${b}`.toUpperCase() || '?';
  }, [patient]);

  const nextAppointment = useMemo(() => {
    const now = new Date();
    const future = appointments
      .filter((a) => new Date(a.date) >= now && String(a.status || '').toLowerCase() !== 'cancelled')
      .sort((a, b) => new Date(a.date) - new Date(b.date));
    return future[0] || null;
  }, [appointments]);

  const { primaryAppointments, cancelledAppointments } = useMemo(() => {
    const primary = [];
    const cancelled = [];
    for (const a of appointments) {
      if (String(a.status || '').toLowerCase() === 'cancelled') {
        cancelled.push(a);
      } else {
        primary.push(a);
      }
    }
    return { primaryAppointments: primary, cancelledAppointments: cancelled };
  }, [appointments]);

  return (
    <div className="patient-details-page ds-page">
      <header className="patient-details-header">
        <div>
          <p className="patient-details-eyebrow">Dossier clinique</p>
          <h1>{patientName}</h1>
          <p className="patient-details-sub">Historique des consultations et notes de suivi</p>
        </div>
        <Link to={backHref} className="btn btn-secondary patient-details-back">
          {user?.role === 'admin' ? 'Liste patients' : 'Agenda'}
        </Link>
      </header>

      {loading && (
        <div className="patient-details-loading">
          <PageSkeleton lines={5} />
        </div>
      )}
      {error && <p className="patient-details-error">{error}</p>}

      {!loading && (
        <>
          <section className="patient-hero-grid">
            <div className="patient-card patient-card--identity">
              <div className="patient-identity">
                <div className="patient-avatar" aria-hidden>
                  {initials}
                </div>
                <div>
                  <h2>Identité</h2>
                  <p className="patient-email-line">
                    <span className="patient-label">Email</span> {patient?.email?.trim() || 'Non renseigné'}
                  </p>
                </div>
              </div>
              <dl className="patient-dl">
                <div>
                  <dt>Âge</dt>
                  <dd>{patient?.age ?? '—'}</dd>
                </div>
                <div>
                  <dt>Genre</dt>
                  <dd>{patient?.gender || '—'}</dd>
                </div>
                <div>
                  <dt>Identifiant dossier</dt>
                  <dd>#{id}</dd>
                </div>
              </dl>
            </div>

            {nextAppointment && (
              <div className="patient-card patient-card--next">
                <h2>Prochain rendez-vous</h2>
                <p className="patient-next-when">{formatDateTimeShort(nextAppointment.date)}</p>
                <p className="patient-next-meta">
                  {getConsultationTypeLabel(nextAppointment)} · {nextAppointment.duration_minutes} min ·{' '}
                  {formatGNF(nextAppointment.price)}
                </p>
                <span className={getStatusMeta(nextAppointment).className}>{getStatusMeta(nextAppointment).label}</span>
              </div>
            )}
          </section>

          <section className="patient-card patient-card--timeline">
            <div className="patient-section-head">
              <h2>Parcours de soins</h2>
              <p className="patient-section-lead">
                Vue chronologique des rendez-vous, statuts de paiement et synthèses de téléconsultation enregistrées sur
                cet appareil.
              </p>
            </div>
            {appointments.length === 0 && (
              <p className="patient-empty-inline">Aucun rendez-vous enregistré pour ce patient.</p>
            )}
            <ol className="patient-timeline">
              {primaryAppointments.map((appointment, index) => {
                const statusMeta = getStatusMeta(appointment);
                const isPast = new Date(appointment.date) < new Date();
                const summary = getConsultationSummary(appointment.id);
                return (
                  <li key={appointment.id} className={`patient-timeline-item ${isPast ? 'is-past' : 'is-future'}`}>
                    <div className="patient-timeline-marker" aria-hidden />
                    <div className="patient-timeline-body">
                      <div className="patient-timeline-top">
                        <time dateTime={appointment.date}>{formatDateTimeShort(appointment.date)}</time>
                        <span className={statusMeta.className}>{statusMeta.label}</span>
                      </div>
                      <p className="patient-timeline-detail">
                        {appointment.duration_minutes} min · {formatGNF(appointment.price)} ·{' '}
                        {getConsultationTypeLabel(appointment)}
                      </p>
                      {summary?.text && (
                        <div className="patient-timeline-summary">
                          <strong>Synthèse (téléconsultation)</strong>
                          <p>{summary.text}</p>
                        </div>
                      )}
                      {index === 0 && (
                        <p className="patient-timeline-hint">Consultation la plus récente enregistrée dans le système.</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
            {cancelledAppointments.length > 0 && (
              <details className="patient-cancelled-block">
                <summary>
                  Rendez-vous annulés ({cancelledAppointments.length}) — archivés, hors parcours actif
                </summary>
                <ol className="patient-timeline patient-timeline--muted">
                  {cancelledAppointments.map((appointment) => {
                    const statusMeta = getStatusMeta(appointment);
                    return (
                      <li key={appointment.id} className="patient-timeline-item is-past is-cancelled">
                        <div className="patient-timeline-marker" aria-hidden />
                        <div className="patient-timeline-body">
                          <div className="patient-timeline-top">
                            <time dateTime={appointment.date}>{formatDateTimeShort(appointment.date)}</time>
                            <span className={statusMeta.className}>{statusMeta.label}</span>
                          </div>
                          <p className="patient-timeline-detail">
                            {appointment.duration_minutes} min · {formatGNF(appointment.price)} ·{' '}
                            {getConsultationTypeLabel(appointment)}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </details>
            )}
          </section>

          <section className="patient-card patient-card--notes">
            <h2>Notes médecin</h2>
            <p className="notes-hint">
              Stockage local sur cet appareil — en production, reliez ce bloc au dossier médical serveur (DMNU).
            </p>
            <textarea
              rows={6}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Synthèse clinique, consignes, suivi à distance…"
            />
            <div className="notes-actions">
              <button type="button" className="btn btn-primary" onClick={handleSaveNotes}>
                Enregistrer
              </button>
              {savedMessage && <span className="saved-note">{savedMessage}</span>}
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default PatientDetails;
