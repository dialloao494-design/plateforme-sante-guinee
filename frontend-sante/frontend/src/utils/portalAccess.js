/** Patient portal — self-service care journeys only. */
export const PATIENT_PORTAL_ROLES = ['patient'];

/** Clinic portal — CIS staff workflows (tenant-scoped). */
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
];

export function normalizeRole(role) {
  return String(role || '').toLowerCase();
}

export function isClinicPortalRole(role) {
  return CLINIC_PORTAL_ROLES.includes(normalizeRole(role));
}

export function isPatientPortalRole(role) {
  return normalizeRole(role) === 'patient';
}

const PORTAL_LABELS = {
  admin: 'Pilotage clinique',
  clinic_admin: 'Pilotage clinique',
  platform_owner: 'Propriétaire plateforme',
  platform_admin: 'Admin plateforme',
  receptionist: 'Réception',
  cashier: 'Caisse',
  doctor: 'Consultation',
  lab_technician: 'Laboratoire',
  pharmacist: 'Pharmacie',
  patient: 'Portail Patient',
};

export function portalLabel(role) {
  const r = normalizeRole(role);
  return PORTAL_LABELS[r] || 'Portail Santé';
}

export function portalSubtitle(role) {
  const r = normalizeRole(role);
  if (r === 'patient') return 'Guinée · Soins & rendez-vous';
  if (r === 'platform_owner') return 'Guinée · Propriété plateforme';
  if (r === 'platform_admin') return 'Guinée · Administration nationale';
  if (r === 'admin' || r === 'clinic_admin') return 'Guinée · Opérations';
  return 'Guinée · Parcours patient';
}
