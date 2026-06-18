import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { appointmentsAPI, messagesAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import AppointmentActions from '../components/AppointmentActions.jsx';
import {
  getAppointmentState,
  getAppointmentActions,
  isPendingAppointment,
} from '../utils/appointmentPresentation.js';
import './DoctorDashboard.css';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';

const DoctorDashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recentMessages, setRecentMessages] = useState([]);
  const [confirmingId, setConfirmingId] = useState(null);

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

  const loadAppointments = useCallback(async () => {
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
  }, []);

  const handleConfirmAppointment = async (item) => {
    if (!item?.id) return;
    setConfirmingId(item.id);
    try {
      await appointmentsAPI.updateStatus(item.id, 'confirmed');
      await loadAppointments();
    } catch (err) {
      setError(getApiErrorMessage(err, 'Impossible de confirmer le rendez-vous.'));
    } finally {
      setConfirmingId(null);
    }
  };

  useEffect(() => {
    void loadAppointments();
  }, [loadAppointments]);

  const todayCount = useMemo(() => {
    const now = new Date();
    return appointments.filter((appointment) => new Date(appointment.date).toDateString() === now.toDateString()).length;
  }, [appointments]);

  const pendingCount = useMemo(
    () => appointments.filter((appointment) => isPendingAppointment(appointment)).length,
    [appointments]
  );

  const awaitingConfirm = pendingCount;

  const teleconsultSoon = useMemo(() => {
    const now = new Date();
    const horizon = new Date(now);
    horizon.setDate(horizon.getDate() + 14);
    return appointments.filter((appointment) => {
      if (appointment.consultation_type !== 'teleconsultation') return false;
      if (String(appointment.status || '').toLowerCase() === 'cancelled') return false;
      const d = new Date(appointment.date);
      return d >= now && d <= horizon;
    }).length;
  }, [appointments]);

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
    <div className="doctor-dashboard-page ds-page">
      <div className="doctor-dashboard-card">
        <p className="doctor-dashboard-eyebrow">Vue clinique</p>
        <h1>Tableau de bord médecin</h1>
        <p className="doctor-dashboard-lead">
          Bonjour{user?.email ? ` — ${user.email}` : ''}. Anticipez les confirmations, la téléconsultation et la
          messagerie sécurisée depuis un seul écran.
        </p>

        {location.state?.clinicRequired && (
          <p className="error" role="alert">
            Votre compte n&apos;est pas rattaché à une clinique CIS. Les modules hospitaliers sont réservés au personnel
            de clinique — contactez l&apos;administrateur pour une affectation.
          </p>
        )}

        {loading && <PageSkeleton lines={4} />}
        {error && <p className="error">{error}</p>}

        {!loading && !error && (
          <>
            <div className="doctor-summary-grid">
              <article className="summary-card">
                <h3>Agenda total</h3>
                <p>{appointments.length}</p>
                <span className="summary-card-hint">Tous statuts</span>
              </article>
              <article className="summary-card summary-card--accent">
                <h3>Aujourd’hui</h3>
                <p>{todayCount}</p>
                <span className="summary-card-hint">Créneaux du jour</span>
              </article>
              <article className="summary-card summary-card--warn">
                <h3>À confirmer</h3>
                <p>{awaitingConfirm}</p>
                <span className="summary-card-hint">Rendez-vous en attente</span>
              </article>
              <article className="summary-card">
                <h3>File &amp; téléconsult.</h3>
                <p>
                  {pendingCount} / {teleconsultSoon}
                </p>
                <span className="summary-card-hint">En attente · téléconsult. 14 j.</span>
              </article>
            </div>

            <div className="doctor-sections">
              <section className="doctor-section-card">
                <div className="section-head">
                  <h2>Prochains rendez-vous</h2>
                  <div className="section-head-links">
                    <Link to="/teleconsultation" className="button-secondary">Téléconsultation</Link>
                    <Link to="/doctor/appointments" className="button-secondary">Voir tout</Link>
                  </div>
                </div>
                {upcomingAppointments.length === 0 && (
                  <EmptyState
                    preset="calendar"
                    title="Aucun rendez-vous à venir"
                    description="Lorsque des patients réservent, ils apparaissent ici avec leur statut et les actions possibles."
                    actionLabel="Ouvrir l’agenda détaillé"
                    onAction={() => navigate('/doctor/appointments')}
                  />
                )}
                <ul className="compact-appointments">
                  {upcomingAppointments.map((appointment) => {
                    const presentation = getAppointmentState(appointment);
                    const actions = getAppointmentActions(appointment, { viewerRole: 'doctor' });
                    const isToday = new Date(appointment.date).toDateString() === new Date().toDateString();
                    return (
                      <li key={appointment.id} className={isToday ? 'urgent' : ''}>
                        <div>
                          <p className="row-title">{appointment?.patient?.first_name || 'Patient'} {appointment?.patient?.last_name || ''}</p>
                          <p>{new Date(appointment.date).toLocaleString('fr-FR')}</p>
                        </div>
                        <div className="row-actions">
                          <span className={presentation.statusColor}>{presentation.displayStatus}</span>
                          <AppointmentActions
                            actions={actions}
                            appointment={appointment}
                            onPay={() => {}}
                            onConfirm={handleConfirmAppointment}
                            onCancel={() => {}}
                            onOpenMessages={() => navigate(`/messages/${appointment.id}`)}
                            onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
                            isPaying={confirmingId === appointment.id}
                            isCancelling={false}
                          />
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
                {patientsPreview.length === 0 && (
                  <EmptyState
                    preset="people"
                    title="Aucun dossier patient récent"
                    description="Les patients liés à vos rendez-vous apparaîtront ici pour un accès rapide au dossier."
                    actionLabel="Voir tous les patients"
                    onAction={() => navigate('/patients')}
                  />
                )}
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
                {recentMessages.length === 0 && (
                  <EmptyState
                    preset="messages"
                    title="Pas encore d’échanges récents"
                    description="Les dernières réponses patients sur vos rendez-vous s’affichent ici pour prioriser les urgences."
                    actionLabel="Ouvrir la messagerie"
                    onAction={() => navigate('/doctor/messages')}
                  />
                )}
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
