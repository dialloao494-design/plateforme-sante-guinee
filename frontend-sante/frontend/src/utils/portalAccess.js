/** Patient portal — self-service care journeys only. */
export const PATIENT_PORTAL_ROLES = ['patient'];

/** Clinic portal — CIS staff workflows (tenant-scoped). */
export const CLINIC_PORTAL_ROLES = [
  'admin',
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
  receptionist: 'Réception',
  cashier: 'Réception',
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
  if (r === 'admin') return 'Guinée · Opérations';
  return 'Guinée · Parcours patient';
}
