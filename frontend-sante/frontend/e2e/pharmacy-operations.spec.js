import { expect, test } from '@playwright/test';
import { loginAsRole } from './helpers.js';

test('pharmacy exposes orders, dispensing history and management report on desktop and mobile', async ({ page }) => {
  await loginAsRole(page, 'pharmacy');
  await expect(page.getByRole('heading', { name: 'Tableau de bord Pharmacie' })).toBeVisible();

  await page.getByTestId('pharmacy-tab-orders').click();
  await expect(page.getByRole('heading', { name: 'Commandes de stock' })).toBeVisible();
  await expect(page.getByLabel('Fournisseur')).toBeVisible();

  await page.getByTestId('pharmacy-tab-stock').click();
  await expect(page.getByRole('heading', { name: 'Stock pharmacie' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Fournisseur' })).toHaveCount(0);

  await page.getByTestId('pharmacy-tab-history').click();
  await expect(page.getByRole('heading', { name: 'Historique des dispensations' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'N° demande' })).toBeVisible();

  await page.getByTestId('pharmacy-tab-report').click();
  await expect(page.getByRole('heading', { name: 'Rapport pharmacie' })).toBeVisible();
  await expect(page.getByText('Patients servis', { exact: true })).toBeVisible();
  await expect(page.getByText('Recettes encaissées', { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});
