/**
 * Role-aware home paths — keep login, guards, and “retour tableau de bord” consistent.
 */
export function getRoleHomePath(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'doctor') return '/doctor/dashboard';
  return '/dashboard';
}

/** Where a patient starts booking; doctors/admins use {@link getRoleHomePath}. */
export function getBookAppointmentPath(doctorId) {
  const id = doctorId == null ? '' : String(doctorId).trim();
  if (!id) return '/appointments';
  return `/appointments?doctor_id=${encodeURIComponent(id)}`;
}
