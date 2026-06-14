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
  admin: [
    { path: '/clinical', label: 'Opérations', icon: 'dash' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'board' },
    { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'queue' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  receptionist: [
    { path: '/clinical/reception', label: 'Réception', icon: 'calendar' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'board' },
    { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'queue' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  cashier: [{ path: '/clinical/reception', label: 'Réception', icon: 'calendar' }],
  doctor: [
    { path: '/clinical/doctor', label: 'Médecin', icon: 'board' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'queue' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'calendar' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
  ],
  lab_technician: [
    { path: '/clinical/lab', label: 'Laboratoire', icon: 'queue' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
  ],
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
