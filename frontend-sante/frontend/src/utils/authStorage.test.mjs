import assert from 'node:assert/strict';
import test from 'node:test';
import {
  clearAllClientStorage,
  getAuthToken,
  getRefreshToken,
  persistSessionTokens,
  setAuthToken,
} from './authStorage.js';

// Minimal web storage polyfill for node:test
function makeMemoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  };
}
if (typeof globalThis.sessionStorage === 'undefined') {
  globalThis.sessionStorage = makeMemoryStorage();
}
if (typeof globalThis.localStorage === 'undefined') {
  globalThis.localStorage = makeMemoryStorage();
}
if (typeof globalThis.window === 'undefined') {
  globalThis.window = globalThis;
}

test('persistSessionTokens stores access + refresh for SPA bearer auth', () => {
  clearAllClientStorage();
  const ok = persistSessionTokens({
    access_token: 'access-abc',
    refresh_token: 'refresh-xyz',
  });
  assert.equal(ok, true);
  assert.equal(getAuthToken(), 'access-abc');
  assert.equal(getRefreshToken(), 'refresh-xyz');
  setAuthToken(null);
  assert.equal(getAuthToken(), null);
});

test('cookie-only login payload without tokens is detected', () => {
  clearAllClientStorage();
  const ok = persistSessionTokens({ access_token: null, refresh_token: null, csrf_token: 'x' });
  assert.equal(ok, false);
  assert.equal(getAuthToken(), null);
});
