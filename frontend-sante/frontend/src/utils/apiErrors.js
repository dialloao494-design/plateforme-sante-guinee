/** Parse FastAPI error payloads for display in forms. */
export function parseApiError(err, fallback = 'Une erreur est survenue') {
  const detail = err?.response?.data?.detail;
  if (!detail) {
    return err?.message || fallback;
  }
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : '';
        const msg = item?.msg?.replace(/^Value error,\s*/i, '') || item?.msg;
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean)
      .join(' ');
  }
  return fallback;
}

export function validateSignupPassword(password) {
  if (!password || password.length < 8) {
    return 'Le mot de passe doit contenir au moins 8 caractères.';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Le mot de passe doit contenir au moins une majuscule (A-Z).';
  }
  if (!/[0-9]/.test(password)) {
    return 'Le mot de passe doit contenir au moins un chiffre (0-9).';
  }
  return null;
}
