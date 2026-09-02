import assert from 'node:assert/strict';
import test from 'node:test';

import { getNavItemsForRole } from './navConfig.js';

for (const role of ['admin', 'clinic_admin']) {
  test(`${role} has one administration destination`, () => {
    const items = getNavItemsForRole(role, 17);
    const administrationItems = items.filter((item) => item.path.startsWith('/clinical/admin'));

    assert.deepEqual(administrationItems, [
      { path: '/clinical/admin', label: 'Administration', icon: 'shield' },
    ]);
    assert.equal(items.some((item) => item.label === 'Utilisateurs'), false);
  });
}

test('clinic doctor has a dedicated prescription register', () => {
  const items = getNavItemsForRole('doctor', 17);
  assert.equal(items.some((item) => item.path === '/clinical/prescriptions' && item.label === 'Ordonnances'), true);
});

test('delegated platform administrators do not receive owner-only controls', () => {
  const ownerPaths = getNavItemsForRole('platform_owner').map((item) => item.path);
  const delegatedPaths = getNavItemsForRole('platform_admin').map((item) => item.path);

  assert.deepEqual(ownerPaths, [
    '/platform/overview',
    '/platform/clinics',
    '/platform/system',
    '/platform/settings',
    '/platform/accounts',
  ]);
  assert.deepEqual(delegatedPaths, ['/platform/clinics']);
});
