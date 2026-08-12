import test from 'node:test';
import assert from 'node:assert/strict';
import {
  classifyRegistrationResponse,
  isCompleteRegistrationResponse,
  isQueuedRegistrationResponse,
  REG_STATUS,
  REGISTRATION_QUEUED_MESSAGE,
  REGISTRATION_INCOMPLETE_MESSAGE,
} from './registrationSuccess.js';

test('accepts real HIS registration with patient_number', () => {
  assert.equal(
    classifyRegistrationResponse({
      id: 434,
      patient_number: 'PAT-017-000434',
      qr_token: 'AASMA-17-ABC',
    }),
    REG_STATUS.COMPLETE,
  );
  assert.equal(
    isCompleteRegistrationResponse({
      id: 434,
      patient_number: 'PAT-017-000434',
    }),
    true,
  );
});

test('treats offline queued optimistic response as queued (not failure)', () => {
  const queued = {
    id: 'offline_abc',
    first_name: 'Awa',
    last_name: 'Diallo',
    _offline_queued: true,
    _sync_status: 'queued',
  };
  assert.equal(classifyRegistrationResponse(queued), REG_STATUS.QUEUED);
  assert.equal(isQueuedRegistrationResponse(queued), true);
  assert.equal(isCompleteRegistrationResponse(queued), false);
});

test('rejects response missing patient_number and not queued', () => {
  assert.equal(classifyRegistrationResponse({ id: 1, first_name: 'Awa' }), REG_STATUS.INCOMPLETE);
  assert.equal(isCompleteRegistrationResponse({ id: 1, patient_number: '   ' }), false);
  assert.equal(classifyRegistrationResponse(null), REG_STATUS.INCOMPLETE);
});

test('queued message tells staff not to re-enter the same patient', () => {
  assert.match(REGISTRATION_QUEUED_MESSAGE, /hors ligne|synchronisation/i);
  assert.match(REGISTRATION_QUEUED_MESSAGE, /Ne resaisissez|N° dossier/i);
  assert.match(REGISTRATION_INCOMPLETE_MESSAGE, /non finalisé/i);
});
