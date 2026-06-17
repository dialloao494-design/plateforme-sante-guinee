/** Role-aware home paths — one dedicated dashboard per role. */

export const CLINIC_PORTAL_ROLES = [
  'admin',
  'clinic_admin',
  'platform_owner',
  'platform_admin',
  'receptionist',
  'cashier',
  'doctor',
  'lab_technician',
  'pharmacist',
  'nutritionist',
  'midwife',
];

export function isClinicStaffRole(role) {
  return CLINIC_PORTAL_ROLES.includes(String(role || '').toLowerCase());
}

const ROLE_HOME = {
  admin: '/clinical',
  clinic_admin: '/clinical',
  platform_owner: '/platform',
  platform_admin: '/users',
  receptionist: '/clinical/reception',
  cashier: '/clinical/reception',
  doctor: '/clinical/doctor',
  lab_technician: '/clinical/lab',
  pharmacist: '/clinical/pharmacy',
  nutritionist: '/clinical/nutrition',
  midwife: '/clinical/midwife',
  patient: '/dashboard',
};

export function getRoleHomePath(role, clinicId) {
  const r = String(role || '').toLowerCase();
  if (r === 'doctor' && !clinicId) {
    return '/doctor/dashboard';
  }
  return ROLE_HOME[r] || '/dashboard';
}

export function getBookAppointmentPath(doctorId) {
  const id = doctorId == null ? '' : String(doctorId).trim();
  if (!id) return '/appointments';
  return `/appointments?doctor_id=${encodeURIComponent(id)}`;
}
