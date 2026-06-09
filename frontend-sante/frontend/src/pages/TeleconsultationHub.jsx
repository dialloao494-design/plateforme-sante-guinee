import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { appointmentsAPI, teleconsultationAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatApiError } from '../utils/apiError.js';
import { getConsultationTypeLabel } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort, formatRelativeDay } from '../utils/formatDateTime.js';
import { getRoleHomePath } from '../utils/rolePaths.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import PageSkeleton from '../components/ui/PageSkeleton.jsx';
import './TeleconsultationHub.css';

export default function TeleconsultationHub() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [roomStatuses, setRoomStatuses] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await appointmentsAPI.getAll();
        if (cancelled) return;
        const list = Array.isArray(data) ? data : [];
        setAppointments(list);

        const teleOnly = list.filter((a) => a.consultation_type === 'teleconsultation');
        const statusEntries = await Promise.all(
          teleOnly.map(async (a) => {
            try {
              const { data: status } = await teleconsultationAPI.getRoomStatus(a.id);
              return [a.id, status];
            } catch {
              return [a.id, null];
            }
          })
        );
        if (!cancelled) {
          setRoomStatuses(Object.fromEntries(statusEntries));
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
        roomStatus: roomStatuses[a.id] || null,
        date: new Date(a.date),
      }))
      .filter((row) => row.date >= now || row.roomStatus?.can_join || row.roomStatus?.reason === 'too_early')
      .sort((a, b) => a.date - b.date);
  }, [appointments, roomStatuses]);

  const homeHref = useMemo(() => getRoleHomePath(user?.role), [user?.role]);

  const title =
    user?.role === 'doctor' || user?.role === 'admin' ? 'Téléconsultations à venir' : 'Vos téléconsultations';

  return (
    <div className="tele-hub ds-page">
      <header className="tele-hub-header">
        <div>
          <h1>{title}</h1>
          <p>Rejoignez la salle vidéo intégrée au moment prévu — directement dans l’application, sans ouvrir un nouvel onglet.</p>
        </div>
        <Link to={homeHref} className="btn btn-secondary tele-hub-back">
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
          preset="video"
          title="Aucune téléconsultation à venir"
          description="Réservez un rendez-vous en choisissant « Téléconsultation » pour le voir apparaître ici, avec le lien sécurisé le jour J."
          actionLabel={
            user?.role === 'patient'
              ? 'Prendre rendez-vous'
              : user?.role === 'doctor' || user?.role === 'admin'
                ? 'Agenda clinique'
                : undefined
          }
          onAction={
            user?.role === 'patient'
              ? () => navigate('/appointments')
              : user?.role === 'doctor' || user?.role === 'admin'
                ? () => navigate(homeHref)
                : undefined
          }
        />
      )}

      {!loading && teleRows.length > 0 && (
        <ul className="tele-hub-list">
          {teleRows.map(({ appointment: a, roomStatus }) => {
            const name =
              user?.role === 'doctor' || user?.role === 'admin'
                ? `${a.patient?.first_name || ''} ${a.patient?.last_name || ''}`.trim() || 'Patient'
                : a.doctor?.name || `Médecin #${a.doctor_id}`;

            const canOpenRoom = roomStatus?.can_join || roomStatus?.reason === 'too_early';
            const waitLabel =
              roomStatus?.reason === 'too_early'
                ? roomStatus.message
                : roomStatus?.can_join === false
                  ? roomStatus?.message || 'Indisponible'
                  : 'Disponible après confirmation';

            return (
              <li key={a.id} className="tele-hub-card">
                <div className="tele-hub-card-main">
                  <p className="tele-hub-name">{name}</p>
                  <p className="tele-hub-when">
                    {formatRelativeDay(a.date)} · {formatDateTimeShort(a.date)}
                  </p>
                  <p className="tele-hub-type">{getConsultationTypeLabel(a)}</p>
                  {roomStatus?.message && !canOpenRoom && (
                    <span className="tele-hub-wait">{roomStatus.message}</span>
                  )}
                </div>
                <div className="tele-hub-card-actions">
                  {canOpenRoom ? (
                    <button type="button" className="btn btn-primary" onClick={() => navigate(`/consultation/${a.id}`)}>
                      Ouvrir la salle
                    </button>
                  ) : (
                    <span className="tele-hub-wait">{waitLabel}</span>
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
