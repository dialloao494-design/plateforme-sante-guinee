/**
 * Teleconsultation provider abstraction — Jitsi embedded (Phase 2).
 */

export const TELECONSULT_PROVIDERS = {
  stub: 'stub',
  daily: 'daily',
  jitsi: 'jitsi',
  twilio: 'twilio',
};

export function getConfiguredTeleconsultProvider() {
  const raw = (import.meta.env.VITE_TELECONSULT_PROVIDER || 'jitsi').toLowerCase().trim();
  if (raw === 'stub') return TELECONSULT_PROVIDERS.jitsi;
  if (Object.prototype.hasOwnProperty.call(TELECONSULT_PROVIDERS, raw)) {
    return raw;
  }
  return TELECONSULT_PROVIDERS.jitsi;
}

export function getJitsiDomain() {
  return (import.meta.env.VITE_JITSI_DOMAIN || '127.0.0.1:8443')
    .replace(/^https?:\/\//, '')
    .replace(/\/$/, '');
}

export function isBlockedPublicJitsiDomain(domain) {
  const host = String(domain || '')
    .replace(/^https?:\/\//, '')
    .split(':')[0]
    .toLowerCase();
  return host === 'meet.jit.si';
}

export function inferProviderFromMeetingUrl(url) {
  if (!url) return TELECONSULT_PROVIDERS.jitsi;
  const u = String(url).toLowerCase();
  if (u.includes('daily.co')) return TELECONSULT_PROVIDERS.daily;
  if (u.includes('meet.jit.si') || u.includes('8x8.vc') || u.includes('jitsi')) {
    return TELECONSULT_PROVIDERS.jitsi;
  }
  if (u.includes('twilio.com') || u.includes('video.twilio')) return TELECONSULT_PROVIDERS.twilio;
  return TELECONSULT_PROVIDERS.jitsi;
}

/**
 * @param {{ appointmentId: number | string }} params
 */
export function resolveRoomProvider() {
  const fromEnv = getConfiguredTeleconsultProvider();
  if (fromEnv !== TELECONSULT_PROVIDERS.stub) {
    return fromEnv;
  }
  return TELECONSULT_PROVIDERS.jitsi;
}

export function buildJitsiMeetingUrl(domain, roomName, jwtToken) {
  if (!domain || !roomName) return null;
  const host = String(domain).replace(/^https?:\/\//, '').replace(/\/$/, '');
  const base = `https://${host}/${roomName}`;
  if (jwtToken) {
    return `${base}?jwt=${encodeURIComponent(jwtToken)}`;
  }
  return base;
}

/**
 * Map getUserMedia / device errors to French user messages.
 */
export function mapMediaDeviceError(err) {
  const name = err?.name || '';
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'Accès refusé. Autorisez la caméra et le micro pour ce site (Réglages Safari → Caméra/Micro).';
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'Aucune caméra ou micro détecté sur cet appareil.';
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'Caméra ou micro déjà utilisé par une autre application.';
  }
  if (name === 'SecurityError') {
    return 'Connexion sécurisée (HTTPS) requise pour la vidéo.';
  }
  return err?.message || 'Impossible d’accéder à la caméra ou au micro.';
}

export function getProviderDisplayLabel(provider) {
  switch (provider) {
    case TELECONSULT_PROVIDERS.daily:
      return 'Daily.co';
    case TELECONSULT_PROVIDERS.jitsi:
      return 'Jitsi (intégré)';
    case TELECONSULT_PROVIDERS.twilio:
      return 'Twilio Video';
    case 'external':
      return 'Jitsi';
    default:
      return 'Jitsi (intégré)';
  }
}

/**
 * Build embed props from GET /teleconsultation/.../access payload.
 */
export function buildEmbedFromAccess(access) {
  if (!access?.room_name) return null;
  const domain = access.jitsi_domain || getJitsiDomain();
  if (access.embed_ready === false) {
    return {
      blocked: true,
      reason:
        access.embed_block_reason ||
        'Configuration vidéo indisponible (meet.jit.si interdit en iframe).',
    };
  }
  if (isBlockedPublicJitsiDomain(domain) && !access.jitsi_jwt) {
    return {
      blocked: true,
      reason:
        'meet.jit.si ne permet pas la vidéo intégrée. Configurez JITSI_DOMAIN (instance dédiée ou JaaS).',
    };
  }
  return {
    domain,
    roomName: access.room_name,
    jwt: access.jitsi_jwt || null,
    appId: access.jitsi_app_id || null,
    jaasMode: access.jitsi_embed_mode === 'jaas',
    displayName: access.display_name || 'Participant',
    email: access.email || null,
  };
}
