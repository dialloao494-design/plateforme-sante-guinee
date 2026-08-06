/**
 * Pure-function unit tests for offline module (no browser required).
 * Run: npm run test:offline
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { classifyRequest, isPatientSearchUrl } from '../src/offline/entityTypes.js';
import { computeBackoffMs, buildOptimisticResponse } from '../src/offline/outbox.js';
import { mergeLastWriteWins, resolveLastWriteWins } from '../src/offline/conflict.js';

test('classifyRequest maps consultation mutations', () => {
  const r = classifyRequest('/clinical/consultations/abc', 'post');
  assert.equal(r.entityType, 'consultation');
  assert.equal(r.operation, 'create');
  assert.equal(r.queueable, true);
});

test('classifyRequest maps billing invoice create', () => {
  const r = classifyRequest('/clinical/reception/his/invoices', 'post');
  assert.equal(r.entityType, 'billing');
  assert.equal(r.domain, 'billing');
});

test('classifyRequest maps pharmacy patch', () => {
  const r = classifyRequest('/clinical/pharmacy/orders/1', 'patch');
  assert.equal(r.entityType, 'pharmacy');
  assert.equal(r.operation, 'update');
});

test('classifyRequest maps lab result create', () => {
  const r = classifyRequest('/clinical/lab/orders/9/results', 'post');
  assert.equal(r.entityType, 'lab');
});

test('isPatientSearchUrl detects search endpoints', () => {
  assert.equal(isPatientSearchUrl('/clinical/reception/his/patients/search'), true);
  assert.equal(isPatientSearchUrl('/clinical/consultations'), false);
});

test('computeBackoffMs grows exponentially with cap', () => {
  assert.equal(computeBackoffMs(1), 2000);
  assert.equal(computeBackoffMs(2), 4000);
  assert.ok(computeBackoffMs(20) <= 300_000);
});

test('buildOptimisticResponse includes offline marker fields', () => {
  const row = buildOptimisticResponse({ patient_id: 42 }, 'consultation');
  assert.equal(row.entity_type, 'consultation');
  assert.equal(row.patient_id, 42);
  assert.ok(row.id.startsWith('offline_'));
  assert.equal(row.record_version, 1);
});

test('resolveLastWriteWins prefers higher version', () => {
  const local = { record_version: 2, updated_at: '2026-01-01' };
  const remote = { record_version: 1, updated_at: '2026-02-01' };
  assert.equal(resolveLastWriteWins(local, remote), 'local');
});

test('resolveLastWriteWins uses timestamp when versions tie', () => {
  const local = { record_version: 1, updated_at: '2026-03-01' };
  const remote = { record_version: 1, updated_at: '2026-01-01' };
  assert.equal(resolveLastWriteWins(local, remote), 'local');
});

test('mergeLastWriteWins applies winner fields', () => {
  const merged = mergeLastWriteWins(
    { id: 1, note: 'local', record_version: 2, updated_at: '2026-03-01' },
    { id: 1, note: 'remote', record_version: 1, updated_at: '2026-01-01' }
  );
  assert.equal(merged.note, 'local');
  assert.equal(merged._conflict_winner, 'local');
});
