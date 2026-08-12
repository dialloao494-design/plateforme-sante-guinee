/**
 * HIS registration response classification.
 *
 * Offline-capable product rule:
 * - Queued (202 / _offline_queued) is a valid pending state — not a failure.
 * - Complete success requires a server-issued patient_number (PAT-…).
 * - After sync, reconcilePatient notifies the UI with the real dossier number.
 */

export const REG_STATUS = {
  COMPLETE: 'complete',
  QUEUED: 'queued',
  INCOMPLETE: 'incomplete',
};

export function classifyRegistrationResponse(data) {
  if (!data || typeof data !== 'object') return REG_STATUS.INCOMPLETE;
  const number = typeof data.patient_number === 'string' ? data.patient_number.trim() : '';
  if (number) return REG_STATUS.COMPLETE;
  if (data._offline_queued || data.offline || data._sync_status === 'queued') {
    return REG_STATUS.QUEUED;
  }
  return REG_STATUS.INCOMPLETE;
}

export function isCompleteRegistrationResponse(data) {
  return classifyRegistrationResponse(data) === REG_STATUS.COMPLETE;
}

export function isQueuedRegistrationResponse(data) {
  return classifyRegistrationResponse(data) === REG_STATUS.QUEUED;
}

export const REGISTRATION_QUEUED_MESSAGE =
  'Patient enregistré hors ligne — synchronisation en attente. '
  + 'Le N° dossier patient sera attribué automatiquement à la reconnexion. '
  + 'Ne resaisissez pas le même patient.';

export const REGISTRATION_INCOMPLETE_MESSAGE =
  'Enregistrement non finalisé : aucune confirmation serveur ni mise en file. '
  + 'Les données du formulaire sont conservées — réessayez.';

/** @deprecated alias kept for older imports */
export const REGISTRATION_ONLINE_REQUIRED_MESSAGE = REGISTRATION_QUEUED_MESSAGE;
