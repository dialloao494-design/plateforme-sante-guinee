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

test('soft throttle 429 is not presented as a hard account lock', () => {
  const msg = toUserFriendlyLoginMessage({
    response: {
      status: 429,
      data: { detail: 'Too many failed login attempts. Slow down and try again.' },
    },
  });
  assert.match(msg, /Trop de tentatives incorrectes/i);
  assert.doesNotMatch(msg, /verrouillé/i);
});

test('generic rate-limit 429 does not claim account lock', () => {
  const msg = toUserFriendlyLoginMessage({
    response: {
      status: 429,
      data: { detail: 'Rate limit exceeded' },
    },
  });
  assert.match(msg, /Trop de tentatives/i);
  assert.doesNotMatch(msg, /verrouillé/i);
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
