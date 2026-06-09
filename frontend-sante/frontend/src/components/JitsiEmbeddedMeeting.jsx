import { useCallback, useEffect, useRef } from 'react';
import { JaaSMeeting, JitsiMeeting } from '@jitsi/react-sdk';

const JITSI_CONFIG = {
  prejoinPageEnabled: false,
  startWithAudioMuted: false,
  startWithVideoMuted: false,
  disableDeepLinking: true,
  enableWelcomePage: false,
  hideConferenceSubject: true,
  enableClosePage: false,
  disableInviteFunctions: true,
  enableLobby: false,
  hideLobbyButton: true,
  disableLogin: true,
  enableUserRolesBasedOnToken: false,
  requireDisplayName: false,
  enableInsecureRoomNameWarning: false,
  disableThirdPartyRequests: true,
  disableProfile: true,
  enableGuestDomain: true,
  guestsEnabled: true,
  lobby: { autoKnock: false, enableChat: false },
};

const JITSI_INTERFACE = {
  SHOW_JITSI_WATERMARK: false,
  MOBILE_APP_PROMO: false,
  DISABLE_JOIN_LEAVE_NOTIFICATIONS: false,
  HIDE_DEEP_LINKING_LOGO: true,
  SHOW_PROMOTIONAL_CLOSE_PAGE: false,
  AUTHENTICATION_ENABLE: false,
  TOOLBAR_ALWAYS_VISIBLE: true,
  TOOLBAR_BUTTONS: ['microphone', 'camera', 'hangup', 'tileview', 'settings'],
};

function mapConnectionError(payload) {
  const raw = payload?.error?.name || payload?.error?.message || payload?.message || '';
  const text = String(raw).toLowerCase();
  if (text.includes('membersonly') || text.includes('members_only')) {
    return (
      'Connexion refusée (salle réservée aux membres). ' +
      'L’instance Jitsi doit autoriser l’entrée directe sans OAuth — voir deploy/jitsi/README.md.'
    );
  }
  if (text.includes('lobby')) {
    return 'Connexion bloquée par la salle d’attente (lobby). Désactivez le lobby sur votre instance Jitsi.';
  }
  return raw || 'Erreur de connexion à la visioconférence.';
}

/**
 * Embedded Jitsi Meet room — real WebRTC audio/video inside the platform.
 *
 * @param {{
 *   domain: string;
 *   roomName: string;
 *   jwt?: string | null;
 *   appId?: string | null;
 *   jaasMode?: boolean;
 *   displayName: string;
 *   email?: string | null;
 *   appointmentId: number | string;
 *   onJoined?: () => void;
 *   onReadyToClose?: () => void;
 *   onParticipantChange?: (count: number) => void;
 *   onMediaError?: (message: string) => void;
 *   onApiReady?: (api: object) => void;
 * }} props
 */
export default function JitsiEmbeddedMeeting({
  domain,
  roomName,
  jwt = null,
  appId = null,
  jaasMode = false,
  displayName,
  email = null,
  appointmentId,
  onJoined,
  onReadyToClose,
  onParticipantChange,
  onMediaError,
  onApiReady,
}) {
  const apiRef = useRef(null);
  const onParticipantChangeRef = useRef(onParticipantChange);
  const onMediaErrorRef = useRef(onMediaError);
  const onJoinedRef = useRef(onJoined);
  const onReadyToCloseRef = useRef(onReadyToClose);
  const onApiReadyRef = useRef(onApiReady);

  useEffect(() => {
    onParticipantChangeRef.current = onParticipantChange;
    onMediaErrorRef.current = onMediaError;
    onJoinedRef.current = onJoined;
    onReadyToCloseRef.current = onReadyToClose;
    onApiReadyRef.current = onApiReady;
  }, [onParticipantChange, onMediaError, onJoined, onReadyToClose, onApiReady]);

  const refreshParticipantCount = useCallback(() => {
    const api = apiRef.current;
    if (!api || typeof api.getNumberOfParticipants !== 'function') return;
    try {
      onParticipantChangeRef.current?.(api.getNumberOfParticipants());
    } catch {
      /* ignore */
    }
  }, []);

  const handleApiReady = useCallback(
    (externalApi) => {
      apiRef.current = externalApi;
      onApiReadyRef.current?.(externalApi);

      externalApi.addListener('videoConferenceJoined', () => {
        onJoinedRef.current?.();
        refreshParticipantCount();
      });

      externalApi.addListener('participantJoined', () => {
        refreshParticipantCount();
      });

      externalApi.addListener('participantLeft', () => {
        refreshParticipantCount();
      });

      externalApi.addListener('readyToClose', () => {
        onReadyToCloseRef.current?.();
      });

      externalApi.addListener('conference.connectionError', (payload) => {
        onMediaErrorRef.current?.(mapConnectionError(payload));
      });

      externalApi.addListener('conferenceFailed', (payload) => {
        onMediaErrorRef.current?.(mapConnectionError(payload));
      });

      externalApi.addListener('errorOccurred', (payload) => {
        const msg = payload?.error?.message || payload?.error?.name || 'Erreur vidéo Jitsi.';
        onMediaErrorRef.current?.(msg);
      });

      externalApi.addListener('mediaDevicesError', (payload) => {
        const msg =
          payload?.message ||
          (payload?.type === 'permission'
            ? 'Autorisez la caméra et le micro dans les réglages du navigateur.'
            : 'Périphérique audio ou vidéo indisponible.');
        onMediaErrorRef.current?.(msg);
      });
    },
    [refreshParticipantCount]
  );

  useEffect(
    () => () => {
      const api = apiRef.current;
      if (api && typeof api.dispose === 'function') {
        try {
          api.dispose();
        } catch {
          /* ignore */
        }
      }
      apiRef.current = null;
    },
    []
  );

  const configOverwrite = {
    ...JITSI_CONFIG,
    subject: `Consultation #${appointmentId}`,
  };

  const sharedProps = {
    configOverwrite,
    interfaceConfigOverwrite: JITSI_INTERFACE,
    userInfo: {
      displayName: displayName || 'Participant',
      email: email || undefined,
    },
    onApiReady: handleApiReady,
    getIFrameRef: (iframeRef) => {
      if (iframeRef) {
        iframeRef.style.height = '100%';
        iframeRef.style.width = '100%';
        iframeRef.style.border = '0';
        iframeRef.setAttribute('allow', 'camera; microphone; fullscreen; autoplay; display-capture');
      }
    },
  };

  const useJaas = Boolean(jaasMode && appId);

  return (
    <div className="consult-jitsi-container">
      {useJaas ? (
        <JaaSMeeting appId={appId} roomName={roomName} jwt={jwt || undefined} {...sharedProps} />
      ) : (
        <JitsiMeeting
          domain={domain}
          roomName={roomName}
          jwt={jwt || undefined}
          {...sharedProps}
        />
      )}
    </div>
  );
}
