/**
 * Map login/API failures to clinic-facing French messages.
 * Must surface lockouts (429) — never hide them behind a generic retry string.
 */

export function toUserFriendlyLoginMessage(err) {
  const status = err?.response?.status;
  const rawDetail = err?.response?.data?.detail ?? err?.response?.data?.message ?? err?.message ?? '';
  const detail = String(Array.isArray(rawDetail) ? rawDetail.map((x) => x?.msg || x).join(' ') : rawDetail);
  const detailLower = detail.toLowerCase();
  const code = String(err?.code || '').toLowerCase();

  if (/temporarily locked|compte.*verrouill/i.test(detail)) {
    return 'Compte temporairement verrouillé après plusieurs échecs. Réessayez dans quelques minutes, ou demandez une réinitialisation du mot de passe à l’administrateur.';
  }

  // Soft throttle (still 429) — short pause, not a full lock window.
  if (/slow down|too many failed login attempts/i.test(detail)) {
    return 'Trop de tentatives incorrectes. Attendez quelques secondes, puis réessayez avec le bon mot de passe.';
  }

  // Generic 429 (IP rate limit, etc.) — do not claim the account is locked.
  if (status === 429 || /try again later|trop de tentatives|rate limit/i.test(detail)) {
    return 'Trop de tentatives pour le moment. Réessayez dans une minute.';
  }

  if (status === 401 || status === 400) {
    if (/mfa/i.test(detailLower)) {
      return 'Code MFA requis ou invalide.';
    }
    return 'Email ou mot de passe incorrect';
  }

  if (status === 403 && /mfa/i.test(detailLower)) {
    return 'Activation MFA requise avant connexion pour ce profil.';
  }

  if (
    code === 'err_network' ||
    code === 'econnrefused' ||
    /failed to fetch|network error|network|econnrefused|connection refused|timeout|405 not allowed|nginx/.test(detailLower) ||
    (!status && /login failed|network error/i.test(String(err?.message || '')))
  ) {
    return typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.PROD
      ? 'Impossible de joindre le serveur. Réessayez dans un instant.'
      : 'Impossible de joindre l’API. Vérifiez que le backend tourne sur http://127.0.0.1:8000.';
  }

  if (/missing authentication token|session non établie|could not validate credentials/i.test(detailLower)) {
    return 'Session non établie après connexion. Réessayez (Safari/iPhone : mettez à jour l’application) ou videz le cache du navigateur.';
  }

  if (detail && detail.trim() && detail.length < 220 && !/^request failed with status code/i.test(detail)) {
    return detail.trim();
  }

  return 'Une erreur est survenue, veuillez réessayer';
}
