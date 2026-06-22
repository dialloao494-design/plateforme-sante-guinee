/**
 * Per-clinic module visibility — AASMA vs Koloma workflows.
 */

export const KOLOMA_CLINIC_ID = 13;
export const AASMA_CLINIC_ID = 17;

/** Nav paths always available when clinic has clinical access. */
const CORE_PATHS = new Set([
  '/clinical/reception',
  '/clinical/doctor',
  '/clinical/lab',
  '/clinical/pharmacy',
  '/clinical/billing',
  '/clinical/admin',
  '/clinical',
]);

/** Koloma-only / extended CIS modules. */
const EXTENDED_PATHS = new Set([
  '/clinical/pev',
  '/clinical/nutrition',
  '/clinical/nursing-care',
  '/clinical/hospitalization',
  '/clinical/discharge',
  '/clinical/radiology',
]);

export function clinicHasExtendedModules(clinicId) {
  return Number(clinicId) === KOLOMA_CLINIC_ID;
}

export function isNavPathAllowedForClinic(path, clinicId) {
  if (!path || !String(path).startsWith('/clinical')) return true;
  if (CORE_PATHS.has(path)) return true;
  if (EXTENDED_PATHS.has(path)) {
    return clinicHasExtendedModules(clinicId);
  }
  return true;
}

export function filterNavItemsForClinic(items, clinicId) {
  if (!Array.isArray(items)) return [];
  return items.filter((item) => isNavPathAllowedForClinic(item.path, clinicId));
}

/** Visit workflow options at reception — hide PEV/nutrition paths for AASMA. */
export function getVisitWorkflowOptions(clinicId) {
  const base = [
    { value: '', label: 'Auto (selon âge et clinique)' },
    { value: 'adult_doctor', label: 'Adulte — Consultation médicale' },
    { value: 'adult_lab', label: 'Adulte — Laboratoire' },
    { value: 'adult_pharmacy', label: 'Adulte — Pharmacie' },
  ];
  if (clinicHasExtendedModules(clinicId)) {
    return [
      ...base,
      { value: 'child', label: 'Enfant — Nutrition + PEV + Médecin' },
      { value: 'adult_midwife', label: 'Adulte — Sage-femme' },
    ];
  }
  return base;
}

export function getClinicDisplayName(clinicId, fallback = '') {
  if (Number(clinicId) === AASMA_CLINIC_ID) return 'CLINIQUE AASMA';
  if (Number(clinicId) === KOLOMA_CLINIC_ID) return 'Centre de Santé Koloma';
  return fallback;
}
