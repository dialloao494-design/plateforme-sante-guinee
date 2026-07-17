import { test, expect } from '@playwright/test';

test('reception demo account logs in and lands on the reception dashboard', async ({ page }) => {
  await page.goto('/login');

  await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible();

  await page.locator('#email').fill('reception@pilot.local');
  await page.locator('#password').fill('ReceptionPilot1!');
  await page.getByRole('button', { name: 'Se connecter' }).click();

  await expect(page).toHaveURL(/\/clinical\/reception/);
});
