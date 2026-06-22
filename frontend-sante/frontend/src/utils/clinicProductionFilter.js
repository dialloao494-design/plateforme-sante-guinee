/** Production clinics only — hide test/demo/stress duplicates. */

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

const TEST_EMAIL_SUFFIXES = ['@sante-gn.test', '@pilot.local', '@clinic.test', '@aasma-clinic.gn', '@field.local'];

function clinicFamilyKey(name) {
  const n = String(name || '').toLowerCase();
  if (n.includes('koloma')) return 'koloma';
  if (n.includes('aasma')) return 'aasma';
  return n.trim();
}

export function isTestStaffEmail(email) {
  const e = String(email || '').toLowerCase();
  if (TEST_EMAIL_SUFFIXES.some((s) => e.endsWith(s))) return true;
  if (/field\.(verify|probe)/.test(e)) return true;
  if (/pwtest|\.probe\./.test(e)) return true;
  return false;
}

export function isProductionClinic(clinic) {
  if (!clinic?.is_active) return false;
  const name = String(clinic.name || '').toLowerCase();
  if (TEST_NAME_KEYWORDS.some((k) => name.includes(k))) return false;
  if (name === 'solo') return false;
  return true;
}

/** Keep newest clinic per family (e.g. one Koloma, one Aasma). */
export function dedupeProductionClinics(clinics) {
  const best = new Map();
  for (const clinic of clinics) {
    const key = clinicFamilyKey(clinic.name);
    const prev = best.get(key);
    if (!prev || clinic.id > prev.id) best.set(key, clinic);
  }
  return Array.from(best.values()).sort((a, b) =>
    String(a.name || '').localeCompare(String(b.name || ''), 'fr')
  );
}

export function filterProductionClinics(clinics) {
  return dedupeProductionClinics(
    (Array.isArray(clinics) ? clinics : []).filter(isProductionClinic)
  );
}
