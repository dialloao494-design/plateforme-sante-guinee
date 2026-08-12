import assert from 'node:assert/strict';
import test from 'node:test';

function mem() {
  const s = new Map();
  return {
    getItem: (k) => (s.has(k) ? s.get(k) : null),
    setItem: (k, v) => s.set(k, String(v)),
    removeItem: (k) => s.delete(k),
  };
}

globalThis.sessionStorage = mem();
globalThis.localStorage = mem();
globalThis.window = globalThis;
if (!import.meta.env) import.meta.env = {};

test('same-origin mode does not persist bearer tokens', async () => {
  import.meta.env.VITE_SAME_ORIGIN_API = 'true';
  const { clearAllClientStorage, getAuthToken, isSameOriginApi, persistSessionTokens } = await import(
    `./authStorage.js?sameOrigin=${Date.now()}`
  );
  clearAllClientStorage();
  persistSessionTokens({ access_token: 'a', refresh_token: 'r', csrf_token: 'c' });
  assert.equal(getAuthToken(), null);
  assert.equal(isSameOriginApi(), true);
});
