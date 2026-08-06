/**
 * Normalize Axios / fetch-style errors for user-facing messages.
 */

const TECHNICAL_ERROR_PATTERNS = [
  {
    test: (text) => /^Requires one of roles:/i.test(text) || /^Operation requires one of roles:/i.test(text),
    message: 'Accès réservé à un autre profil. Contactez l’administrateur de la clinique si vous pensez qu’il s’agit d’une erreur.',
  },
  {
    test: (text) => /Platform admin must specify clinic context/i.test(text),
    message: 'Aucune clinique sélectionnée. Créez ou choisissez une clinique depuis l’administration.',
  },
  {
    test: (text) => /Platform owner privileges required/i.test(text),
    message: 'Cette section est réservée au propriétaire de la plateforme.',
  },
  {
    test: (text) => /Could not validate credentials/i.test(text),
    message: 'Session expirée. Reconnectez-vous.',
  },
];

export function humanizeApiError(text) {
  if (!text || typeof text !== 'string') {
    return text;
  }
  const trimmed = text.trim();
  for (const { test, message } of TECHNICAL_ERROR_PATTERNS) {
    if (test(trimmed)) {
      return message;
    }
  }
  return trimmed;
}

export function getApiErrorDetail(err) {
  return err?.response?.data?.detail;
}

/** Structured FastAPI detail objects (e.g. duplicate_patient 409). */
export function getApiErrorDetailObject(err) {
  const detail = getApiErrorDetail(err);
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    return detail;
  }
  return null;
}

export function isDuplicatePatientError(err) {
  const detail = getApiErrorDetailObject(err);
  return err?.response?.status === 409 && detail?.code === 'duplicate_patient';
}

export function isPermissionDeniedError(err) {
  const detail = getApiErrorDetail(err);
  const text =
    typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && !Array.isArray(detail)
        ? String(detail.message || detail.code || '')
        : String(err?.message || '');
  return (
    /^Requires one of roles:/i.test(text) ||
    /^Operation requires one of roles:/i.test(text) ||
    /^Permission denied:/i.test(text)
  );
}

export function formatApiError(err, fallback = 'Une erreur est survenue.') {
  if (!err) return fallback;

  const detail = getApiErrorDetail(err);
  if (typeof detail === 'string' && detail.trim()) {
    return humanizeApiError(detail.trim());
  }
  if (Array.isArray(detail) && detail.length) {
    return humanizeApiError(
      detail
        .map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item)))
        .join(' · ')
    );
  }
  if (detail && typeof detail === 'object') {
    const objectMessage =
      (typeof detail.message === 'string' && detail.message.trim()) ||
      (typeof detail.detail === 'string' && detail.detail.trim()) ||
      (typeof detail.error === 'string' && detail.error.trim()) ||
      '';
    if (objectMessage) {
      return humanizeApiError(objectMessage);
    }
  }

  const msg = err?.response?.data?.message;
  if (typeof msg === 'string' && msg.trim()) {
    return humanizeApiError(msg.trim());
  }

  const statusPayload = err?.response?.data?.status;
  if (statusPayload === 'error' && typeof err?.response?.data?.message === 'string') {
    return humanizeApiError(err.response.data.message.trim());
  }

  const net = String(err?.message || '');
  if (/network|failed to fetch|timeout/i.test(net)) {
    return 'Impossible de joindre le serveur. Vérifiez votre connexion et réessayez.';
  }

  if (typeof err?.message === 'string' && err.message.trim() && !err.message.startsWith('Missing authentication')) {
    return humanizeApiError(err.message.trim());
  }

  return fallback;
}
