/**
 * Normalize Axios / fetch-style errors for user-facing messages.
 */
export function formatApiError(err, fallback = 'Une erreur est survenue.') {
  if (!err) return fallback;

  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim();
  }
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || JSON.stringify(item)))
      .join(' · ');
  }

  const msg = err?.response?.data?.message;
  if (typeof msg === 'string' && msg.trim()) {
    return msg.trim();
  }

  const net = String(err?.message || '');
  if (/network|failed to fetch|timeout/i.test(net)) {
    return 'Erreur de connexion. Vérifiez votre réseau et réessayez.';
  }

  if (typeof err?.message === 'string' && err.message.trim() && !err.message.startsWith('Missing authentication')) {
    return err.message.trim();
  }

  return fallback;
}
