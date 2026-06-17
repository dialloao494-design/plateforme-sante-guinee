/** Navigation — each role sees only its own workflow. */

export const PATIENT_NAV_ITEMS = [
  { path: '/dashboard', label: 'Tableau de bord', icon: 'dash' },
  { path: '/my-records', label: 'Dossier médical', icon: 'board' },
  { path: '/appointments', label: 'Mes rendez-vous', icon: 'calendar' },
  { path: '/doctors', label: 'Médecins', icon: 'steth' },
  { path: '/teleconsultation', label: 'Téléconsultation', icon: 'video' },
  { path: '/notifications', label: 'Notifications', icon: 'bell' },
];

const CLINIC_ADMIN_NAV = [
  { path: '/clinical', label: 'Opérations', icon: 'dash' },
  { path: '/clinical/admin', label: 'Administration', icon: 'shield' },
  { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'board' },
  { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
  { path: '/clinical/discharge', label: 'Sortie patient', icon: 'queue' },
  { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
  { path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' },
  { path: '/clinical/immunization', label: 'PEV / Vaccination', icon: 'calendar' },
  { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
  { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
];

const ROLE_NAV = {
  admin: CLINIC_ADMIN_NAV,
  clinic_admin: CLINIC_ADMIN_NAV,
  platform_owner: [
    { path: '/platform', label: 'Console plateforme', icon: 'shield' },
    { path: '/users', label: 'Utilisateurs', icon: 'people' },
    { path: '/clinical/admin', label: 'Administration', icon: 'shield' },
    { path: '/clinical', label: 'Opérations', icon: 'dash' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  platform_admin: [
    { path: '/users', label: 'Utilisateurs', icon: 'people' },
    { path: '/clinical', label: 'Opérations', icon: 'dash' },
    { path: '/clinical/admin', label: 'Administration', icon: 'shield' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  receptionist: [
    { path: '/clinical/reception', label: 'Réception', icon: 'calendar' },
    { path: '/clinical/immunization', label: 'PEV / Vaccination', icon: 'calendar' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'board' },
    { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'queue' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  cashier: [
    { path: '/clinical/reception', label: 'Réception', icon: 'calendar' },
    { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
    { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
  ],
  doctor: [
    { path: '/clinical/doctor', label: 'Médecin', icon: 'board' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'queue' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'calendar' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
    { path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' },
    { path: '/clinical/immunization', label: 'PEV / Vaccination', icon: 'calendar' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
  ],
  lab_technician: [
    { path: '/clinical/lab', label: 'Laboratoire', icon: 'queue' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
  ],
  pharmacist: [{ path: '/clinical/pharmacy', label: 'Pharmacie', icon: 'steth' }],
  nutritionist: [{ path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' }],
  midwife: [
    { path: '/clinical/midwife', label: 'Sage-femme', icon: 'board' },
    { path: '/clinical/immunization', label: 'PEV / Vaccination', icon: 'calendar' },
    { path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' },
  ],
};

export function getNavItemsForRole(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return PATIENT_NAV_ITEMS;
  return ROLE_NAV[r] || [];
}

export function getNavSectionTitle(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return 'Mon espace';
  if (r === 'platform_owner') return 'Plateforme';
  if (r === 'admin' || r === 'clinic_admin') return 'Pilotage';
  if (r === 'platform_admin') return 'Plateforme';
  return 'Mon poste';
}
