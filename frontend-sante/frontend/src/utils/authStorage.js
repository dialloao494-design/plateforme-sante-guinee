/** Per-tab auth persistence — sessionStorage isolates each browser tab. */

import { invalidateCache } from './apiCache.js';

export const AUTH_STORAGE_KEYS = [
  'token',
  'access_token',
  'refresh_token',
  'user_role',
  'user_id',
  'must_change_password',
  'password_reset_required',
  'force_password_change',
  'session_last_activity',
  'sg_auth_profile',
];

const PROFILE_STORAGE_KEYS = AUTH_STORAGE_KEYS.filter(
  (key) => key !== 'token' && key !== 'access_token' && key !== 'refresh_token'
);

export function isSameOriginApi() {
  const fromMeta =
    typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {};
  const fromProcess = typeof process !== 'undefined' ? process.env : {};
  const flag = (name) =>
    String(fromMeta[name] ?? fromProcess[name] ?? '')
      .trim()
      .toLowerCase() === 'true';
  const apiUrl = String(fromMeta.VITE_API_URL ?? fromProcess.VITE_API_URL ?? '').trim();
  if (flag('VITE_SAME_ORIGIN_API') || flag('VITE_USE_RELATIVE_API')) {
    return true;
  }
  return apiUrl === '/api';
}

function tabStore() {
  return typeof window !== 'undefined' ? sessionStorage : null;
}

function legacySharedStore() {
  return typeof window !== 'undefined' ? localStorage : null;
}

let legacyMigrated = false;

/** One-time copy from legacy shared localStorage when this tab has no session yet. */
function migrateLegacyAuthOnce() {
  if (legacyMigrated) {
    return;
  }
  legacyMigrated = true;
  const tab = tabStore();
  const legacy = legacySharedStore();
  if (!tab || !legacy) {
    return;
  }
  const hasTabToken = tab.getItem('token') || tab.getItem('access_token');
  if (hasTabToken) {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    try {
      const value = legacy.getItem(key);
      if (value != null) {
        tab.setItem(key, value);
      }
    } catch {
      /* ignore */
    }
  }
}

/** Remove shared localStorage auth keys so they cannot overwrite other tabs on migration. */
export function clearLegacySharedAuth() {
  const legacy = legacySharedStore();
  if (!legacy) {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    try {
      legacy.removeItem(key);
    } catch {
      /* ignore */
    }
  }
}

export function getAuthItem(key) {
  migrateLegacyAuthOnce();
  const tab = tabStore();
  if (!tab) {
    return null;
  }
  try {
    return tab.getItem(key);
  } catch {
    return null;
  }
}

export function setAuthItem(key, value) {
  const tab = tabStore();
  if (!tab) {
    return;
  }
  try {
    tab.setItem(key, value);
  } catch {
    /* ignore quota errors */
  }
}

export function removeAuthItem(key) {
  try {
    tabStore()?.removeItem(key);
  } catch {
    /* ignore */
  }
}

export function getAuthToken() {
  return getAuthItem('token') || getAuthItem('access_token');
}

export function setAuthToken(token) {
  if (!token) {
    removeAuthItem('token');
    removeAuthItem('access_token');
    return;
  }
  setAuthItem('token', token);
  setAuthItem('access_token', token);
}

export function getRefreshToken() {
  return getAuthItem('refresh_token');
}

export function setRefreshToken(token) {
  if (!token) {
    removeAuthItem('refresh_token');
    return;
  }
  setAuthItem('refresh_token', token);
}

/** Persist SPA bearer session tokens returned by login/refresh JSON. */
export function persistSessionTokens(payload = {}) {
  const access =
    payload?.access_token || payload?.accessToken || payload?.token || null;
  const refresh = payload?.refresh_token || payload?.refreshToken || null;
  if (isSameOriginApi()) {
    if (access || refresh) {
      setAuthToken(null);
      setRefreshToken(null);
    }
    return Boolean(access || refresh || payload?.csrf_token);
  }
  if (access) {
    setAuthToken(access);
  }
  if (refresh) {
    setRefreshToken(refresh);
  }
  return Boolean(access);
}

export function touchSessionActivity() {
  setAuthItem('session_last_activity', String(Date.now()));
}

/** Clear auth for the current tab only, plus offline PHI stores. */
export function clearAllClientStorage() {
  if (typeof window === 'undefined') {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    removeAuthItem(key);
  }
  invalidateCache();
  // Best-effort async purge — do not block logout UX.
  void import('../offline/db.js')
    .then(({ purgeOfflinePrivacyState }) => purgeOfflinePrivacyState())
    .catch(() => {});
}
