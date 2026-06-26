/** Shared auth persistence — survives refresh and works across browser tabs. */

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
  'sg_auth_profile',
];

function persistStore() {
  return typeof window !== 'undefined' ? localStorage : null;
}

function legacyTabStore() {
  return typeof window !== 'undefined' ? sessionStorage : null;
}

export function getAuthItem(key) {
  const store = persistStore();
  if (!store) {
    return null;
  }
  try {
    const value = store.getItem(key);
    if (value != null) {
      return value;
    }
  } catch {
    /* ignore */
  }
  try {
    const legacy = legacyTabStore()?.getItem(key);
    if (legacy != null) {
      store.setItem(key, legacy);
      legacyTabStore()?.removeItem(key);
      return legacy;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function setAuthItem(key, value) {
  const store = persistStore();
  if (!store) {
    return;
  }
  try {
    store.setItem(key, value);
  } catch {
    /* ignore quota errors */
  }
  try {
    legacyTabStore()?.removeItem(key);
  } catch {
    /* ignore */
  }
}

export function removeAuthItem(key) {
  try {
    persistStore()?.removeItem(key);
  } catch {
    /* ignore */
  }
  try {
    legacyTabStore()?.removeItem(key);
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
