import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

async function fillRegistrationForm(page, { lastName, firstName, phone, dob = '1990-05-15' }) {
  await page.getByRole('button', { name: /Enregistrement/ }).click();
  await page.getByLabel('Nom *', { exact: true }).fill(lastName);
  await page.getByLabel('Prénom *', { exact: true }).fill(firstName);
  await page.locator('.reception-his-birthdate-field input[type="date"]').fill(dob);
  await page.getByLabel('Adresse *', { exact: true }).fill('123 Rue de Kaloum, Conakry');
  await page.getByLabel('Tél. principal *', { exact: true }).fill(phone);
  await page.getByLabel('Nom du contact *', { exact: true }).fill('Contact Urgence');
  await page.getByRole('combobox', { name: 'Relation *' }).selectOption('Père');
  await page.getByLabel('Téléphone *', { exact: true }).fill('622000000');
}

test('reception can register a new patient end to end', async ({ page }) => {
  test.setTimeout(90_000);
  await loginAsReception(page);

  const unique = Date.now();
  await fillRegistrationForm(page, {
    lastName: `TestNom${unique}`,
    firstName: `TestPrenom${unique}`,
    phone: `622${String(unique).slice(-6)}`,
  });

  await page.getByTestId('reception-register-submit').click();

  await expect(page.getByText(/Patient enregistré · N° dossier patient PAT-/i)).toBeVisible();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/);
  await expect(page.getByTestId('reception-registration-success')).toBeVisible();
});

test('reception duplicate patient shows matches and allow confirm', async ({ page }) => {
  test.setTimeout(90_000);
  await loginAsReception(page);

  const unique = Date.now();
  const shared = {
    lastName: `DupNom${unique}`,
    firstName: `DupPrenom${unique}`,
    phone: `623${String(unique).slice(-6)}`,
    dob: '1991-06-20',
  };

  await fillRegistrationForm(page, shared);
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/);

  await page.getByRole('button', { name: 'Nouvel enregistrement' }).click();
  await fillRegistrationForm(page, shared);
  await page.getByTestId('reception-register-submit').click();

  await expect(page.getByTestId('duplicate-patient-panel')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Patients similaires détectés/i })).toBeVisible();
  await expect(page.getByText(/Request failed with status code 409/i)).toHaveCount(0);

  await page.getByTestId('confirm-duplicate-register').click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/);
});
