/**
 * A completed HIS registration must include a real patient_number.
 * Offline optimistic responses must not be treated as success.
 */
export function isCompleteRegistrationResponse(data) {
  if (!data || typeof data !== 'object') return false;
  if (data._offline_queued || data.offline) return false;
  const number = typeof data.patient_number === 'string' ? data.patient_number.trim() : '';
  return Boolean(number);
}

export const REGISTRATION_INCOMPLETE_MESSAGE =
  'Enregistrement non finalisé : le N° dossier patient n’a pas été généré. '
  + 'Vérifiez la connexion internet et réessayez. Les données du formulaire sont conservées.';
