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

function tabStore() {
  return typeof window !== 'undefined' ? sessionStorage : null;
}

function legacySharedStore() {
  try {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') return null;
    return localStorage;
  } catch {
    return null;
  }
}

let legacyMigrated = false;

export function isSameOriginApi() {
  try {
    const env = (typeof import.meta !== 'undefined' && import.meta.env) || {};
    const fromProcess = (typeof globalThis !== 'undefined' && globalThis.process && globalThis.process.env) || {};
    const same =
      env.VITE_SAME_ORIGIN_API
      || fromProcess.VITE_SAME_ORIGIN_API
      || env.VITE_USE_RELATIVE_API
      || fromProcess.VITE_USE_RELATIVE_API;
    if (String(same || '').toLowerCase() === 'true') return true;
    const explicit = String(env.VITE_API_URL || fromProcess.VITE_API_URL || '').trim();
    if (explicit === '/api' || explicit === '/') return true;
  } catch { /* ignore */ }
  return false;
}

function migrateLegacyAuthOnce() {
  if (legacyMigrated) return;
  legacyMigrated = true;
  const tab = tabStore();
  const legacy = legacySharedStore();
  if (!tab || !legacy) return;
  if (tab.getItem('token') || tab.getItem('access_token')) return;
  for (const key of AUTH_STORAGE_KEYS) {
    try {
      const value = legacy.getItem(key);
      if (value != null) tab.setItem(key, value);
    } catch { /* ignore */ }
  }
}

export function clearLegacySharedAuth() {
  const legacy = legacySharedStore();
  if (!legacy) return;
  for (const key of AUTH_STORAGE_KEYS) {
    try { legacy.removeItem(key); } catch { /* ignore */ }
  }
}

export function getAuthItem(key) {
  migrateLegacyAuthOnce();
  try { return tabStore()?.getItem(key) ?? null; } catch { return null; }
}

export function setAuthItem(key, value) {
  try { tabStore()?.setItem(key, value); } catch { /* ignore */ }
}

export function removeAuthItem(key) {
  try { tabStore()?.removeItem(key); } catch { /* ignore */ }
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

export function persistSessionTokens(payload = {}) {
  if (isSameOriginApi()) {
    removeAuthItem('token');
    removeAuthItem('access_token');
    removeAuthItem('refresh_token');
    return Boolean(
      payload?.csrf_token
      || payload?.user_id
      || payload?.access_token
      || payload?.accessToken
      || payload?.token
    );
  }
  const access = payload?.access_token || payload?.accessToken || payload?.token || null;
  const refresh = payload?.refresh_token || payload?.refreshToken || null;
  if (access) setAuthToken(access);
  if (refresh) setRefreshToken(refresh);
  return Boolean(access);
}

export function touchSessionActivity() {
  setAuthItem('session_last_activity', String(Date.now()));
}

export function clearAllClientStorage() {
  if (typeof window === 'undefined') return;
  for (const key of AUTH_STORAGE_KEYS) removeAuthItem(key);
  invalidateCache();
  void import('../offline/db.js')
    .then(({ purgeOfflinePrivacyState }) => purgeOfflinePrivacyState())
    .catch(() => {});
}

export { PROFILE_STORAGE_KEYS };
