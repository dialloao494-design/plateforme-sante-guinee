/** Session-only storage for temp passwords shown once after create/reset. */

export function credStorageKey(clinicId) {
  return `platform_staff_creds_${clinicId}`;
}

export function loadSessionCreds(clinicId) {
  try {
    const raw = sessionStorage.getItem(credStorageKey(clinicId));
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveSessionCred(clinicId, userId, password) {
  const all = loadSessionCreds(clinicId);
  all[userId] = { password, at: Date.now() };
  sessionStorage.setItem(credStorageKey(clinicId), JSON.stringify(all));
}

export function genStaffPassword(prefix = 'Clinic') {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let s = prefix;
  for (let i = 0; i < 6; i += 1) s += chars[Math.floor(Math.random() * chars.length)];
  return `${s}!`;
}

export function displaySessionPassword(creds, userId) {
  return creds[userId]?.password || 'Masqué';
}
