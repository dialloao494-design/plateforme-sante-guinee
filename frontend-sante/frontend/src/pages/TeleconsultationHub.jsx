import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { appointmentsAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatApiError } from '../utils/apiError.js';
import { getAppointmentState, getConsultationTypeLabel } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort, formatRelativeDay } from '../utils/formatDateTime.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './TeleconsultationHub.css';

export default function TeleconsultationHub() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await appointmentsAPI.getAll();
        if (!cancelled) {
          setAppointments(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(formatApiError(err, 'Impossible de charger les rendez-vous.'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const teleRows = useMemo(() => {
    const now = new Date();
    return appointments
      .filter((a) => a.consultation_type === 'teleconsultation')
      .map((a) => ({
        appointment: a,
        state: getAppointmentState(a),
        date: new Date(a.date),
      }))
      .filter((row) => row.date >= now)
      .sort((a, b) => a.date - b.date);
  }, [appointments]);

  const title =
    user?.role === 'doctor' || user?.role === 'admin' ? 'Téléconsultations à venir' : 'Vos téléconsultations';

  return (
    <div className="tele-hub">
      <header className="tele-hub-header">
        <div>
          <h1>{title}</h1>
          <p>Rejoignez la salle sécurisée au moment prévu. Le flux vidéo réel sera activé par votre cabinet.</p>
        </div>
        <Link to="/dashboard" className="btn btn-secondary tele-hub-back">
          Tableau de bord
        </Link>
      </header>

      {loading && <PageSkeleton lines={5} />}

      {error && !loading && (
        <div className="tele-hub-error" role="alert">
          {error}
        </div>
      )}

      {!loading && !error && teleRows.length === 0 && (
        <EmptyState
          title="Aucune téléconsultation à venir"
          description="Réservez un rendez-vous en choisissant « Téléconsultation » pour le voir apparaître ici."
          actionLabel={user?.role === 'patient' ? 'Prendre rendez-vous' : undefined}
          onAction={user?.role === 'patient' ? () => navigate('/appointments') : undefined}
          icon="📹"
        />
      )}

      {!loading && teleRows.length > 0 && (
        <ul className="tele-hub-list">
          {teleRows.map(({ appointment: a, state }) => {
            const name =
              user?.role === 'doctor' || user?.role === 'admin'
                ? `${a.patient?.first_name || ''} ${a.patient?.last_name || ''}`.trim() || 'Patient'
                : a.doctor?.name || `Médecin #${a.doctor_id}`;

            return (
              <li key={a.id} className="tele-hub-card">
                <div className="tele-hub-card-main">
                  <p className="tele-hub-name">{name}</p>
                  <p className="tele-hub-when">
                    {formatRelativeDay(a.date)} · {formatDateTimeShort(a.date)}
                  </p>
                  <p className="tele-hub-type">{getConsultationTypeLabel(a)}</p>
                  <span className={state.statusColor}>{state.displayStatus}</span>
                </div>
                <div className="tele-hub-card-actions">
                  {state.canJoin ? (
                    <button type="button" className="btn btn-primary" onClick={() => navigate(`/consultation/${a.id}`)}>
                      Ouvrir la salle
                    </button>
                  ) : (
                    <span className="tele-hub-wait">Disponible après confirmation</span>
                  )}
                  <Link to={`/messages/${a.id}`} className="btn btn-secondary tele-hub-msg">
                    Messages
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
