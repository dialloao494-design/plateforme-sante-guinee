/** Centralized client auth storage keys and cleanup. */

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

export function touchSessionActivity() {
  if (typeof window === 'undefined') {
    return;
  }
  localStorage.setItem('session_last_activity', String(Date.now()));
}

export function clearAllClientStorage() {
  if (typeof window === 'undefined') {
    return;
  }
  for (const key of AUTH_STORAGE_KEYS) {
    localStorage.removeItem(key);
  }
  try {
    sessionStorage.clear();
  } catch {
    // ignore
  }
}
