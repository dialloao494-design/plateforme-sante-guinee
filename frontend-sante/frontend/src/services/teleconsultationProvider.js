/**
 * Teleconsultation provider abstraction — wire Daily.co, Jitsi, or Twilio Video
 * without importing their SDKs until credentials are configured.
 */

export const TELECONSULT_PROVIDERS = {
  stub: 'stub',
  daily: 'daily',
  jitsi: 'jitsi',
  twilio: 'twilio',
};

export function getConfiguredTeleconsultProvider() {
  const raw = (import.meta.env.VITE_TELECONSULT_PROVIDER || 'stub').toLowerCase().trim();
  if (Object.prototype.hasOwnProperty.call(TELECONSULT_PROVIDERS, raw)) {
    return raw;
  }
  return TELECONSULT_PROVIDERS.stub;
}

export function inferProviderFromMeetingUrl(url) {
  if (!url) return TELECONSULT_PROVIDERS.stub;
  const u = String(url).toLowerCase();
  if (u.includes('daily.co')) return TELECONSULT_PROVIDERS.daily;
  if (u.includes('meet.jit.si') || u.includes('8x8.vc') || u.includes('jitsi')) {
    return TELECONSULT_PROVIDERS.jitsi;
  }
  if (u.includes('twilio.com') || u.includes('video.twilio')) return TELECONSULT_PROVIDERS.twilio;
  return 'external';
}

/**
 * @param {{ meetingUrl?: string | null, appointmentId: number | string }} params
 */
export function resolveRoomProvider(params) {
  const fromEnv = getConfiguredTeleconsultProvider();
  if (fromEnv !== TELECONSULT_PROVIDERS.stub) {
    return fromEnv;
  }
  return inferProviderFromMeetingUrl(params.meetingUrl);
}

export function getProviderDisplayLabel(provider) {
  switch (provider) {
    case TELECONSULT_PROVIDERS.daily:
      return 'Daily.co';
    case TELECONSULT_PROVIDERS.jitsi:
      return 'Jitsi';
    case TELECONSULT_PROVIDERS.twilio:
      return 'Twilio Video';
    case 'external':
      return 'Lien externe';
    default:
      return 'Mode démo';
  }
}
