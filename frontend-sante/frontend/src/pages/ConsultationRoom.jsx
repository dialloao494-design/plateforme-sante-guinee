import { useCallback, useEffect, useMemo, useRef, useState, startTransition } from 'react';

import { Link, useNavigate, useParams } from 'react-router-dom';

import { teleconsultationAPI, patientRecordAPI } from '../services/api.js';

import httpClient from '../services/httpClient.js';

import { useAuth } from '../contexts/AuthContext.jsx';

import { formatApiError } from '../utils/apiError.js';

import { formatDateTimeShort, formatRelativeDay } from '../utils/formatDateTime.js';

import JitsiEmbeddedMeeting from '../components/JitsiEmbeddedMeeting.jsx';

import {

  buildEmbedFromAccess,

  getProviderDisplayLabel,

  mapMediaDeviceError,

  resolveRoomProvider,

} from '../services/teleconsultationProvider.js';

import './ConsultationRoom.css';



const STATUS = {

  loading: 'loading',

  prejoin: 'prejoin',

  joining: 'joining',

  live: 'live',

  leaving: 'leaving',

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

  const jitsiApiRef = useRef(null);



  const [roomStatus, setRoomStatus] = useState(STATUS.loading);

  const [appointment, setAppointment] = useState(null);

  const [error, setError] = useState('');

  const [mediaError, setMediaError] = useState('');

  const [nowTick, setNowTick] = useState(() => Date.now());

  const [elapsedSec, setElapsedSec] = useState(0);

  const [participantCount, setParticipantCount] = useState(0);

  const [conferenceJoined, setConferenceJoined] = useState(false);

  const [summaryDraft, setSummaryDraft] = useState('');

  const [mediaStatus, setMediaStatus] = useState({ checked: false, ok: false, reason: '' });

  const [roomEligibility, setRoomEligibility] = useState(null);

  const [embedAccess, setEmbedAccess] = useState(null);



  const load = useCallback(async () => {

    setRoomStatus(STATUS.loading);

    setConferenceJoined(false);

    setParticipantCount(0);

    setElapsedSec(0);

    setError('');

    setMediaError('');

    setEmbedAccess(null);

    setRoomEligibility(null);

    try {

      const [{ data: appointmentData }, { data: eligibility }] = await Promise.all([

        httpClient.get(`/appointments/${appointmentId}`),

        teleconsultationAPI.getRoomStatus(appointmentId),

      ]);

      setAppointment(appointmentData);

      setRoomEligibility(eligibility);



      if (appointmentData.consultation_type !== 'teleconsultation') {

        setError(eligibility?.message || 'Ce rendez-vous n’est pas une téléconsultation.');

        setRoomStatus(STATUS.error);

        return;

      }



      if (!eligibility?.can_join) {

        if (eligibility?.reason === 'too_early') {

          setRoomStatus(STATUS.prejoin);

          return;

        }

        setError(eligibility?.message || 'Cette téléconsultation n’est pas disponible pour le moment.');

        setRoomStatus(STATUS.error);

        return;

      }



      setRoomStatus(STATUS.prejoin);

    } catch (err) {

      setError(formatApiError(err, 'Impossible de charger la salle de téléconsultation.'));

      setRoomStatus(STATUS.error);

    }

  }, [appointmentId]);



  useEffect(() => {

    startTransition(() => {

      void load();

    });

  }, [load]);



  const provider = useMemo(
    () => resolveRoomProvider({ appointmentId }),
    [appointmentId]
  );



  const providerLabel = useMemo(() => getProviderDisplayLabel(provider), [provider]);



  const embedProps = useMemo(() => buildEmbedFromAccess(embedAccess), [embedAccess]);



  const appointmentStartMs = appointment?.date ? new Date(appointment.date).getTime() : null;

  const msUntilStart = appointmentStartMs != null ? appointmentStartMs - nowTick : null;



  useEffect(() => {

    if (roomStatus !== STATUS.prejoin && roomStatus !== STATUS.joining) return undefined;

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

            reason: mapMediaDeviceError(err),

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

    if (roomStatus !== STATUS.live || !conferenceJoined) return undefined;

    const id = window.setInterval(() => setElapsedSec((s) => s + 1), 1000);

    return () => window.clearInterval(id);

  }, [roomStatus, conferenceJoined]);



  useEffect(() => {

    if (roomEligibility?.reason !== 'too_early') return undefined;

    const id = window.setInterval(() => {

      teleconsultationAPI

        .getRoomStatus(appointmentId)

        .then(({ data }) => {

          setRoomEligibility(data);

          if (data?.can_join) {

            setError('');

          }

        })

        .catch(() => {

          /* keep waiting banner */

        });

    }, 15000);

    return () => window.clearInterval(id);

  }, [appointmentId, roomEligibility?.reason]);



  const enterRoom = async () => {

    setError('');

    setMediaError('');

    if (!mediaStatus.ok) {

      setMediaError(mediaStatus.reason || 'Autorisez la caméra et le micro avant de rejoindre.');

      return;

    }

    setRoomStatus(STATUS.joining);

    try {

      const { data: access } = await teleconsultationAPI.getAccess(appointmentId);

      const embed = buildEmbedFromAccess(access);

      if (embed?.blocked) {

        throw new Error(embed.reason || 'Configuration vidéo indisponible.');

      }

      if (!embed?.roomName || !embed?.domain) {

        throw new Error('Configuration vidéo indisponible pour ce rendez-vous.');

      }

      setEmbedAccess(access);

      setRoomEligibility((prev) => ({ ...(prev || {}), can_join: true, reason: 'ok' }));

      setRoomStatus(STATUS.live);

    } catch (err) {

      setError(formatApiError(err, 'Accès à la téléconsultation refusé.'));

      setRoomStatus(STATUS.prejoin);

    }

  };



  const hangUpAndEnd = useCallback(async () => {

    if (roomStatus === STATUS.leaving || roomStatus === STATUS.ended) return;

    setRoomStatus(STATUS.leaving);

    const api = jitsiApiRef.current;

    if (api && typeof api.executeCommand === 'function') {

      try {

        api.executeCommand('hangup');

      } catch {

        /* best-effort */

      }

    }

    jitsiApiRef.current = null;

    try {

      await teleconsultationAPI.endSession(appointmentId);

    } catch {

      /* best-effort */

    }

    if (appointment?.id && appointment?.patient_id) {

      try {

        const { data } = await patientRecordAPI.listSummaries(appointment.patient_id);

        const match = (data || []).find((s) => s.appointment_id === appointment.id);

        const parts = match

          ? [match.diagnostic, match.traitement, match.recommandations].filter(Boolean)

          : [];

        setSummaryDraft(parts.join('\n\n') || '');

      } catch {

        setSummaryDraft('');

      }

    } else {

      setSummaryDraft('');

    }

    setEmbedAccess(null);

    setRoomStatus(STATUS.ended);

  }, [appointment?.id, appointment?.patient_id, appointmentId, roomStatus]);



  const handleReadyToClose = useCallback(() => {

    void hangUpAndEnd();

  }, [hangUpAndEnd]);



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

    roomEligibility?.reason === 'too_early' ||

    (msUntilStart != null && msUntilStart > JOIN_WINDOW_MS && (roomStatus === STATUS.prejoin || roomStatus === STATUS.joining));

  const countdownLabel =

    msUntilStart != null && msUntilStart > 0 && msUntilStart <= 2 * 60 * 60 * 1000 ? formatCountdown(msUntilStart) : null;



  const peerPresent = participantCount > 1;

  const peerStatusLabel = !conferenceJoined

    ? 'Connexion à la salle…'

    : peerPresent

      ? isDoctorLike

        ? 'Patient connecté'

        : 'Médecin en ligne'

      : isDoctorLike

        ? 'En attente du patient…'

        : 'En attente du médecin…';



  const flowStep =

    roomStatus === STATUS.error

      ? 1

      : roomStatus === STATUS.loading

        ? 0

        : roomStatus === STATUS.prejoin || roomStatus === STATUS.joining

          ? 1

          : roomStatus === STATUS.live || roomStatus === STATUS.leaving

            ? 2

            : roomStatus === STATUS.ended

              ? 3

              : 0;



  const flowLabels = ['Salle d’attente', 'Préparation', 'Consultation en direct', 'Clôture'];



  const postConsultHref = isDoctorLike ? '/doctor/dashboard' : '/dashboard';



  const saveSummaryAndLeave = async () => {

    if (appointment?.id && appointment?.patient_id && summaryDraft.trim()) {

      try {

        await patientRecordAPI.createSummary(appointment.patient_id, {

          appointment_id: appointment.id,

          diagnostic: summaryDraft.trim(),

        });

      } catch {

        /* navigation continues even if save fails — user can retry from dossier */

      }

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



      {mediaError && (

        <div className="consult-room-banner consult-room-banner--error" role="alert">

          {mediaError}

        </div>

      )}



      {roomStatus === STATUS.loading && (

        <div className="consult-room-loading page-loading" role="status">

          <span className="app-spinner" aria-hidden />

          <span>Ouverture de la salle chiffrée…</span>

        </div>

      )}



      {(roomStatus === STATUS.prejoin || roomStatus === STATUS.joining) && appointment && (

        <section className="consult-prejoin" aria-labelledby="prejoin-title">

          <h2 id="prejoin-title" className="visually-hidden">

            Avant d’entrer

          </h2>



          {earlyForSession && (

            <div className="consult-waiting-banner" role="status">

              <strong>Salle d’attente virtuelle</strong>

              <span>

                {roomEligibility?.message ||

                  'Vous êtes connecté en avance. L’accès complet à la consultation s’ouvre en général 15 minutes avant l’horaire prévu.'}

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

              <div className="consult-device-preview on">

                <span className="consult-device-placeholder">Vidéo intégrée — {providerLabel}</span>

              </div>

              <ul className="consult-device-checklist">

                <li className={mediaStatus.ok ? 'is-ok' : mediaStatus.checked ? '' : 'is-ok'}>

                  {mediaStatus.checked

                    ? mediaStatus.ok

                      ? 'Caméra / micro autorisés'

                      : mediaStatus.reason

                    : 'Vérification des périphériques…'}

                </li>

                <li className="is-ok">Connexion chiffrée (HTTPS)</li>

                <li className="is-ok">Salle vidéo dans l’application (sans nouvel onglet)</li>

              </ul>

            </div>

            <div className="consult-prejoin-side">

              <p className="consult-provider-pill">

                Fournisseur vidéo : <strong>{providerLabel}</strong>

              </p>

              <p className="consult-prejoin-copy">

                La consultation audio et vidéo se déroule directement dans cette page. Sur iPhone, autorisez caméra et

                micro lorsque Safari vous le demande.

              </p>

              {roomStatus === STATUS.joining && (

                <div className="consult-connecting-panel" role="status" aria-live="polite">

                  <span className="app-spinner consult-connecting-spinner" aria-hidden />

                  <p className="consult-connecting-text">Préparation de la salle vidéo…</p>

                </div>

              )}

              <button

                type="button"

                className="btn btn-primary consult-join-main"

                disabled={roomStatus === STATUS.joining || roomEligibility?.reason === 'too_early' || !mediaStatus.ok}

                onClick={enterRoom}

              >

                {roomStatus === STATUS.joining

                  ? 'Connexion…'

                  : roomEligibility?.reason === 'too_early'

                    ? 'Salle pas encore ouverte'

                    : 'Rejoindre la consultation'}

              </button>

            </div>

          </div>

        </section>

      )}



      {(roomStatus === STATUS.live || roomStatus === STATUS.leaving) && embedProps && !embedProps.blocked && (

        <section className="consult-live" aria-label="Salle de téléconsultation">

          <div className="consult-live-statusbar">

            <div className="consult-live-status-left">

              <span className="consult-live-timer" aria-label="Durée de la séance">

                {conferenceJoined ? formatElapsed(elapsedSec) : '00:00'}

              </span>

              <span className="consult-live-pill consult-live-pill--signal">

                {conferenceJoined ? 'En direct' : 'Connexion…'}

              </span>

              <span className="consult-live-pill consult-live-pill--count" aria-label="Participants">

                {participantCount} participant{participantCount !== 1 ? 's' : ''}

              </span>

            </div>

            <div className={`consult-live-peer ${peerPresent ? 'is-on' : 'is-wait'}`}>{peerStatusLabel}</div>

          </div>



          <JitsiEmbeddedMeeting

            domain={embedProps.domain}

            roomName={embedProps.roomName}

            jwt={embedProps.jwt}

            appId={embedProps.appId}

            jaasMode={embedProps.jaasMode}

            displayName={embedProps.displayName}

            email={embedProps.email}

            appointmentId={appointmentId}

            onJoined={() => setConferenceJoined(true)}

            onReadyToClose={handleReadyToClose}

            onParticipantChange={setParticipantCount}

            onMediaError={setMediaError}

            onApiReady={(api) => {

              jitsiApiRef.current = api;

            }}

          />



          <div className="consult-live-toolbar">

            <button

              type="button"

              className="consult-toolbar-btn consult-toolbar-btn--danger"

              disabled={roomStatus === STATUS.leaving}

              onClick={() => void hangUpAndEnd()}

            >

              {roomStatus === STATUS.leaving ? 'Fin…' : 'Quitter la consultation'}

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

              <p>

                Merci d’avoir utilisé la téléconsultation sécurisée. Vous pouvez retrouver les messages liés à ce

                rendez-vous dans votre messagerie.

              </p>

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

