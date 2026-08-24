import { test, expect } from '@playwright/test';
import { loginAsRole } from './helpers.js';

async function expectNoPageOverflow(page) {
  await expect.poll(() => page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
}

test('shared hospital workflow navigation stays usable on a narrow pharmacy screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsRole(page, 'pharmacy');

  const workflow = page.getByTestId('pharmacy-tab-workflow');
  const stock = page.getByTestId('pharmacy-tab-stock');
  await expect(workflow).toHaveAttribute('aria-current', 'page');
  await stock.click();
  await expect(stock).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('heading', { name: /Stock pharmacie/i })).toBeVisible();
  await expectNoPageOverflow(page);
});

test('billing and administration forms reflow on a narrow clinic screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsRole(page, 'admin');

  await page.goto('/clinical/billing');
  await expect(page.getByTestId('billing-dashboard')).toBeVisible();
  await expect(page.getByLabel('Mode de paiement')).toBeVisible();
  await expectNoPageOverflow(page);

  await page.goto('/clinical/admin#create-user');
  await expect(page.getByTestId('admin-dashboard')).toBeVisible();
  await expect(page.getByLabel('Email professionnel')).toBeVisible();
  await expect(page.getByText('Aucun mot de passe à transmettre')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ouverture et relève du poste' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Ouvrir le poste|Clôturer et transmettre/ })).toBeVisible();
  await expectNoPageOverflow(page);
});
