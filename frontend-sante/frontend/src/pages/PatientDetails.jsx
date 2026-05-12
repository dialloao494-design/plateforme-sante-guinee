import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { appointmentsAPI, patientsAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatGNF, getConsultationTypeLabel, getStatusMeta } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort } from '../utils/formatDateTime.js';
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

  return (
    <div className="patient-details-page">
      <header className="patient-details-header">
        <div>
          <h1>Dossier patient</h1>
          <p>{patientName}</p>
        </div>
        <Link to={backHref} className="button-secondary">
          {user?.role === 'admin' ? 'Retour à la liste' : 'Retour aux rendez-vous'}
        </Link>
      </header>

      {loading && (
        <div className="page-loading" role="status">
          <span className="app-spinner" aria-hidden />
          <span>Chargement du dossier…</span>
        </div>
      )}
      {error && <p className="error">{error}</p>}

      {!loading && (
        <>
          <section className="patient-card patient-card--identity">
            <div className="patient-identity">
              <div className="patient-avatar" aria-hidden>
                {initials}
              </div>
              <div>
                <h2>Informations patient</h2>
                <p className="patient-email-line">
                  <strong>Email:</strong> {patient?.email?.trim() || 'Non renseigné'}
                </p>
              </div>
            </div>
            <p><strong>Nom:</strong> {patientName}</p>
            <p><strong>Âge:</strong> {patient?.age ?? 'Non renseigné'}</p>
            <p><strong>Genre:</strong> {patient?.gender || 'Non renseigné'}</p>
          </section>

          <section className="patient-card">
            <h2>Historique des rendez-vous</h2>
            {appointments.length === 0 && <p>Aucun rendez-vous pour ce patient.</p>}
            <ul className="history-list">
              {appointments.map((appointment) => {
                const statusMeta = getStatusMeta(appointment);
                return (
                  <li key={appointment.id} className="history-item">
                    <div className="history-item-main">
                      <p className="history-item-date">{formatDateTimeShort(appointment.date)}</p>
                      <p className="history-item-meta">
                        {appointment.duration_minutes} min · {formatGNF(appointment.price)} ·{' '}
                        {getConsultationTypeLabel(appointment)}
                      </p>
                    </div>
                    <span className={statusMeta.className}>{statusMeta.label}</span>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="patient-card patient-card--notes">
            <h2>Notes médecin</h2>
            <p className="notes-hint">Stockage local sur cet appareil — à migrer vers le dossier serveur en production.</p>
            <textarea
              rows={6}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Ajoutez des notes de suivi..."
            />
            <div className="notes-actions">
              <button type="button" className="button-pay" onClick={handleSaveNotes}>Enregistrer</button>
              {savedMessage && <span className="saved-note">{savedMessage}</span>}
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default PatientDetails;
