import assert from 'node:assert/strict';
import test from 'node:test';

import { readClinicalPatientId, updateClinicalPatientId } from './clinicalPatientRoute.js';

test('reads the canonical patient id without changing other route state', () => {
  const params = new URLSearchParams('patient=42&tab=workflow');
  assert.equal(readClinicalPatientId(params), '42');
  assert.equal(params.get('tab'), 'workflow');
});

test('updates patient context while preserving module-specific route state', () => {
  const next = updateClinicalPatientId(new URLSearchParams('tab=stock&status=pending'), 81);
  assert.equal(next.toString(), 'tab=stock&status=pending&patient=81');
});

test('clears only patient context', () => {
  const next = updateClinicalPatientId(new URLSearchParams('patient=81&tab=stock'), '');
  assert.equal(next.toString(), 'tab=stock');
});
