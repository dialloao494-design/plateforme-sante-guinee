import assert from 'node:assert/strict';
import test from 'node:test';
import { toUserFriendlyLoginMessage } from './loginErrors.js';

test('429 lockout is never a generic retry message', () => {
  const msg = toUserFriendlyLoginMessage({
    response: {
      status: 429,
      data: { detail: 'Account temporarily locked due to failed login attempts. Try again later.' },
    },
  });
  assert.match(msg, /verrouillé/i);
  assert.doesNotMatch(msg, /^Une erreur est survenue/);
});

test('401 shows incorrect credentials', () => {
  assert.equal(
    toUserFriendlyLoginMessage({
      response: { status: 401, data: { detail: 'Incorrect email or password' } },
    }),
    'Email ou mot de passe incorrect'
  );
});

test('session bootstrap cookie failure is actionable', () => {
  const msg = toUserFriendlyLoginMessage({
    message: 'Missing authentication token',
    response: { status: undefined, data: {} },
  });
  assert.match(msg, /Session non établie|cache/i);
});
