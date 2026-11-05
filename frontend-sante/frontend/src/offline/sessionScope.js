import { getAuthItem } from '../utils/authStorage.js';
import { buildOwnerKey } from './db.js';

/** Read the authenticated user/clinic scope for offline ownership. */
export function readOfflineOwnerScope() {
  let userId = getAuthItem('user_id');
  let clinicId = null;
  try {
    const raw = getAuthItem('sg_auth_profile');
    if (raw) {
      const profile = JSON.parse(raw);
      if (profile?.id != null) userId = String(profile.id);
      if (profile?.clinic_id != null) clinicId = String(profile.clinic_id);
    }
  } catch {
    /* ignore */
  }
  return {
    userId: userId || null,
    clinicId: clinicId || null,
    ownerKey: buildOwnerKey(userId, clinicId),
  };
}

/** Legacy profiles retain offline support until the server supplies a policy. */
export function isOfflineAllowed(profile) {
  if (profile !== undefined) return profile?.offline_workstations_enabled !== false;
  try {
    return JSON.parse(getAuthItem('sg_auth_profile') || '{}').offline_workstations_enabled !== false;
  } catch {
    return false;
  }
}

export function readOfflineProfile() {
  try { return JSON.parse(getAuthItem('sg_auth_profile') || '{}'); }
  catch { return {}; }
}
