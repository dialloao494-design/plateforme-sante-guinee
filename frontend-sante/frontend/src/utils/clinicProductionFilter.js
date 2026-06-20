/** Hide test/demo/stress clinics from field onboarding views. */

const TEST_NAME_KEYWORDS = [
  'alpha',
  'beta',
  'pilote',
  'pilot',
  'field-',
  'onboard',
  'stress',
  'deployprobe',
  'e2e',
  'staging',
  'test clinic',
];

export function isProductionClinic(clinic) {
  if (!clinic?.is_active) return false;
  const name = String(clinic.name || '').toLowerCase();
  if (TEST_NAME_KEYWORDS.some((k) => name.includes(k))) return false;
  if (name === 'solo') return false;
  return true;
}

export function filterProductionClinics(clinics) {
  return (Array.isArray(clinics) ? clinics : []).filter(isProductionClinic);
}
