/**
 * Regression: FastAPI object `detail` (duplicate_patient 409) must surface
 * the human message — never a generic Axios status string.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  formatApiError,
  isDuplicatePatientError,
  getApiErrorDetailObject,
} from './apiError.js';

test('formatApiError reads message from object detail', () => {
  const err = {
    message: 'Request failed with status code 409',
    response: {
      status: 409,
      data: {
        detail: {
          code: 'duplicate_patient',
          message: 'Un ou plusieurs patients similaires existent déjà',
          matches: [{ id: 1, patient_number: 'PAT-001' }],
        },
      },
    },
  };
  assert.equal(
    formatApiError(err, 'Enregistrement du patient impossible'),
    'Un ou plusieurs patients similaires existent déjà'
  );
  assert.equal(isDuplicatePatientError(err), true);
  assert.equal(getApiErrorDetailObject(err)?.code, 'duplicate_patient');
  assert.equal(getApiErrorDetailObject(err)?.matches?.length, 1);
});

test('formatApiError still supports string and validation-array detail', () => {
  assert.equal(
    formatApiError({ response: { data: { detail: 'Champ invalide' } } }, 'fallback'),
    'Champ invalide'
  );
  assert.equal(
    formatApiError(
      {
        response: {
          data: {
            detail: [
              { msg: 'Field required', loc: ['body', 'gender'] },
              { msg: 'Field required', loc: ['body', 'phone'] },
            ],
          },
        },
      },
      'fallback'
    ),
    'Field required · Field required'
  );
});

test('isDuplicatePatientError is false for other 409s', () => {
  assert.equal(
    isDuplicatePatientError({
      response: { status: 409, data: { detail: { code: 'other', message: 'Conflict' } } },
    }),
    false
  );
  assert.equal(
    isDuplicatePatientError({
      response: { status: 400, data: { detail: { code: 'duplicate_patient', message: 'x' } } },
    }),
    false
  );
});
