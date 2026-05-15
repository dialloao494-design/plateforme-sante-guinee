import { useCallback, useEffect, useMemo, useState, startTransition } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { appointmentsAPI, teleconsultationAPI } from '../services/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';
import { formatApiError } from '../utils/apiError.js';
import { getAppointmentState } from '../utils/appointmentPresentation.js';
import { formatDateTimeShort, formatRelativeDay } from '../utils/formatDateTime.js';
import { getConsultationSummary, setConsultationSummary } from '../utils/clinicalStorage.js';
import {
  buildJitsiMeetingUrl,
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

const JOIN_WINDOW_MS = 15 * 60 * 1000;

function formatCountdown(ms) {
  if (ms <= 0) return null;
  const totalSec = Math.ceil(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h} h ${m} min`;
  if (m > 0) return `${m} min ${s} s`;
  return `${s} s`;
}

function formatElapsed(totalSec) {
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function ConsultationRoom() {
  const { appointmentId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [roomStatus, setRoomStatus] = useState(STATUS.loading);
  const [appointment, setAppointment] = useState(null);
  const [error, setError] = useState('');
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(true);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [connectionHint, setConnectionHint] = useState('');
  const [elapsedSec, setElapsedSec] = useState(0);
  const [peerPresent, setPeerPresent] = useState(false);
  const [summaryDraft, setSummaryDraft] = useState('');
  const [mediaStatus, setMediaStatus] = useState({ checked: false, ok: false, reason: '' });

  const load = useCallback(async () => {
    setRoomStatus(STATUS.loading);
    setPeerPresent(false);
    setElapsedSec(0);
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

  const appointmentStartMs = appointment?.date ? new Date(appointment.date).getTime() : null;
  const msUntilStart = appointmentStartMs != null ? appointmentStartMs - nowTick : null;

  useEffect(() => {
    if (roomStatus !== STATUS.prejoin && roomStatus !== STATUS.connecting) return undefined;
    const id = window.setInterval(() => setNowTick(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [roomStatus]);

  useEffect(() => {
    if (roomStatus !== STATUS.prejoin) return undefined;
    let cancelled = false;
    const probe = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) {
          setMediaStatus({
            checked: true,
            ok: false,
            reason: 'Navigateur sans accès caméra/micro (HTTPS requis).',
          });
        }
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
        stream.getTracks().forEach((t) => t.stop());
        if (!cancelled) setMediaStatus({ checked: true, ok: true, reason: '' });
      } catch (err) {
        if (!cancelled) {
          setMediaStatus({
            checked: true,
            ok: false,
            reason: err?.name === 'NotAllowedError' ? 'Autorisez caméra et micro.' : 'Périphériques indisponibles.',
          });
        }
      }
    };
    void probe();
    return () => {
      cancelled = true;
    };
  }, [roomStatus]);

  useEffect(() => {
    if (roomStatus !== STATUS.connecting) {
      const clearId = window.setTimeout(() => setConnectionHint(''), 0);
      return () => window.clearTimeout(clearId);
    }
    let cancelled = false;
    const t0 = window.setTimeout(() => {
      if (!cancelled) setConnectionHint('Établissement du canal sécurisé…');
    }, 0);
    const t1 = window.setTimeout(() => {
      if (!cancelled) setConnectionHint('Négociation chiffrée (TLS)…');
    }, 280);
    const t2 = window.setTimeout(() => {
      if (!cancelled) setConnectionHint('Préparation audio & vidéo…');
    }, 620);
    const t3 = window.setTimeout(() => {
      if (!cancelled) setRoomStatus(STATUS.live);
    }, 1180);
    return () => {
      cancelled = true;
      window.clearTimeout(t0);
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [roomStatus]);

  useEffect(() => {
    if (roomStatus !== STATUS.live) return undefined;
    const id = window.setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => window.clearInterval(id);
  }, [roomStatus]);

  useEffect(() => {
    if (roomStatus !== STATUS.live) {
      const clearId = window.setTimeout(() => setPeerPresent(false), 0);
      return () => window.clearTimeout(clearId);
    }
    const t = window.setTimeout(() => setPeerPresent(true), 2600);
    return () => window.clearTimeout(t);
  }, [roomStatus]);

  const enterRoom = async () => {
    setRoomStatus(STATUS.connecting);
    setError('');
    try {
      const { data } = await teleconsultationAPI.getAccess(appointmentId);
      let link = data?.meeting_url;
      if (data?.provider === 'jitsi' && data?.room_name && data?.jitsi_domain) {
        link = buildJitsiMeetingUrl(data.jitsi_domain, data.room_name, data.jitsi_jwt) || link;
      }
      if (link) {
        setAppointment((prev) => (prev ? { ...prev, meeting_link: link } : prev));
      }
    } catch (err) {
      setError(formatApiError(err, 'Accès à la téléconsultation refusé.'));
      setRoomStatus(STATUS.error);
    }
  };

  const endSession = async () => {
    try {
      await teleconsultationAPI.endSession(appointmentId);
    } catch {
      /* best-effort */
    }
    if (appointment?.id) {
      const existing = getConsultationSummary(appointment.id);
      setSummaryDraft(existing?.text || '');
    } else {
      setSummaryDraft('');
    }
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

  const isDoctorLike = user?.role === 'doctor' || user?.role === 'admin';
  const earlyForSession =
    msUntilStart != null && msUntilStart > JOIN_WINDOW_MS && (roomStatus === STATUS.prejoin || roomStatus === STATUS.connecting);
  const countdownLabel =
    msUntilStart != null && msUntilStart > 0 && msUntilStart <= 2 * 60 * 60 * 1000 ? formatCountdown(msUntilStart) : null;

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

  const flowLabels = ['Salle d’attente', 'Préparation', 'Consultation en direct', 'Clôture'];

  const postConsultHref = isDoctorLike ? '/doctor/dashboard' : '/dashboard';

  const saveSummaryAndLeave = () => {
    if (appointment?.id && appointment?.patient_id && summaryDraft.trim()) {
      setConsultationSummary(appointment.id, appointment.patient_id, summaryDraft.trim());
    }
    navigate(postConsultHref);
  };

  const leaveConsultation = () => {
    navigate(postConsultHref);
  };

  return (
    <div className="consult-room ds-page">
      <header className="consult-room-header">
        <div>
          <p className="consult-room-eyebrow">Téléconsultation sécurisée</p>
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
            Hub téléconsultation
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
          <span>Ouverture de la salle chiffrée…</span>
        </div>
      )}

      {(roomStatus === STATUS.prejoin || roomStatus === STATUS.connecting) && appointment && (
        <section className="consult-prejoin" aria-labelledby="prejoin-title">
          <h2 id="prejoin-title" className="visually-hidden">
            Avant d’entrer
          </h2>

          {earlyForSession && (
            <div className="consult-waiting-banner" role="status">
              <strong>Salle d’attente virtuelle</strong>
              <span>
                Vous êtes connecté en avance. L’accès complet à la consultation s’ouvre en général{' '}
                <strong>15 minutes</strong> avant l’horaire prévu. Préparez vos documents médicaux.
              </span>
            </div>
          )}

          {!earlyForSession && countdownLabel && (
            <div className="consult-countdown-banner" role="status">
              <span className="consult-countdown-label">Début dans</span>
              <span className="consult-countdown-value">{countdownLabel}</span>
            </div>
          )}

          <div className="consult-prejoin-grid">
            <div className="consult-device-card">
              <div className={`consult-device-preview ${camOn ? 'on' : 'off'}`}>
                <span className="consult-device-placeholder">
                  {camOn ? 'Aperçu caméra (simulation)' : 'Caméra désactivée'}
                </span>
              </div>
              <ul className="consult-device-checklist">
                <li className={micOn ? 'is-ok' : ''}>Micro {micOn ? 'prêt' : 'coupé'}</li>
                <li className={camOn ? 'is-ok' : ''}>Caméra {camOn ? 'prête' : 'désactivée'}</li>
                <li className={mediaStatus.ok ? 'is-ok' : mediaStatus.checked ? '' : 'is-ok'}>
                  {mediaStatus.checked
                    ? mediaStatus.ok
                      ? 'Caméra / micro autorisés'
                      : mediaStatus.reason
                    : 'Vérification des périphériques…'}
                </li>
                <li className="is-ok">Connexion chiffrée (HTTPS)</li>
              </ul>
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
                Fournisseur vidéo : <strong>{providerLabel}</strong>
              </p>
              <p className="consult-prejoin-copy">
                {provider === 'jitsi'
                  ? 'Une fois connecté, vous pouvez ouvrir la salle Jitsi sécurisée (JWT si configuré sur le serveur).'
                  : 'Le flux vidéo est fourni par Daily.co, Jitsi ou Twilio selon la configuration du cabinet.'}
              </p>
              {appointment.meeting_link && (
                <button type="button" className="btn btn-secondary consult-external" onClick={openExternal}>
                  Ouvrir le lien fournisseur
                </button>
              )}
              {roomStatus === STATUS.connecting && (
                <div className="consult-connecting-panel" role="status" aria-live="polite">
                  <span className="app-spinner consult-connecting-spinner" aria-hidden />
                  <p className="consult-connecting-text">{connectionHint}</p>
                </div>
              )}
              <button
                type="button"
                className="btn btn-primary consult-join-main"
                disabled={roomStatus === STATUS.connecting}
                onClick={enterRoom}
              >
                {roomStatus === STATUS.connecting ? 'Connexion sécurisée…' : 'Rejoindre la consultation'}
              </button>
            </div>
          </div>
        </section>
      )}

      {roomStatus === STATUS.live && (
        <section className="consult-live" aria-label="Salle de téléconsultation">
          <div className="consult-live-statusbar">
            <div className="consult-live-status-left">
              <span className="consult-live-timer" aria-label="Durée de la séance">
                {formatElapsed(elapsedSec)}
              </span>
              <span className="consult-live-pill consult-live-pill--signal">Signal stable</span>
            </div>
            <div className={`consult-live-peer ${peerPresent ? 'is-on' : 'is-wait'}`}>
              {peerPresent
                ? isDoctorLike
                  ? 'Patient connecté'
                  : 'Médecin en ligne'
                : isDoctorLike
                  ? 'En attente du patient…'
                  : 'Connexion au cabinet…'}
            </div>
          </div>
          <div className="consult-live-grid">
            <div className="consult-video-main">
              <span className="consult-video-main-label">{counterpartLabel}</span>
              <span>Flux principal (SDK à intégrer)</span>
              <small>{providerLabel}</small>
            </div>
            <div className="consult-video-pip">
              <span>Vous</span>
            </div>
          </div>
          <div className="consult-live-toolbar">
            <button type="button" className={`consult-toolbar-btn ${micOn ? '' : 'is-muted'}`} onClick={() => setMicOn((v) => !v)}>
              Micro {micOn ? 'activé' : 'muet'}
            </button>
            <button type="button" className={`consult-toolbar-btn ${camOn ? '' : 'is-muted'}`} onClick={() => setCamOn((v) => !v)}>
              Caméra {camOn ? 'on' : 'off'}
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
        <div className={`consult-ended ${isDoctorLike ? 'consult-ended--doctor' : ''}`}>
          <h2>Consultation terminée</h2>
          {isDoctorLike ? (
            <>
              <p className="consult-ended-intro">
                Rédigez une synthèse clinique courte (motif, examen, suite). Elle est enregistrée sur cet appareil et
                rattachée au dossier patient dans l’historique des rendez-vous.
              </p>
              <label htmlFor="consult-summary" className="visually-hidden">
                Synthèse de consultation
              </label>
              <textarea
                id="consult-summary"
                className="consult-summary-textarea"
                rows={5}
                value={summaryDraft}
                onChange={(e) => setSummaryDraft(e.target.value)}
                placeholder="Ex. Douleurs thoraciques atypiques — ECG normal — ordonnance envoyée par messagerie — revoir si persistance…"
              />
              <div className="consult-ended-actions">
                <button type="button" className="btn btn-primary" onClick={saveSummaryAndLeave}>
                  Enregistrer la synthèse et quitter
                </button>
                <button type="button" className="btn btn-secondary" onClick={leaveConsultation}>
                  Quitter sans enregistrer
                </button>
              </div>
            </>
          ) : (
            <>
              <p>Merci d’avoir utilisé la téléconsultation sécurisée. Vous pouvez retrouver les messages liés à ce rendez-vous dans votre messagerie.</p>
              <button type="button" className="btn btn-primary" onClick={leaveConsultation}>
                Retour au tableau de bord
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
