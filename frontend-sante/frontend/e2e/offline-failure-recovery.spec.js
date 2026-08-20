import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

test('network loss before request queues registration', async ({ page, context }) => {
  test.setTimeout(120_000);
  await loginAsReception(page);
  const unique = Date.now();
  await page.getByTestId('reception-tab-register').click();
  await page.getByLabel('Nom *', { exact: true }).fill(`FailNom${unique}`);
  await page.getByLabel('Prénom *', { exact: true }).fill(`FailPrenom${unique}`);
  await page.getByTestId('reception-date-of-birth').fill('1991-03-03');
  await page.getByLabel('Adresse *', { exact: true }).fill('Kaloum');
  await page.getByLabel('Tél. principal *', { exact: true }).fill(`625${String(unique).slice(-6)}`);
  await page.getByLabel('Nom du contact *', { exact: true }).fill('Contact');
  await page.getByRole('combobox', { name: 'Relation *' }).selectOption('Père');
  await page.getByLabel('Téléphone *', { exact: true }).fill('622000111');
  await context.setOffline(true);
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-registration-queued')).toBeVisible({ timeout: 15_000 });

  const patientCreatePattern = '**/clinical/reception/his/patients';
  await page.route(patientCreatePattern, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"temporary"}' });
      return;
    }
    await route.continue();
  });
  await context.setOffline(false);

  const syncNow = page.getByRole('button', { name: 'Synchroniser maintenant' }).first();
  await expect(syncNow).toBeVisible({ timeout: 30_000 });
  await page.unroute(patientCreatePattern);
  await syncNow.click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, { timeout: 60_000 });
});
