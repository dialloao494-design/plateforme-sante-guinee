/** Navigation — each role sees only its own workflow. */

export const PATIENT_NAV_ITEMS = [
  { path: '/dashboard', label: 'Tableau de bord', icon: 'dash' },
  { path: '/my-records', label: 'Dossier médical', icon: 'board' },
  { path: '/appointments', label: 'Mes rendez-vous', icon: 'calendar' },
  { path: '/doctors', label: 'Médecins', icon: 'steth' },
  { path: '/teleconsultation', label: 'Téléconsultation', icon: 'video' },
  { path: '/notifications', label: 'Notifications', icon: 'bell' },
];

const ROLE_NAV = {
  admin: [{ path: '/clinical', label: 'Opérations', icon: 'dash' }],
  receptionist: [{ path: '/clinical/reception', label: 'Réception', icon: 'calendar' }],
  cashier: [{ path: '/clinical/reception', label: 'Réception', icon: 'calendar' }],
  doctor: [{ path: '/clinical/doctor', label: 'Médecin', icon: 'board' }],
  lab_technician: [{ path: '/clinical/lab', label: 'Laboratoire', icon: 'queue' }],
  pharmacist: [{ path: '/clinical/pharmacy', label: 'Pharmacie', icon: 'steth' }],
};

export function getNavItemsForRole(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return PATIENT_NAV_ITEMS;
  return ROLE_NAV[r] || [];
}

export function getNavSectionTitle(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return 'Mon espace';
  if (r === 'admin') return 'Pilotage';
  return 'Mon poste';
}
