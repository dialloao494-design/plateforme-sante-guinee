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
