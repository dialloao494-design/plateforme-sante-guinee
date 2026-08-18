import assert from 'node:assert/strict';
import test from 'node:test';
import { readReceptionRouteState, updateReceptionRouteState } from './routeState.js';

test('reads a supported reception workflow and patient', () => {
  assert.deepEqual(readReceptionRouteState(new URLSearchParams('tab=admission&patient=42')), {
    tab: 'admission',
    patientId: '42',
  });
});

test('falls back to dashboard for an unknown workflow', () => {
  assert.equal(readReceptionRouteState(new URLSearchParams('tab=unknown')).tab, 'dashboard');
});

test('updates workflow without losing patient context', () => {
  const next = updateReceptionRouteState(new URLSearchParams('patient=42'), { tab: 'billing' });
  assert.equal(next.toString(), 'patient=42&tab=billing');
});

test('clears default workflow and patient from the URL', () => {
  const next = updateReceptionRouteState(new URLSearchParams('patient=42&tab=billing'), {
    tab: 'dashboard',
    patientId: '',
  });
  assert.equal(next.toString(), '');
});
