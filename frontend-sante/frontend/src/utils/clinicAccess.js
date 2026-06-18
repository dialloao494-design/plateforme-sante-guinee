import { normalizeRole } from './roleAccess.js';

/** Roles that may open /clinical/* without a clinic_id (cross-tenant operators). */
export const CLINIC_OPTIONAL_ROLES = ['platform_owner', 'platform_admin'];

/** Roles allowed to create hospital rooms/beds. */
export const HOSPITAL_BED_ADMIN_ROLES = [
  'clinic_admin',
  'admin',
  'receptionist',
  'platform_owner',
  'platform_admin',
];

/** Roles allowed to record nutrition assessments (doctors are read-only). */
export const NUTRITION_WRITE_ROLES = ['nutritionist', 'midwife', 'clinic_admin', 'admin'];

export function isClinicOptionalRole(role) {
  return CLINIC_OPTIONAL_ROLES.includes(normalizeRole(role));
}

export function userNeedsClinicAssignment(user, pathname = '') {
  if (!user || !String(pathname).startsWith('/clinical')) {
    return false;
  }
  if (isClinicOptionalRole(user.role || user.user_role)) {
    return false;
  }
  return user.clinic_id == null;
}

export function userCanManageHospitalBeds(role) {
  return HOSPITAL_BED_ADMIN_ROLES.includes(normalizeRole(role));
}

export function userCanWriteNutrition(role) {
  return NUTRITION_WRITE_ROLES.includes(normalizeRole(role));
}
