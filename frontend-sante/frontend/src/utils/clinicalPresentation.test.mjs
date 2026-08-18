import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatClinicalDate,
  formatClinicalDateTime,
  formatClinicalTime,
  formatGNF,
  patientDisplayName,
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
