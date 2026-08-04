/** Per-tab auth persistence for non-secret profile state only. */

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

const PROFILE_STORAGE_KEYS = AUTH_STORAGE_KEYS.filter(
  (key) => key !== 'token' && key !== 'access_token'
);

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
  for (const key of PROFILE_STORAGE_KEYS) {
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
  return null;
}

export function setAuthToken(token) {
  void token;
  removeAuthItem('token');
  removeAuthItem('access_token');
}

export function touchSessionActivity() {
  setAuthItem('session_last_activity', String(Date.now()));
}

/** Clear auth for the current tab only. */
export function clearAllClientStorage() {
  if (typeof window === 'undefined') {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    removeAuthItem(key);
  }
  invalidateCache();
}
