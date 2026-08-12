/**
 * A completed HIS registration must include a real patient_number.
 * Offline optimistic responses must not be treated as success.
 *
 * Product rule: HIS patient registration is online-only — dossier numbers are
 * server-issued and must never be queued in the offline outbox.
 */
export function isCompleteRegistrationResponse(data) {
  if (!data || typeof data !== 'object') return false;
  if (data._offline_queued || data.offline) return false;
  const number = typeof data.patient_number === 'string' ? data.patient_number.trim() : '';
  return Boolean(number);
}

export const REGISTRATION_ONLINE_REQUIRED_MESSAGE =
  'Connexion internet requise pour générer le N° dossier patient. '
  + 'L’enregistrement n’a pas été mis en file d’attente. '
  + 'Les données du formulaire sont conservées — reconnectez-vous puis réessayez.';

/** @deprecated Use REGISTRATION_ONLINE_REQUIRED_MESSAGE */
export const REGISTRATION_INCOMPLETE_MESSAGE = REGISTRATION_ONLINE_REQUIRED_MESSAGE;
