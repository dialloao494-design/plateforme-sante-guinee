/** Navigation — each role sees only its own workflow. */

import { isClinicOptionalRole } from './clinicAccess.js';

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
  { path: '/clinical/admin#create-user', label: 'Utilisateurs', icon: 'people' },
  { path: '/clinical/pev', label: 'PEV / Vaccination', icon: 'calendar' },
  { path: '/clinical/nursing-care', label: 'Soins infirmiers', icon: 'board' },
  { path: '/clinical/patient-history', label: 'Dossier patient', icon: 'board' },
  { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'board' },
  { path: '/clinical/billing', label: 'Facturation', icon: 'calendar' },
  { path: '/clinical/discharge', label: 'Sortie patient', icon: 'queue' },
  { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
  { path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' },
  { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
  { path: '/clinical/reports', label: 'Rapports', icon: 'calendar' },
];

const ROLE_NAV = {
  admin: CLINIC_ADMIN_NAV,
  clinic_admin: CLINIC_ADMIN_NAV,
  platform_owner: [
    { path: '/platform/clinics', label: 'Cliniques', icon: 'shield' },
  ],
  platform_admin: [
    { path: '/platform/clinics', label: 'Cliniques', icon: 'shield' },
  ],
  receptionist: [
    { path: '/clinical/reception', label: 'Réception', icon: 'calendar' },
    { path: '/clinical/patient-history', label: 'Dossier patient', icon: 'board' },
    { path: '/clinical/pev', label: 'PEV / Vaccination', icon: 'calendar' },
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
    { path: '/clinical/patient-history', label: 'Dossier patient', icon: 'board' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'queue' },
    { path: '/clinical/discharge', label: 'Sortie patient', icon: 'calendar' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
    { path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' },
    { path: '/clinical/pev', label: 'PEV / Vaccination', icon: 'calendar' },
    { path: '/clinical/notifications', label: 'Notifications', icon: 'bell' },
  ],
  lab_technician: [
    { path: '/clinical/lab', label: 'Laboratoire', icon: 'queue' },
    { path: '/clinical/radiology', label: 'Radiologie', icon: 'steth' },
  ],
  pharmacist: [{ path: '/clinical/pharmacy', label: 'Pharmacie', icon: 'steth' }],
  nutritionist: [{ path: '/clinical/nutrition', label: 'Nutrition', icon: 'board' }],
  pev_agent: [{ path: '/clinical/pev', label: 'PEV / Vaccination', icon: 'calendar' }],
  nurse: [
    { path: '/clinical/nursing-care', label: 'Soins infirmiers', icon: 'board' },
    { path: '/clinical/patient-history', label: 'Dossier patient', icon: 'board' },
    { path: '/clinical/hospitalization', label: 'Hospitalisation', icon: 'queue' },
  ],
  midwife: [
    { path: '/clinical/pev', label: 'PEV / Vaccination', icon: 'calendar' },
    { path: '/clinical/nursing-care', label: 'Soins infirmiers', icon: 'board' },
  ],
};

const DOCTOR_STANDALONE_NAV = [
  { path: '/doctor/dashboard', label: 'Tableau de bord', icon: 'dash' },
  { path: '/doctor/appointments', label: 'Mes rendez-vous', icon: 'calendar' },
  { path: '/doctor/messages', label: 'Messages', icon: 'chat' },
  { path: '/teleconsultation', label: 'Téléconsultation', icon: 'video' },
  { path: '/notifications', label: 'Notifications', icon: 'bell' },
];

/** CIS-only modules — hidden when staff has no clinic_id. */
const CLINIC_ONLY_PATHS = new Set([
  '/clinical/hospitalization',
  '/clinical/discharge',
  '/clinical/radiology',
  '/clinical/nutrition',
  '/clinical/pev',
  '/clinical/nursing-care',
  '/clinical/patient-history',
  '/clinical/billing',
  '/clinical/reports',
  '/clinical/notifications',
  '/clinical/lab',
  '/clinical/pharmacy',
  '/clinical/reception',
  '/clinical/admin',
  '/clinical',
]);

function filterNavByClinic(items, clinicId, role) {
  if (clinicId != null || isClinicOptionalRole(role)) {
    return items;
  }
  return items.filter((item) => !CLINIC_ONLY_PATHS.has(item.path));
}

export function getNavItemsForRole(role, clinicId = null) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return PATIENT_NAV_ITEMS;
  if (r === 'doctor' && clinicId == null) {
    return DOCTOR_STANDALONE_NAV;
  }
  return filterNavByClinic(ROLE_NAV[r] || [], clinicId, r);
}

export function getNavSectionTitle(role) {
  const r = String(role || '').toLowerCase();
  if (r === 'patient') return 'Mon espace';
  if (r === 'platform_owner') return 'Plateforme';
  if (r === 'admin' || r === 'clinic_admin') return 'Pilotage';
  if (r === 'platform_admin') return 'Plateforme';
  return 'Mon poste';
}
