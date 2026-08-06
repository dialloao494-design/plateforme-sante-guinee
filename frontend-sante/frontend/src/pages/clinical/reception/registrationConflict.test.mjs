/**
 * Regression lock for reception duplicate_patient handling.
 *
 * These tests encode the production clinic blocker:
 * - object detail 409 must not surface as Axios "Request failed with status code 409"
 * - confirm_duplicate must be prepared on the pending payload
 * - RegisterTab must keep the confirm UI contract (data-testid)
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import {
  DUPLICATE_PATIENT_CODE,
  resolveRegistrationConflict,
  shouldShowDuplicatePanel,
} from './registrationConflict.js';

const here = path.dirname(fileURLToPath(import.meta.url));

function duplicateErr(matches = [{ id: 1, patient_number: 'PAT-001', match_reasons: ['phone'] }]) {
  return {
    message: 'Request failed with status code 409',
    response: {
      status: 409,
      data: {
        detail: {
          code: DUPLICATE_PATIENT_CODE,
          message: 'Un ou plusieurs patients similaires existent déjà',
          matches,
        },
      },
    },
  };
}

test('resolveRegistrationConflict maps duplicate_patient 409 to confirmable state', () => {
  const payload = { first_name: 'Aissatou', phone: '622000111', confirm_duplicate: false };
  const conflict = resolveRegistrationConflict(duplicateErr(), payload);

  assert.equal(conflict.kind, 'duplicate_patient');
  assert.match(conflict.message, /patients similaires/i);
  assert.doesNotMatch(conflict.message, /Request failed with status code 409/i);
  assert.equal(conflict.matches.length, 1);
  assert.equal(conflict.pendingPayload.confirm_duplicate, true);
  assert.equal(conflict.pendingPayload.phone, '622000111');
  assert.equal(shouldShowDuplicatePanel(conflict), true);
});

test('resolveRegistrationConflict keeps generic registration errors opaque-safe', () => {
  const conflict = resolveRegistrationConflict(
    { message: 'Network Error', response: { status: 500, data: { detail: 'boom' } } },
    { phone: '1' }
  );
  assert.equal(conflict.kind, 'error');
  assert.equal(conflict.matches.length, 0);
  assert.equal(conflict.pendingPayload, null);
  assert.equal(shouldShowDuplicatePanel(conflict), false);
  assert.doesNotMatch(conflict.message, /Request failed with status code/i);
});

test('RegisterTab keeps duplicate panel + confirm contract', () => {
  const src = fs.readFileSync(path.join(here, 'tabs', 'RegisterTab.jsx'), 'utf8');
  assert.match(src, /data-testid="duplicate-patient-panel"/);
  assert.match(src, /data-testid="confirm-duplicate-register"/);
  assert.match(src, /handleConfirmDuplicateRegister/);
  assert.match(src, /openExistingDuplicate/);
});

test('useReceptionDashboard uses shared resolveRegistrationConflict (no ad-hoc 409 fork)', () => {
  const src = fs.readFileSync(path.join(here, 'hooks', 'useReceptionDashboard.jsx'), 'utf8');
  assert.match(src, /resolveRegistrationConflict/);
  assert.match(src, /from '\.\.\/registrationConflict\.js'/);
  // Guard against reintroducing raw Axios 409 messaging path without the helper.
  assert.doesNotMatch(src, /Request failed with status code 409/);
});
