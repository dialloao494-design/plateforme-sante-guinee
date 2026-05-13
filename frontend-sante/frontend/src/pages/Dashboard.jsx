import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAppointmentContext } from '../contexts/AppointmentContext.jsx';
import AppointmentCard from '../components/AppointmentCard.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import { getAppointmentActions, getAppointmentState, isPendingAppointment } from '../utils/appointmentPresentation.js';
import './Dashboard.css';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { appointments, loading, error, updateAppointment, fetchAppointments } = useAppointmentContext();
  const [confirmingId, setConfirmingId] = useState(null);
  const role = user?.role;
  const previewAppointments = appointments.slice(0, 3);
  const viewerRole = role === 'doctor' || role === 'admin' ? role : 'patient';

  const stats = useMemo(() => {
    const now = new Date();
    const upcoming = appointments.filter((a) => {
      if (String(a.status || '').toLowerCase() === 'cancelled') return false;
      return new Date(a.date) >= now;
    }).length;
    const past = appointments.filter((a) => new Date(a.date) < now).length;
    const tele = appointments.filter((a) => a.consultation_type === 'teleconsultation').length;
    const actionNeeded = appointments.filter(
      (a) => isPendingAppointment(a) && String(a.payment_status || '').toLowerCase() === 'paid'
    ).length;
    return { upcoming, past, tele, actionNeeded };
  }, [appointments]);

  const handleConfirmAppointment = async (item) => {
    if (!item?.id) return;
    setConfirmingId(item.id);
    try {
      await updateAppointment(item.id, 'confirmed');
    } finally {
      setConfirmingId(null);
    }
  };

  const getPreviewTitle = (appointment) => {
    if (role === 'doctor' || role === 'admin') {
      return appointment?.patient?.first_name || 'Patient';
    }
    if (appointment?.doctor?.name) {
      return appointment.doctor.name;
    }
    return `Dr #${appointment?.doctor_id || '-'}`;
  };

  const isPatient = role === 'patient';

  return (
    <div className="dashboard ds-page">
      <header className="dashboard-hero">
        <div>
          <p className="dashboard-eyebrow">Espace connecté</p>
          <h1 className="dashboard-title">Tableau de bord</h1>
          <p className="dashboard-sub">
            {user?.email ? (
              <>
                Connecté en tant que <strong>{user.email}</strong>
                {role ? (
                  <>
                    {' '}
                    · <span className="dashboard-role-pill">{role}</span>
                  </>
                ) : null}
              </>
            ) : (
              'Chargement du profil…'
            )}
          </p>
        </div>
      </header>

      {error && (
        <div className="dashboard-banner dashboard-banner--error" role="alert">
          <span>{error}</span>
          <button type="button" className="btn btn-secondary dashboard-retry-btn" onClick={() => fetchAppointments()}>
            Réessayer
          </button>
        </div>
      )}

      {loading && <PageSkeleton lines={5} />}

      {!loading && isPatient && (
        <section className="dashboard-stats" aria-label="Indicateurs rapides">
          <article className="dashboard-stat-card">
            <h3>À venir</h3>
            <p>{stats.upcoming}</p>
            <span className="dashboard-stat-hint">Rendez-vous actifs</span>
          </article>
          <article className="dashboard-stat-card">
            <h3>Historique</h3>
            <p>{stats.past}</p>
            <span className="dashboard-stat-hint">Consultations passées</span>
          </article>
          <article className="dashboard-stat-card">
            <h3>Téléconsultation</h3>
            <p>{stats.tele}</p>
            <span className="dashboard-stat-hint">Lieu ou visio</span>
          </article>
          <article className="dashboard-stat-card dashboard-stat-card--accent">
            <h3>À confirmer</h3>
            <p>{stats.actionNeeded}</p>
            <span className="dashboard-stat-hint">Payés, en attente du médecin</span>
          </article>
        </section>
      )}

      <div className="dashboard-actions">
        <Link to="/notifications" className="action-button action-button--ghost">
          Notifications
        </Link>
        {role === 'patient' && (
          <>
            <Link to="/appointments" className="action-button">
              Mes rendez-vous
            </Link>
            <Link to="/teleconsultation" className="action-button action-button--ghost">
              Téléconsultation
            </Link>
            <button type="button" className="action-button" onClick={() => navigate('/doctors')}>
              Trouver un médecin
            </button>
          </>
        )}
        {role === 'doctor' && (
          <>
            <Link
              to={user?.doctor_id ? `/doctors/${user.doctor_id}` : '/doctors'}
              className="action-button"
            >
              Ma fiche publique
            </Link>
            <Link to="/doctor/dashboard" className="action-button">
              Agenda clinique
            </Link>
            <Link to="/teleconsultation" className="action-button action-button--ghost">
              Téléconsultation
            </Link>
          </>
        )}
        {role === 'admin' && (
          <>
            <Link to="/doctor/dashboard" className="action-button">
              Vue médecin
            </Link>
            <Link to="/users" className="action-button">
              Utilisateurs
            </Link>
            <Link to="/appointments" className="action-button">
              Tous les rendez-vous
            </Link>
            <Link to="/doctors" className="action-button">
              Médecins
            </Link>
          </>
        )}
        {!role && (
          <>
            <Link to="/doctors" className="action-button">
              Annuaire des médecins
            </Link>
            <Link to="/appointments" className="action-button">
              Mes rendez-vous
            </Link>
          </>
        )}
      </div>

      {!loading && appointments.length === 0 && isPatient && (
        <EmptyState
          preset="calendar"
          title="Aucun rendez-vous pour le moment"
          description="Prenez rendez-vous avec un praticien à Conakry, Kindia ou en téléconsultation. Vos prochains soins apparaîtront ici."
          actionLabel="Prendre rendez-vous"
          onAction={() => navigate('/appointments')}
        />
      )}

      {!loading && previewAppointments.length > 0 && (
        <section className="dashboard-preview">
          <div className="dashboard-preview-head">
            <h3>Prochains rendez-vous</h3>
            <Link to="/appointments" className="dashboard-preview-link">
              Voir tout
            </Link>
          </div>
          <ul className="dashboard-preview-list">
            {previewAppointments.map((appointment) => {
              const presentation = getAppointmentState(appointment);
              const actions = getAppointmentActions(appointment, { viewerRole });
              return (
                <AppointmentCard
                  key={appointment.id}
                  appointment={appointment}
                  title={getPreviewTitle(appointment)}
                  onPay={() => {}}
                  onConfirm={handleConfirmAppointment}
                  onCancel={() => {}}
                  onOpenMessages={(item) => navigate(`/messages/${item.id}`)}
                  onJoinConsultation={(item) => navigate(`/consultation/${item.id}`)}
                  presentation={presentation}
                  actions={actions}
                  isPaying={confirmingId === appointment.id}
                  isCancelling={false}
                />
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
