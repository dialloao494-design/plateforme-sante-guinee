import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { appointmentsAPI, patientRecordAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatGNF, getConsultationTypeLabel, getStatusMeta } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort } from '../utils/formatDateTime.js';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './PatientDetails.css';

const PatientDetails = () => {
  const { user } = useAuth();
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [patient, setPatient] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [clinicalNotes, setClinicalNotes] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [notesDraft, setNotesDraft] = useState('');
  const [noteType, setNoteType] = useState('suivi');
  const [savingNote, setSavingNote] = useState(false);

  const getErrorMessage = (err, fallback) => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    return err?.message || fallback;
  };

  const canWriteClinical = user?.role === 'doctor' || user?.role === 'admin';

  const loadData = async () => {
    setLoading(true);
    try {
      const { data } = await appointmentsAPI.getAll();
      const list = Array.isArray(data) ? data : [];
      const patientAppointments = list
        .filter((appointment) => Number(appointment.patient_id) === Number(id))
        .sort((a, b) => new Date(b.date) - new Date(a.date));

      setAppointments(patientAppointments);

      try {
        const patientResponse = await patientRecordAPI.getPatient(id);
        setPatient(patientResponse.data || null);
      } catch {
        if (patientAppointments.length > 0) {
          setPatient(patientAppointments[0].patient || null);
        } else {
          setPatient(null);
        }
      }

      try {
        const notesResponse = await patientRecordAPI.listNotes(id);
        setClinicalNotes(Array.isArray(notesResponse.data) ? notesResponse.data : []);
      } catch {
        setClinicalNotes([]);
      }

      try {
        const timelineResponse = await patientRecordAPI.getTimeline(id);
        setTimeline(Array.isArray(timelineResponse.data) ? timelineResponse.data : []);
      } catch {
        setTimeline([]);
      }

      try {
        const docsResponse = await patientRecordAPI.listDocuments(id);
        setDocuments(Array.isArray(docsResponse.data) ? docsResponse.data : []);
      } catch {
        setDocuments([]);
      }

      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Impossible de charger le dossier patient.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const patientName = useMemo(() => {
    if (!patient) return 'Patient';
    return `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || `Patient #${id}`;
  }, [patient, id]);

  const backHref = user?.role === 'admin' ? '/patients' : '/doctor/appointments';

  const handleSaveNote = async () => {
    if (!notesDraft.trim()) return;
    setSavingNote(true);
    try {
      await patientRecordAPI.createNote(id, {
        note_type: noteType,
        contenu: notesDraft.trim(),
      });
      toast.success('Note enregistrée dans le dossier serveur');
      setNotesDraft('');
      const notesResponse = await patientRecordAPI.listNotes(id);
      setClinicalNotes(Array.isArray(notesResponse.data) ? notesResponse.data : []);
      const timelineResponse = await patientRecordAPI.getTimeline(id);
      setTimeline(Array.isArray(timelineResponse.data) ? timelineResponse.data : []);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Enregistrement impossible'));
    } finally {
      setSavingNote(false);
    }
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

  const summaryByAppointment = useMemo(() => {
    const map = new Map();
    for (const event of timeline) {
      if (event.event_type !== 'consultation_summary') continue;
      const apptId = event.payload?.appointment_id;
      if (!apptId) continue;
      const parts = [
        event.payload?.diagnostic,
        event.payload?.traitement,
        event.payload?.recommandations,
      ].filter(Boolean);
      map.set(apptId, parts.join(' — '));
    }
    return map;
  }, [timeline]);

  const timelineLabel = (event) => {
    const map = {
      cis_consultation: 'Consultation CIS',
      lab_order: 'Examen laboratoire',
      lab_result: 'Résultat labo',
      prescription: 'Ordonnance',
      pharmacy_order: 'Pharmacie',
      billing_charge: 'Facturation',
      clinical_note: 'Note clinique',
      consultation_summary: 'Synthèse téléconsultation',
      patient_document: 'Document',
      appointment: 'Rendez-vous',
    };
    return map[event.event_type] || event.summary || event.event_type;
  };

  const handleUploadDocument = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const type = e.target.dataset.type || 'scan';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type_document', type);
    try {
      await patientRecordAPI.uploadDocument(id, formData);
      toast.success('Document enregistré');
      const docsResponse = await patientRecordAPI.listDocuments(id);
      setDocuments(Array.isArray(docsResponse.data) ? docsResponse.data : []);
      const timelineResponse = await patientRecordAPI.getTimeline(id);
      setTimeline(Array.isArray(timelineResponse.data) ? timelineResponse.data : []);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Upload impossible'));
    }
    e.target.value = '';
  };

  const handleDownloadDocument = async (docId, typeDocument) => {
    try {
      const response = await patientRecordAPI.downloadDocument(id, docId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${typeDocument}_${docId}`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Téléchargement impossible'));
    }
  };

  return (
    <div className="patient-details-page ds-page">
      <header className="patient-details-header">
        <div>
          <p className="patient-details-eyebrow">Dossier clinique</p>
          <h1>{patientName}</h1>
          <p className="patient-details-sub">Dossier patient serveur — historisé et auditable</p>
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
                  <dt>Téléphone</dt>
                  <dd>{patient?.phone || '—'}</dd>
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
              <h2>Historique unifié</h2>
              <p className="patient-section-lead">
                Consultations CIS, examens, ordonnances, facturation et documents — chronologie serveur.
              </p>
            </div>
            {timeline.length === 0 && (
              <p className="patient-empty-inline">Aucun événement clinique enregistré.</p>
            )}
            <ol className="patient-timeline">
              {timeline.map((event) => (
                <li key={`${event.event_type}-${event.resource_id}`} className="patient-timeline-item is-past">
                  <div className="patient-timeline-marker" aria-hidden />
                  <div className="patient-timeline-body">
                    <div className="patient-timeline-top">
                      <time dateTime={event.timestamp}>
                        {event.timestamp ? new Date(event.timestamp).toLocaleString('fr-FR') : '—'}
                      </time>
                      <span className="patient-status-badge">{timelineLabel(event)}</span>
                    </div>
                    <p className="patient-timeline-detail">{event.summary}</p>
                    {event.event_type === 'lab_result' && event.payload?.result_summary && (
                      <p className="patient-timeline-summary">{event.payload.result_summary}</p>
                    )}
                    {event.event_type === 'cis_consultation' && event.payload?.diagnosis && (
                      <p className="patient-timeline-summary">Diagnostic : {event.payload.diagnosis}</p>
                    )}
                    {event.event_type === 'billing_charge' && (
                      <p className="patient-timeline-summary">
                        {formatGNF(event.payload?.amount_gnf)} · {event.payload?.payment_status}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className="patient-card patient-card--documents">
            <div className="patient-section-head">
              <h2>Documents cliniques</h2>
              <p className="patient-section-lead">Résultats labo, scans et pièces jointes — stockage sécurisé.</p>
            </div>
            {documents.length > 0 && (
              <ul className="patient-notes-list">
                {documents.map((doc) => (
                  <li key={doc.id}>
                    <strong>{doc.type_document}</strong>
                    <span className="patient-note-date">
                      {doc.created_at ? new Date(doc.created_at).toLocaleString('fr-FR') : ''}
                    </span>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleDownloadDocument(doc.id, doc.type_document)}
                    >
                      Télécharger
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {canWriteClinical && (
              <div className="patient-doc-upload">
                <label htmlFor="doc-scan">Ajouter un scan / document</label>
                <input id="doc-scan" type="file" data-type="scan" accept=".pdf,.jpg,.jpeg,.png,.txt" onChange={handleUploadDocument} />
              </div>
            )}
          </section>

          <section className="patient-card patient-card--timeline">
            <div className="patient-section-head">
              <h2>Parcours rendez-vous</h2>
              <p className="patient-section-lead">
                Vue des rendez-vous et synthèses de téléconsultation.
              </p>
            </div>
            {appointments.length === 0 && (
              <p className="patient-empty-inline">Aucun rendez-vous enregistré pour ce patient.</p>
            )}
            <ol className="patient-timeline">
              {primaryAppointments.map((appointment, index) => {
                const statusMeta = getStatusMeta(appointment);
                const isPast = new Date(appointment.date) < new Date();
                const summaryText = summaryByAppointment.get(appointment.id);
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
                      {summaryText && (
                        <div className="patient-timeline-summary">
                          <strong>Synthèse (téléconsultation)</strong>
                          <p>{summaryText}</p>
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
            <h2>Notes cliniques</h2>
            <p className="notes-hint">
              Stockage serveur sécurisé — chaque lecture et écriture est tracée dans le journal d&apos;audit.
            </p>

            {clinicalNotes.length > 0 && (
              <ul className="patient-notes-list">
                {clinicalNotes.map((note) => (
                  <li key={note.id}>
                    <strong>{note.note_type}</strong>
                    <span className="patient-note-date">
                      {note.created_at ? new Date(note.created_at).toLocaleString('fr-FR') : ''}
                    </span>
                    <p>{note.contenu}</p>
                  </li>
                ))}
              </ul>
            )}

            {canWriteClinical ? (
              <>
                <label htmlFor="note-type">Type de note</label>
                <select id="note-type" value={noteType} onChange={(e) => setNoteType(e.target.value)}>
                  <option value="consultation">Consultation</option>
                  <option value="suivi">Suivi</option>
                  <option value="urgence">Urgence</option>
                </select>
                <textarea
                  rows={6}
                  value={notesDraft}
                  onChange={(e) => setNotesDraft(e.target.value)}
                  placeholder="Synthèse clinique, consignes, suivi à distance…"
                />
                <div className="notes-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSaveNote}
                    disabled={savingNote || !notesDraft.trim()}
                  >
                    {savingNote ? 'Enregistrement…' : 'Enregistrer sur le serveur'}
                  </button>
                </div>
              </>
            ) : (
              <p className="patient-empty-inline">Seuls les médecins autorisés peuvent ajouter des notes cliniques.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
};

export default PatientDetails;
