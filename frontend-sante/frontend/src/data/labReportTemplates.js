/** Official AASMA lab report templates — mirrors clinic paper forms. */

export const LAB_TEMPLATES = {
  hemogram: {
    id: 'hemogram',
    title: 'Hémogramme (Mindray BC-10)',
    keywords: ['hémogramme', 'hemogramme', 'nfs', 'mindray', 'bc-10', 'bc10'],
    rows: [
      { parameter: 'GB', unit: '10^9/L', reference: '4.0 – 10.0' },
      { parameter: 'Lymph', unit: '10^9/L', reference: '0.8 – 4.0' },
      { parameter: 'Mid', unit: '10^9/L', reference: '0.1 – 1.5' },
      { parameter: 'Gran', unit: '10^9/L', reference: '2.0 – 7.0' },
      { parameter: 'Lymph%', unit: '%', reference: '20.0 – 50.0' },
      { parameter: 'Mid%', unit: '%', reference: '0.500 – 10.0' },
      { parameter: 'Gran%', unit: '%', reference: '20.0 – 70.0' },
      { parameter: 'RBC', unit: '10^12/L', reference: '4.00 – 5.50' },
      { parameter: 'HGB', unit: 'g/L', reference: '120 – 160' },
      { parameter: 'HCT', unit: 'L/L', reference: '0.400 – 0.540' },
      { parameter: 'MCV', unit: 'fL', reference: '80.0 – 100.0' },
      { parameter: 'MCH', unit: 'pg', reference: '27.0 – 34.0' },
      { parameter: 'MCHC', unit: 'g/L', reference: '320 – 360' },
      { parameter: 'RDW-CV', unit: '', reference: '0.110 – 0.160' },
      { parameter: 'RDW-SD', unit: 'fL', reference: '35.0 – 56.0' },
      { parameter: 'PLT', unit: '10^9/L', reference: '100 – 300' },
      { parameter: 'MPV', unit: 'fL', reference: '6.5 – 12.0' },
      { parameter: 'PDW', unit: '', reference: '15.0 – 17.0' },
      { parameter: 'PCT', unit: 'mL/L', reference: '1.08 – 2.82' },
      { parameter: 'P-LCR', unit: '', reference: '0.110 – 0.450' },
    ],
  },
  bu: {
    id: 'bu',
    title: 'Biochimie des urines (BU)',
    keywords: ['biochimie des urines', 'biochimie urinaire', 'bu ', 'bandelette'],
    rows: [
      { parameter: 'Leucocytes', reference: 'Négatif' },
      { parameter: 'Nitrite', reference: 'Négatif' },
      { parameter: 'PH', reference: '5.0-8.5' },
      { parameter: 'Urobilinogène', reference: 'Normal' },
      { parameter: 'Bilirubine', reference: 'Négatif' },
      { parameter: 'Sang', reference: 'Négatif' },
      { parameter: 'Densité', reference: '1.005-1.030' },
      { parameter: 'Protéine', reference: 'Négatif' },
      { parameter: 'Glucose', reference: 'Négatif' },
      { parameter: 'Cétone', reference: 'Négatif' },
    ],
  },
  ecbu: {
    id: 'ecbu',
    title: 'Examen Cytobactériologique des Urines (ECBU)',
    keywords: ['ecbu', 'cytobact', 'cytobactériologique', 'cytobacteriologique'],
    macro: 'Aspect macroscopique : urine jaune clair, culot léger',
    rows: [
      { parameter: 'Leucocytes', unit: 'mm³', reference: '<10' },
      { parameter: 'Hématies', unit: 'mm³', reference: '<10' },
      { parameter: 'Cellules épithéliales', unit: '', reference: '0-5' },
      { parameter: 'Cylindres', unit: '', reference: 'Absents' },
      { parameter: 'Cristaux', unit: '', reference: 'Absents ou rares' },
      { parameter: 'Levures', unit: '', reference: 'Absentes' },
      { parameter: 'Parasites', unit: '', reference: 'Absentes' },
      { parameter: 'Gram', unit: '', reference: 'Absent' },
      { parameter: 'Culture/identification', unit: '', reference: '' },
    ],
  },
};

export function detectLabTemplateId(testName) {
  const name = (testName || '').toLowerCase();
  for (const [id, tpl] of Object.entries(LAB_TEMPLATES)) {
    if (tpl.keywords.some((kw) => name.includes(kw))) return id;
  }
  return null;
}

export function templateRowsForExam(testName) {
  const id = detectLabTemplateId(testName);
  if (!id) return [{ parameter: testName || '', result: '', reference: '', unit: '' }];
  return LAB_TEMPLATES[id].rows.map((r) => ({
    parameter: r.parameter,
    result: '',
    reference: r.reference || '',
    unit: r.unit || '',
  }));
}
