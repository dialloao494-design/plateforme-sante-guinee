import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createProfileRequestGuard, invalidateAuthGeneration } from './authGeneration.js';

test('logout or identity switch invalidates an already-running profile request', () => {
  const request = createProfileRequestGuard();
  const current = request();
  assert.equal(current(), true);
  invalidateAuthGeneration();
  assert.equal(current(), false);
  assert.equal(request()(), true);
});

test('an older policy response cannot override the latest response in the same session', () => {
  const request = createProfileRequestGuard();
  const older = request();
  const newer = request();
  assert.equal(newer(), true);
  assert.equal(older(), false);
});
