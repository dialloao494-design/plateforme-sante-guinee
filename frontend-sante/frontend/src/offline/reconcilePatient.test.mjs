import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildRegistrationFingerprint,
  isTempPatientId,
  mergeReconciledPatient,
} from './reconcilePatient.js';

test('fingerprint normalizes phone and names', () => {
  const a = buildRegistrationFingerprint({
    phone: '062-011-1222',
    first_name: ' Awa ',
    last_name: 'DIALLO',
    date_of_birth: '1995-04-12',
  });
  const b = buildRegistrationFingerprint({
    phone: '620111222',
    first_name: 'awa',
    last_name: 'diallo',
    date_of_birth: '1995-04-12',
  });
  assert.equal(a, b);
});

test('isTempPatientId detects offline_* ids only', () => {
  assert.equal(isTempPatientId('offline_abcd1234'), true);
  assert.equal(isTempPatientId(437), false);
  assert.equal(isTempPatientId('PAT-017-000437'), false);
});

test('mergeReconciledPatient promotes server dossier number', () => {
  const merged = mergeReconciledPatient(
    {
      id: 'offline_abc',
      first_name: 'Awa',
      _offline_queued: true,
      _sync_status: 'queued',
      patient_number: null,
    },
    {
      id: 437,
      patient_number: 'PAT-017-000437',
      qr_token: 'AASMA-17-XYZ',
      first_name: 'Awa',
      last_name: 'Diallo',
    },
  );
  assert.equal(merged.id, 437);
  assert.equal(merged.patient_number, 'PAT-017-000437');
  assert.equal(merged._sync_status, 'synced');
  assert.equal(merged._offline_queued, false);
  assert.equal(merged._temp_id, 'offline_abc');
});
