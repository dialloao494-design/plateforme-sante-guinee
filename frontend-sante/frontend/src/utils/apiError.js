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

export function formatApiError(err, fallback = 'Une erreur est survenue.') {
  if (!err) return fallback;

  const detail = err?.response?.data?.detail;
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

  const msg = err?.response?.data?.message;
  if (typeof msg === 'string' && msg.trim()) {
    return humanizeApiError(msg.trim());
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
