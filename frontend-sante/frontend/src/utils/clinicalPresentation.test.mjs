import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatClinicalDate,
  formatClinicalDateTime,
  formatClinicalStatus,
  formatClinicalTime,
  formatGNF,
  patientAddress,
  patientAge,
  patientDisplayName,
  patientGenderLabel,
} from './clinicalPresentation.js';

test('clinical formatters use Guinea French presentation and safe fallbacks', () => {
  assert.match(formatClinicalDate('2026-08-18T14:05:00Z'), /18/);
  assert.match(formatClinicalDateTime('2026-08-18T14:05:00Z'), /2026/);
  assert.match(formatClinicalTime('2026-08-18T14:05:00Z'), /\d{2}/);
  assert.equal(formatClinicalDate('invalid'), '—');
  assert.equal(formatClinicalDateTime(null), '—');
});

test('GNF formatter produces stable zero-decimal clinical currency', () => {
  assert.match(formatGNF(5105000), /5[\s\u202f]105[\s\u202f]000 GNF/);
  assert.equal(formatGNF('not-a-number'), '0 GNF');
});

test('patient display names prioritize canonical server identity', () => {
  assert.equal(patientDisplayName({ full_name: 'BARRY Maimouna', first_name: 'Wrong' }), 'BARRY Maimouna');
  assert.equal(patientDisplayName({ first_name: 'Maimouna', last_name: 'Barry' }), 'Barry Maimouna');
  assert.equal(patientDisplayName(null), 'Identité non renseignée');
});

test('patient presentation handles recorded and calculated demographics', () => {
  assert.equal(patientAge({ age: 7 }), '7');
  assert.equal(patientAge({ date_of_birth: '2000-09-01' }, '—', new Date('2026-08-18')), '25');
  assert.equal(patientAge({}, 'Inconnu'), 'Inconnu');
  assert.equal(patientGenderLabel('F'), 'Féminin');
  assert.equal(patientGenderLabel('male'), 'Masculin');
  assert.equal(patientAddress({ quartier: 'Koloma', city: 'Conakry', region: 'Conakry' }), 'Koloma, Conakry, Conakry');
});

test('clinical statuses are translated without hiding unknown server values', () => {
  assert.equal(formatClinicalStatus('sample_collected'), 'Prélèvement effectué');
  assert.equal(formatClinicalStatus('partially_paid'), 'Partiellement payé');
  assert.equal(formatClinicalStatus('custom_review'), 'custom_review');
  assert.equal(formatClinicalStatus(''), '—');
});
