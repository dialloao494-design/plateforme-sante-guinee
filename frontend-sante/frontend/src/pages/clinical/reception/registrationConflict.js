/**
 * Single source of truth for reception HIS registration conflict handling.
 *
 * The backend returns HTTP 409 with an object detail:
 *   { code: "duplicate_patient", message, matches: [...] }
 * and accepts confirm_duplicate=true to proceed.
 *
 * This module must stay the only place that interprets that contract for the
 * reception UI — do not reimplement ad-hoc 409 handling in tabs/hooks.
 */

import {
  formatApiError,
  getApiErrorDetailObject,
  isDuplicatePatientError,
} from '../../../utils/apiError.js';

export const DUPLICATE_PATIENT_CODE = 'duplicate_patient';

const DUPLICATE_FOLLOW_UP =
  ' Vérifiez les dossiers ci-dessous, ouvrez un patient existant, ou confirmez qu’il s’agit bien d’un nouveau patient.';

/**
 * @param {unknown} err Axios-like error
 * @param {object} payload Registration payload that was submitted
 * @returns {{
 *   kind: 'duplicate_patient' | 'error',
 *   message: string,
 *   matches: object[],
 *   pendingPayload: object | null,
 * }}
 */
export function resolveRegistrationConflict(err, payload = {}) {
  if (isDuplicatePatientError(err)) {
    const detail = getApiErrorDetailObject(err);
    const matches = Array.isArray(detail?.matches) ? detail.matches : [];
    const message =
      formatApiError(err, 'Un ou plusieurs patients similaires existent déjà') +
      (matches.length ? DUPLICATE_FOLLOW_UP : '');
    return {
      kind: DUPLICATE_PATIENT_CODE,
      message,
      matches,
      pendingPayload: { ...payload, confirm_duplicate: true },
    };
  }

  return {
    kind: 'error',
    message: formatApiError(err, 'Enregistrement du patient impossible'),
    matches: [],
    pendingPayload: null,
  };
}

/** True when UI must show the confirm/open-existing panel. */
export function shouldShowDuplicatePanel(conflict) {
  return conflict?.kind === DUPLICATE_PATIENT_CODE && Array.isArray(conflict.matches) && conflict.matches.length > 0;
}
