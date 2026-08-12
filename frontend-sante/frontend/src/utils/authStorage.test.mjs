import assert from 'node:assert/strict';
import test from 'node:test';
import {
  clearAllClientStorage,
  getAuthToken,
  getRefreshToken,
  isSameOriginApi,
  persistSessionTokens,
  setAuthToken,
  setRefreshToken,
} from './authStorage.js';

function makeMemoryStorage() {
  const store = new Map();
  return {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
  };
}
if (typeof globalThis.sessionStorage === 'undefined') globalThis.sessionStorage = makeMemoryStorage();
if (typeof globalThis.localStorage === 'undefined') globalThis.localStorage = makeMemoryStorage();
if (typeof globalThis.window === 'undefined') globalThis.window = globalThis;

test('persistSessionTokens stores access + refresh for SPA bearer auth', () => {
  delete process.env.VITE_SAME_ORIGIN_API;
  clearAllClientStorage();
  const ok = persistSessionTokens({ access_token: 'access-abc', refresh_token: 'refresh-xyz' });
  assert.equal(ok, true);
  assert.equal(getAuthToken(), 'access-abc');
  assert.equal(getRefreshToken(), 'refresh-xyz');
});

test('cookie-only login payload without tokens is detected', () => {
  delete process.env.VITE_SAME_ORIGIN_API;
  clearAllClientStorage();
  const ok = persistSessionTokens({ access_token: null, refresh_token: null, csrf_token: 'x' });
  assert.equal(ok, false);
});

test('same-origin mode does not persist bearer tokens in sessionStorage', () => {
  process.env.VITE_SAME_ORIGIN_API = 'true';
  clearAllClientStorage();
  setAuthToken('stale');
  setRefreshToken('stale');
  const ok = persistSessionTokens({ access_token: 'a', refresh_token: 'b', csrf_token: 'c' });
  assert.equal(ok, true);
  assert.equal(getAuthToken(), null);
  assert.equal(isSameOriginApi(), true);
  delete process.env.VITE_SAME_ORIGIN_API;
});
