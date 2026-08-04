import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/** Fail only on serious/critical violations; minor/moderate are logged but tolerated. */
async function expectNoSeriousA11yViolations(page, contextLabel) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  const serious = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical'
  );

  if (serious.length > 0) {
    console.warn(`[a11y] ${contextLabel} — serious/critical violations:`, JSON.stringify(serious, null, 2));
  }

  expect(serious, `Serious/critical a11y violations on ${contextLabel}`).toEqual([]);
}

test('login page has no serious or critical a11y violations', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible();
  await expectNoSeriousA11yViolations(page, 'login page');
});

test('reception dashboard has no serious or critical a11y violations after login', async ({ page }) => {
  await page.goto('/login');
  await page.locator('#email').fill('reception@pilot.local');
  await page.locator('#password').fill('ReceptionPilot1!');
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await expect(page).toHaveURL(/\/clinical\/reception/);
  await expect(page.getByRole('heading', { name: /Tableau de bord — Réception/ })).toBeVisible();

  // Known minor noise: search results list may be empty; tab shortcuts use <kbd> without labels.
  await expectNoSeriousA11yViolations(page, 'reception dashboard');
});
