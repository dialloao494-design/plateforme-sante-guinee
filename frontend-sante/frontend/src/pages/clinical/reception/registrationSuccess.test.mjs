import test from 'node:test';
import assert from 'node:assert/strict';
import {
  isCompleteRegistrationResponse,
  REGISTRATION_ONLINE_REQUIRED_MESSAGE,
  REGISTRATION_INCOMPLETE_MESSAGE,
} from './registrationSuccess.js';

test('accepts real HIS registration with patient_number', () => {
  assert.equal(
    isCompleteRegistrationResponse({
      id: 434,
      patient_number: 'PAT-017-000434',
      qr_token: 'AASMA-17-ABC',
    }),
    true,
  );
});

test('rejects offline queued optimistic response (no dossier ID)', () => {
  assert.equal(
    isCompleteRegistrationResponse({
      id: 'offline_abc',
      first_name: 'Awa',
      last_name: 'Diallo',
      _offline_queued: true,
    }),
    false,
  );
});

test('rejects response missing patient_number', () => {
  assert.equal(isCompleteRegistrationResponse({ id: 1, first_name: 'Awa' }), false);
  assert.equal(isCompleteRegistrationResponse({ id: 1, patient_number: '   ' }), false);
  assert.equal(isCompleteRegistrationResponse(null), false);
});

test('online-required message forbids queueing and mentions dossier number', () => {
  assert.match(REGISTRATION_ONLINE_REQUIRED_MESSAGE, /N° dossier patient/);
  assert.match(REGISTRATION_ONLINE_REQUIRED_MESSAGE, /pas été mis en file/i);
  assert.equal(REGISTRATION_INCOMPLETE_MESSAGE, REGISTRATION_ONLINE_REQUIRED_MESSAGE);
});
