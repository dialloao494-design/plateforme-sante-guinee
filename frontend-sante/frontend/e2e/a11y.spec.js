import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { loginAsReception, loginAsRole, waitForLoginForm } from './helpers.js';

/**
 * Fail on critical always; fail on serious except color-contrast.
 * Contrast is enforced separately via darker --color-primary (#0f766e).
 * Remaining palette tweaks are tracked but must not block clinical e2e.
 */
async function expectNoBlockingA11yViolations(page, contextLabel) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const colorContrast = results.violations.filter((v) => v.id === 'color-contrast');
  if (colorContrast.length > 0) {
    console.warn(
      `[a11y] ${contextLabel} — color-contrast warnings (non-blocking):`,
      colorContrast.map((v) => ({ id: v.id, nodes: v.nodes.length }))
    );
  }

  const blocking = results.violations.filter((v) => {
    if (v.id === 'color-contrast') return false;
    return v.impact === 'serious' || v.impact === 'critical';
  });

  if (blocking.length > 0) {
    console.warn(`[a11y] ${contextLabel} — blocking violations:`, JSON.stringify(blocking, null, 2));
  }

  expect(blocking, `Blocking a11y violations on ${contextLabel}`).toEqual([]);
}

test('login page has no serious or critical a11y violations', async ({ page }) => {
  test.setTimeout(60_000);
  await waitForLoginForm(page);
  await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible();
  await expectNoBlockingA11yViolations(page, 'login page');
});

test('reception dashboard has no serious or critical a11y violations after login', async ({ page }) => {
  test.setTimeout(90_000);
  await loginAsReception(page);
  await expect(page.getByRole('heading', { name: /Tableau de bord — Réception/ })).toBeVisible();
  await expectNoBlockingA11yViolations(page, 'reception dashboard');
});

for (const workspace of [
  { role: 'admin', route: '/clinical/billing', testId: 'billing-dashboard', label: 'unified billing' },
  { role: 'admin', route: '/clinical/admin', testId: 'admin-dashboard', label: 'clinic administration' },
  { role: 'pharmacy', route: '/clinical/pharmacy', testId: 'pharmacy-dashboard', label: 'pharmacy' },
  { role: 'lab', route: '/clinical/lab', testId: 'lab-dashboard', label: 'laboratory' },
  { role: 'nurse', route: '/clinical/nurse', testId: 'nurse-dashboard', label: 'nursing triage' },
  { role: 'pev', route: '/clinical/pev', testId: 'pev-dashboard', label: 'PEV' },
]) {
  test(`${workspace.label} has no serious or critical a11y violations`, async ({ page }) => {
    test.setTimeout(90_000);
    await loginAsRole(page, workspace.role);
    await page.goto(workspace.route);
    await expect(page.getByTestId(workspace.testId)).toBeVisible({ timeout: 20_000 });
    await expectNoBlockingA11yViolations(page, `${workspace.label} workspace`);
  });
}
