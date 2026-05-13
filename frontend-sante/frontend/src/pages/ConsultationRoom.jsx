import { useCallback, useEffect, useMemo, useState, startTransition } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { appointmentsAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatApiError } from '../utils/apiError.js';
import { getAppointmentState } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort, formatRelativeDay } from '../utils/formatDateTime.js';
import {
  getProviderDisplayLabel,
  resolveRoomProvider,
} from '../services/teleconsultationProvider.js';
import './ConsultationRoom.css';

const STATUS = {
  loading: 'loading',
  prejoin: 'prejoin',
  connecting: 'connecting',
  live: 'live',
  ended: 'ended',
  error: 'error',
};

export default function ConsultationRoom() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [roomStatus, setRoomStatus] = useState(STATUS.loading);
  const [appointment, setAppointment] = useState(null);
  const [error, setError] = useState('');
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);

  const load = useCallback(async () => {
    setRoomStatus(STATUS.loading);
    setError('');
    try {
      const { data } = await appointmentsAPI.getById(appointmentId);
      setAppointment(data);
      const state = getAppointmentState(data);
      if (data.consultation_type !== 'teleconsultation') {
        setError('Ce rendez-vous n’est pas une téléconsultation.');
        setRoomStatus(STATUS.error);
        return;
      }
      if (!state.canJoin) {
        setError('Cette téléconsultation n’est pas encore disponible (statut ou horaire).');
        setRoomStatus(STATUS.error);
        return;
      }
      setRoomStatus(STATUS.prejoin);
    } catch (err) {
      setError(formatApiError(err, 'Impossible de charger le rendez-vous.'));
      setRoomStatus(STATUS.error);
    }
  }, [appointmentId]);

  useEffect(() => {
    startTransition(() => {
      void load();
    });
  }, [load]);

  const provider = useMemo(
    () => resolveRoomProvider({ meetingUrl: appointment?.meeting_link, appointmentId }),
    [appointment, appointmentId]
  );

  const providerLabel = useMemo(() => getProviderDisplayLabel(provider), [provider]);

  const enterRoom = () => {
    setRoomStatus(STATUS.connecting);
    window.setTimeout(() => setRoomStatus(STATUS.live), 900);
  };

  const endSession = () => {
    setRoomStatus(STATUS.ended);
  };

  const openExternal = () => {
    const url = appointment?.meeting_link;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const counterpartLabel = useMemo(() => {
    if (!appointment) return '';
    if (user?.role === 'doctor' || user?.role === 'admin') {
      const p = appointment.patient;
      return `${p?.first_name || ''} ${p?.last_name || ''}`.trim() || 'Patient';
    }
    return appointment?.doctor?.name || `Médecin #${appointment?.doctor_id ?? ''}`;
  }, [appointment, user]);

  const flowStep =
    roomStatus === STATUS.error
      ? 1
      : roomStatus === STATUS.loading
        ? 0
        : roomStatus === STATUS.prejoin || roomStatus === STATUS.connecting
          ? 1
          : roomStatus === STATUS.live
            ? 2
            : roomStatus === STATUS.ended
              ? 3
              : 0;

  const flowLabels = ['Salle d’attente', 'Préparation', 'Consultation', 'Clôture'];

  return (
    <div className="consult-room">
      <header className="consult-room-header">
        <div>
          <p className="consult-room-eyebrow">Téléconsultation</p>
          <h1 className="consult-room-title">Salle de consultation</h1>
          {appointment && (
            <p className="consult-room-meta">
              {counterpartLabel} · {formatRelativeDay(appointment.date)} · {formatDateTimeShort(appointment.date)}
            </p>
          )}
        </div>
        <div className="consult-room-header-actions">
          {appointment?.id && (
            <Link to={`/messages/${appointment.id}`} className="btn btn-secondary consult-room-link">
              Messages
            </Link>
          )}
          <Link to="/teleconsultation" className="btn btn-secondary consult-room-link">
            Quitter
          </Link>
        </div>
      </header>

      <ol className="consult-flow" aria-label="Étapes de la téléconsultation">
        {flowLabels.map((label, i) => (
          <li
            key={label}
            className={`consult-flow-step ${i < flowStep ? 'is-past' : ''} ${i === flowStep ? 'is-current' : ''}`}
          >
            <span className="consult-flow-dot" aria-hidden />
            <span className="consult-flow-label">{label}</span>
          </li>
        ))}
      </ol>

      {error && (
        <div className="consult-room-banner consult-room-banner--error" role="alert">
          {error}
          <button type="button" className="btn btn-secondary consult-room-retry" onClick={() => load()}>
            Réessayer
          </button>
        </div>
      )}

      {roomStatus === STATUS.loading && (
        <div className="consult-room-loading page-loading" role="status">
          <span className="app-spinner" aria-hidden />
          <span>Préparation de la salle…</span>
        </div>
      )}

      {(roomStatus === STATUS.prejoin || roomStatus === STATUS.connecting) && appointment && (
        <section className="consult-prejoin" aria-labelledby="prejoin-title">
          <h2 id="prejoin-title" className="visually-hidden">
            Avant d’entrer
          </h2>
          <div className="consult-prejoin-grid">
            <div className="consult-device-card">
              <div className={`consult-device-preview ${camOn ? 'on' : 'off'}`}>
                <span className="consult-device-placeholder">{camOn ? 'Caméra (aperçu)' : 'Caméra désactivée'}</span>
              </div>
              <div className="consult-device-toggles">
                <button
                  type="button"
                  className={`consult-toggle ${micOn ? 'is-on' : ''}`}
                  onClick={() => setMicOn((v) => !v)}
                  aria-pressed={micOn}
                >
                  Micro {micOn ? 'activé' : 'coupé'}
                </button>
                <button
                  type="button"
                  className={`consult-toggle ${camOn ? 'is-on' : ''}`}
                  onClick={() => setCamOn((v) => !v)}
                  aria-pressed={camOn}
                >
                  Caméra {camOn ? 'activée' : 'coupée'}
                </button>
              </div>
            </div>
            <div className="consult-prejoin-side">
              <p className="consult-provider-pill">
                Fournisseur cible : <strong>{providerLabel}</strong>
              </p>
              <p className="consult-prejoin-copy">
                La vidéo réelle sera fournie par Daily.co, Jitsi ou Twilio Video selon la configuration du cabinet.
                Activez le micro et la caméra uniquement lorsque vous êtes prêt.
              </p>
              {appointment.meeting_link && (
                <button type="button" className="btn btn-secondary consult-external" onClick={openExternal}>
                  Ouvrir le lien fournisseur dans un nouvel onglet
                </button>
              )}
              <button
                type="button"
                className="btn btn-primary consult-join-main"
                disabled={roomStatus === STATUS.connecting}
                onClick={enterRoom}
              >
                {roomStatus === STATUS.connecting ? 'Connexion…' : 'Entrer dans la salle'}
              </button>
            </div>
          </div>
        </section>
      )}

      {roomStatus === STATUS.live && (
        <section className="consult-live" aria-label="Salle de téléconsultation">
          <div className="consult-live-grid">
            <div className="consult-video-main">
              <span>Flux vidéo principal</span>
              <small>Intégration SDK à brancher ({providerLabel})</small>
            </div>
            <div className="consult-video-pip">
              <span>Votre aperçu</span>
            </div>
          </div>
          <div className="consult-live-toolbar">
            <button type="button" className="consult-toolbar-btn" onClick={() => setMicOn((v) => !v)}>
              Micro {micOn ? 'on' : 'off'}
            </button>
            <button type="button" className="consult-toolbar-btn" onClick={() => setCamOn((v) => !v)}>
              Cam {camOn ? 'on' : 'off'}
            </button>
            {appointment?.meeting_link && (
              <button type="button" className="consult-toolbar-btn" onClick={openExternal}>
                Lien externe
              </button>
            )}
            <button type="button" className="consult-toolbar-btn consult-toolbar-btn--danger" onClick={endSession}>
              Terminer
            </button>
          </div>
        </section>
      )}

      {roomStatus === STATUS.ended && (
        <div className="consult-ended">
          <h2>Consultation terminée</h2>
          <p>Vous pouvez fermer cette page ou retourner au tableau de bord.</p>
          <button type="button" className="btn btn-primary" onClick={() => navigate('/dashboard')}>
            Tableau de bord
          </button>
        </div>
      )}
    </div>
  );
}
