import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

test('reception can register a new patient end to end', async ({ page }) => {
  test.setTimeout(90_000);
  await loginAsReception(page);

  await page.getByRole('button', { name: /Enregistrement/ }).click();

  const unique = Date.now();
  await page.getByLabel('Nom *', { exact: true }).fill(`TestNom${unique}`);
  await page.getByLabel('Prénom *', { exact: true }).fill(`TestPrenom${unique}`);
  await page.locator('.reception-his-birthdate-field input[type="date"]').fill('1990-05-15');
  await page.getByLabel('Adresse *', { exact: true }).fill('123 Rue de Kaloum, Conakry');
  await page.getByLabel('Tél. principal *', { exact: true }).fill(`622${String(unique).slice(-6)}`);
  await page.getByLabel('Nom du contact *', { exact: true }).fill('Contact Urgence');
  await page.getByRole('combobox', { name: 'Relation *' }).selectOption('Père');
  await page.getByLabel('Téléphone *', { exact: true }).fill('622000000');

  await page.getByRole('button', { name: 'Enregistrer le patient' }).click();

  await expect(page.getByText(/Patient enregistré · N° dossier patient/)).toBeVisible();
});
