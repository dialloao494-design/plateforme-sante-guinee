import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { appointmentsAPI, patientsAPI } from '../services/api.js';
import { formatGNF, getStatusMeta } from '../utils/appointmentPresentation.js';
import './PatientDetails.css';

const PatientDetails = () => {
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

  const handleSaveNotes = () => {
    localStorage.setItem(notesKey, notes);
    setSavedMessage('Notes enregistrées.');
    setTimeout(() => setSavedMessage(''), 1800);
  };

  return (
    <div className="patient-details-page">
      <header className="patient-details-header">
        <div>
          <h1>Dossier patient</h1>
          <p>{patientName}</p>
        </div>
        <Link to="/doctor/appointments" className="button-secondary">Retour aux rendez-vous</Link>
      </header>

      {loading && <p>Chargement...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && (
        <>
          <section className="patient-card">
            <h2>Informations patient</h2>
            <p><strong>Nom:</strong> {patientName}</p>
            <p><strong>Email:</strong> Non disponible</p>
            <p><strong>Âge:</strong> {patient?.age ?? 'Non renseigné'}</p>
            <p><strong>Genre:</strong> {patient?.gender || 'Non renseigné'}</p>
          </section>

          <section className="patient-card">
            <h2>Historique des rendez-vous</h2>
            {appointments.length === 0 && <p>Aucun rendez-vous pour ce patient.</p>}
            <ul className="history-list">
              {appointments.map((appointment) => {
                const statusMeta = getStatusMeta(appointment.status);
                return (
                  <li key={appointment.id}>
                    <p>
                      {new Date(appointment.date).toLocaleString('fr-FR')} · {appointment.duration_minutes} min · {formatGNF(appointment.price)}
                    </p>
                    <span className={statusMeta.className}>{statusMeta.label}</span>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="patient-card">
            <h2>Notes médecin</h2>
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
