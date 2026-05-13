/**
 * Maps backend / seed specialty strings (often English) to French clinical labels for UI.
 */
const SPECIALTY_MAP = new Map(
  Object.entries({
    Pédiatrie: 'Pédiatrie',
    pédiatrie: 'Pédiatrie',
    Pediatrics: 'Pédiatrie',
    pediatric: 'Pédiatrie',
    'Médecine générale': 'Médecine générale',
    'General Medicine': 'Médecine générale',
    'general medicine': 'Médecine générale',
    Généraliste: 'Médecine générale',
    généraliste: 'Médecine générale',
    Dermatology: 'Dermatologie',
    dermatology: 'Dermatologie',
    Dermatologie: 'Dermatologie',
    Cardiology: 'Cardiologie',
    Cardiologie: 'Cardiologie',
    Gynecology: 'Gynécologie',
    Gynécologie: 'Gynécologie',
    Ophtalmologie: 'Ophtalmologie',
    Ophthalmology: 'Ophtalmologie',
    ORL: 'ORL',
    Psychiatrie: 'Psychiatrie',
    Psychiatry: 'Psychiatrie',
  }).map(([k, v]) => [k.toLowerCase(), v])
);

export function formatSpecialtyLabel(raw) {
  if (raw == null || String(raw).trim() === '') {
    return 'Médecine générale';
  }
  const key = String(raw).trim().toLowerCase();
  return SPECIALTY_MAP.get(key) || String(raw).trim();
}
