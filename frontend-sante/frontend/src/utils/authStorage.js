/** Per-tab auth storage — tokens and role state must not leak across browser tabs. */

import { invalidateCache } from './apiCache.js';

export const AUTH_STORAGE_KEYS = [
  'token',
  'access_token',
  'user_role',
  'user_id',
  'must_change_password',
  'password_reset_required',
  'force_password_change',
  'session_last_activity',
];

function tabStore() {
  return typeof window !== 'undefined' ? sessionStorage : null;
}

export function getAuthItem(key) {
  const store = tabStore();
  if (!store) {
    return null;
  }
  const value = store.getItem(key);
  if (value != null) {
    return value;
  }
  try {
    const legacy = localStorage.getItem(key);
    if (legacy != null) {
      store.setItem(key, legacy);
      localStorage.removeItem(key);
      return legacy;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function setAuthItem(key, value) {
  const store = tabStore();
  if (!store) {
    return;
  }
  store.setItem(key, value);
  try {
    localStorage.removeItem(key);
  } catch {
    /* purge shared storage so another tab cannot read this session */
  }
}

export function removeAuthItem(key) {
  tabStore()?.removeItem(key);
  try {
    localStorage.removeItem(key);
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

export function touchSessionActivity() {
  setAuthItem('session_last_activity', String(Date.now()));
}

export function clearAllClientStorage() {
  if (typeof window === 'undefined') {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    removeAuthItem(key);
  }
  invalidateCache();
}
