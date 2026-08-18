import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

async function fillRegistrationForm(page, { lastName, firstName, phone, dob = '1990-05-15' }) {
  await page.getByTestId('reception-tab-register').click();
  await page.getByLabel('Nom *', { exact: true }).fill(lastName);
  await page.getByLabel('Prénom *', { exact: true }).fill(firstName);
  await page.getByTestId('reception-date-of-birth').fill(dob);
  await page.getByLabel('Adresse *', { exact: true }).fill('123 Rue de Kaloum, Conakry');
  await page.getByLabel('Tél. principal *', { exact: true }).fill(phone);
  await page.getByLabel('Nom du contact *', { exact: true }).fill('Contact Urgence');
  await page.getByRole('combobox', { name: 'Relation *' }).selectOption('Père');
  await page.getByLabel('Téléphone *', { exact: true }).fill('622000000');
}

test('offline registration queues then reconciles dossier after reconnect', async ({ page, context }) => {
  test.setTimeout(120_000);
  await loginAsReception(page);

  const unique = Date.now();
  await fillRegistrationForm(page, {
    lastName: `OffNom${unique}`,
    firstName: `OffPrenom${unique}`,
    phone: `624${String(unique).slice(-6)}`,
  });

  // Lose network before submit — mutation must queue, not invent a PAT- number.
  await context.setOffline(true);
  await page.getByTestId('reception-register-submit').click();

  await expect(page.getByTestId('reception-registration-queued')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('reception-patient-sync-status')).toBeVisible();
  await expect(page.getByTestId('reception-register-submit')).toBeDisabled();
  await expect(page.getByTestId('reception-patient-number')).toHaveCount(0);

  // Reconnect and wait for outbox flush + reconciliation.
  await context.setOffline(false);
  // Trigger sync (auto-sync may take up to 15s; also rely on online event).
  await page.waitForTimeout(500);
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, {
    timeout: 60_000,
  });
  await expect(page.getByTestId('reception-registration-success')).toBeVisible();
});
