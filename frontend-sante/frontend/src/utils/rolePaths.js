/** Role-aware home paths — one dedicated dashboard per role. */

export const CLINIC_PORTAL_ROLES = [
  'admin',
  'clinic_admin',
  'platform_admin',
  'receptionist',
  'cashier',
  'doctor',
  'lab_technician',
  'pharmacist',
];

export function isClinicStaffRole(role) {
  return CLINIC_PORTAL_ROLES.includes(String(role || '').toLowerCase());
}

const ROLE_HOME = {
  admin: '/clinical',
  clinic_admin: '/clinical',
  platform_admin: '/users',
  receptionist: '/clinical/reception',
  cashier: '/clinical/reception',
  doctor: '/clinical/doctor',
  lab_technician: '/clinical/lab',
  pharmacist: '/clinical/pharmacy',
  patient: '/dashboard',
};

export function getRoleHomePath(role) {
  const r = String(role || '').toLowerCase();
  return ROLE_HOME[r] || '/dashboard';
}

export function getBookAppointmentPath(doctorId) {
  const id = doctorId == null ? '' : String(doctorId).trim();
  if (!id) return '/appointments';
  return `/appointments?doctor_id=${encodeURIComponent(id)}`;
}
