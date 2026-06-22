/** Auth bootstrap helpers — timeouts, logging, user-facing errors. */

export const AUTH_BOOTSTRAP_TIMEOUT_MS = 15_000;
export const PROFILE_GATE_TIMEOUT_MS = 12_000;

export function logAuthSessionFailure(phase, error, extra = {}) {
  const payload = {
    phase,
    message: error?.message || String(error),
    status: error?.response?.status,
    code: error?.code,
    url: error?.config?.url,
    ...extra,
  };
  console.error('[AUTH-SESSION]', payload);
  return payload;
}

export function withTimeout(promise, ms = AUTH_BOOTSTRAP_TIMEOUT_MS, label = 'auth') {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = window.setTimeout(() => {
      const err = new Error(`Délai dépassé (${Math.round(ms / 1000)}s) — ${label}`);
      err.code = 'AUTH_TIMEOUT';
      reject(err);
    }, ms);
  });
  return Promise.race([promise, timeout]).finally(() => {
    window.clearTimeout(timer);
  });
}

export function toBootstrapErrorMessage(err) {
  if (err?.code === 'AUTH_TIMEOUT' || err?.code === 'ECONNABORTED') {
    return 'Le serveur met trop de temps à répondre. Vérifiez votre connexion et réessayez.';
  }
  const status = err?.response?.status;
  if (status === 401 || status === 403) {
    return 'Session expirée ou non autorisée. Reconnectez-vous.';
  }
  if (status >= 500) {
    return 'Le serveur est temporairement indisponible. Réessayez dans un instant.';
  }
  if (!status && /network|fetch|failed/i.test(String(err?.message || ''))) {
    return 'Impossible de joindre le serveur. Vérifiez votre connexion.';
  }
  return err?.message || 'Impossible de charger votre profil.';
}
