import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { appointmentsAPI, messagesAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getStatusMeta } from '../utils/appointmentPresentation.js';
import './DoctorDashboard.css';

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recentMessages, setRecentMessages] = useState([]);

  const getApiErrorMessage = (err, fallback) => {
    if (!err?.response && /network|failed to fetch/i.test(String(err?.message || ''))) {
      return 'Erreur de connexion. Veuillez réessayer.';
    }

    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    return err?.message || fallback;
  };

  const loadAppointments = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await appointmentsAPI.getAll();
      const list = Array.isArray(data) ? data : [];
      setAppointments(list);

      // Build recent messages preview from the latest appointments.
      const latestAppointments = [...list]
        .sort((a, b) => new Date(b.date) - new Date(a.date))
        .slice(0, 6);

      const results = await Promise.all(
        latestAppointments.map(async (appointment) => {
          try {
            const response = await messagesAPI.getByAppointment(appointment.id);
            const conversation = Array.isArray(response.data) ? response.data : [];
            const last = conversation[conversation.length - 1];
            if (!last) return null;
            return {
              appointmentId: appointment.id,
              patientName: `${appointment?.patient?.first_name || 'Patient'} ${appointment?.patient?.last_name || ''}`.trim(),
              content: last.content || last.attachment_name || 'Pièce jointe',
              createdAt: last.created_at,
            };
          } catch {
            return null;
          }
        })
      );

      setRecentMessages(results.filter(Boolean).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)).slice(0, 5));
    } catch (err) {
      setError(getApiErrorMessage(err, 'Impossible de charger les rendez-vous.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  const todayCount = useMemo(() => {
    const now = new Date();
    return appointments.filter((appointment) => new Date(appointment.date).toDateString() === now.toDateString()).length;
  }, [appointments]);

  const pendingCount = useMemo(
    () => appointments.filter((appointment) => String(appointment.status || '').toLowerCase() === 'pending').length,
    [appointments]
  );

  const upcomingAppointments = useMemo(() => {
    const now = new Date();
    return appointments
      .filter((appointment) => new Date(appointment.date) >= now)
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(0, 6);
  }, [appointments]);

  const patientsPreview = useMemo(() => {
    const map = new Map();
    appointments.forEach((appointment) => {
      const patient = appointment?.patient;
      if (!patient?.id) return;
      if (!map.has(patient.id)) {
        map.set(patient.id, {
          id: patient.id,
          name: `${patient.first_name || 'Patient'} ${patient.last_name || ''}`.trim(),
          email: patient.email || '-',
        });
      }
    });
    return Array.from(map.values()).slice(0, 6);
  }, [appointments]);

  return (
    <div className="doctor-dashboard-page">
      <div className="doctor-dashboard-card">
        <h1>Tableau de bord médecin</h1>
        <p>Bienvenue Dr {user?.email || ''}. Suivez vos consultations et vos échanges patients.</p>

        {loading && <p>Chargement...</p>}
        {error && <p className="error">{error}</p>}

        {!loading && !error && (
          <>
            <div className="doctor-summary-grid">
              <article className="summary-card">
                <h3>Total rendez-vous</h3>
                <p>{appointments.length}</p>
              </article>
              <article className="summary-card">
                <h3>Aujourd'hui</h3>
                <p>{todayCount}</p>
              </article>
              <article className="summary-card">
                <h3>En attente</h3>
                <p>{pendingCount}</p>
              </article>
            </div>

            <div className="doctor-sections">
              <section className="doctor-section-card">
                <div className="section-head">
                  <h2>Prochains rendez-vous</h2>
                  <Link to="/doctor/appointments" className="button-secondary">Voir tout</Link>
                </div>
                {upcomingAppointments.length === 0 && <p>Aucun rendez-vous à venir.</p>}
                <ul className="compact-appointments">
                  {upcomingAppointments.map((appointment) => {
                    const statusMeta = getStatusMeta(appointment);
                    const isToday = new Date(appointment.date).toDateString() === new Date().toDateString();
                    return (
                      <li key={appointment.id} className={isToday ? 'urgent' : ''}>
                        <div>
                          <p className="row-title">{appointment?.patient?.first_name || 'Patient'} {appointment?.patient?.last_name || ''}</p>
                          <p>{new Date(appointment.date).toLocaleString('fr-FR')}</p>
                        </div>
                        <div className="row-actions">
                          <span className={statusMeta.className}>{statusMeta.label}</span>
                          <button className="button-secondary" onClick={() => navigate(`/messages/${appointment.id}`)}>Messages</button>
                          {appointment?.consultation_type === 'teleconsultation' && appointment?.meeting_link && (
                            <button
                              className="button-secondary"
                              onClick={() => window.open(appointment.meeting_link, '_blank', 'noopener,noreferrer')}
                            >
                              Rejoindre la consultation
                            </button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>

              <section className="doctor-section-card">
                <div className="section-head">
                  <h2>Patients</h2>
                  <Link to="/patients" className="button-secondary">Voir les patients</Link>
                </div>
                {patientsPreview.length === 0 && <p>Aucun patient.</p>}
                <ul className="patients-preview-list">
                  {patientsPreview.map((patient) => (
                    <li key={patient.id}>
                      <div>
                        <p className="row-title">{patient.name}</p>
                        <p>{patient.email}</p>
                      </div>
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={() => navigate(`/doctor/patient/${patient.id}`)}
                      >
                        Ouvrir
                      </button>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="doctor-section-card">
                <div className="section-head">
                  <h2>Messages récents</h2>
                  <Link to="/doctor/messages" className="button-secondary">Ouvrir la messagerie</Link>
                </div>
                {recentMessages.length === 0 && <p>Aucun message récent.</p>}
                <ul className="recent-messages-list">
                  {recentMessages.map((message) => (
                    <li key={`${message.appointmentId}-${message.createdAt}`}>
                      <button type="button" className="recent-message-btn" onClick={() => navigate(`/doctor/messages?appointmentId=${message.appointmentId}`)}>
                        <span className="row-title">{message.patientName}</span>
                        <span className="message-preview">{message.content}</span>
                        <small>{new Date(message.createdAt).toLocaleString('fr-FR')}</small>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DoctorDashboard;
