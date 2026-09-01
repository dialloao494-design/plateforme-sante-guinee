import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

test('server probe recovers when browser connectivity state remains stale', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      get: () => false,
    });
  });
  await loginAsReception(page);
  await expect.poll(
    () => page.evaluate(async () => {
      const { isBrowserOnline } = await import('/src/offline/register.js');
      return { browser: navigator.onLine, application: isBrowserOnline() };
    }),
    { timeout: 12_000 },
  ).toEqual({ browser: false, application: true });
});

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

  // Model an interrupted automatic replay that left a very recent row marked
  // in-flight. The explicit staff action must reclaim it immediately instead
  // of reporting "zero sent" until the one-minute crash timer expires.
  await page.evaluate(async () => {
    const { offlineDb } = await import('/src/offline/db.js');
    const row = await offlineDb.outbox.where('status').equals('pending').first();
    if (!row) throw new Error('Expected one queued offline registration');
    await offlineDb.outbox.update(row.id, { status: 'in_flight', updated_at: Date.now() });
  });

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
  await page.route(patientCreatePattern, async (route) => {
    if (route.request().method() === 'POST') {
      await new Promise((resolve) => setTimeout(resolve, 350));
    }
    await route.continue();
  });
  await syncNow.click();
  await expect(page.getByRole('button', { name: 'Synchronisation…', exact: true })).toBeVisible();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, { timeout: 60_000 });
  await expect(page.getByText('Synchronisation terminée', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Synchroniser maintenant' })).toHaveCount(0);
});
