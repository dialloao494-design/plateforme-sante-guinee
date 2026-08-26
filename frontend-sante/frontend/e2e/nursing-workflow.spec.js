import { expect, test } from '@playwright/test';

import { loginAsRole } from './helpers.js';

test('nurse completes an offline observation and keeps the patient context', async ({ page, context, request }) => {
  const login = await request.post('http://127.0.0.1:8000/auth/login-json', {
    data: { email: 'reception@pilot.local', password: 'ReceptionPilot1!' },
  });
  expect(login.ok()).toBe(true);
  const { csrf_token: csrfToken } = await login.json();
  expect(csrfToken).toBeTruthy();
  const suffix = String(Date.now()).slice(-7);
  const registration = await request.post('http://127.0.0.1:8000/clinical/reception/his/patients', {
    headers: { 'X-CSRF-Token': csrfToken },
    data: {
      first_name: 'Aminata', last_name: `Nurse${suffix}`, gender: 'F',
      date_of_birth: '1995-04-12', phone: `62${suffix}`, address: 'Conakry',
      emergency_contact: { full_name: 'Mamadou Diallo', relationship: 'parent', phone: `63${suffix}`, same_address_as_patient: true },
      payer: { payer_type: 'patient' }, confirm_duplicate: false,
      registration_date: new Date().toISOString().slice(0, 10),
    },
  });
  expect(registration.status()).toBe(201);

  await loginAsRole(page, 'nurse');
  await page.goto('/clinical/nurse');
  await page.getByLabel('Recherche patient').fill(`Nurse${suffix}`);
  await page.getByRole('button', { name: 'Rechercher' }).click();
  const firstPatient = page.locator('.reception-his-search-results button').first();
  await expect(firstPatient).toBeVisible();
  await firstPatient.click();
  await expect(page.getByTestId('nurse-vitals-first')).toBeVisible();

  const vitalTop = await page.getByTestId('nurse-vitals-first').evaluate((element) => element.getBoundingClientRect().top);
  const motiveTop = await page.getByRole('group', { name: /Motif de consultation/ }).evaluate((element) => element.getBoundingClientRect().top);
  expect(vitalTop).toBeLessThan(motiveTop);

  await page.getByLabel('Tension systolique').fill('120');
  await page.getByLabel('Tension diastolique').fill('80');
  await page.locator('input[name="temperature_c"]').fill('37.2');
  await page.locator('input[name="heart_rate"]').fill('76');
  await page.locator('input[name="oxygen_saturation"]').fill('98');
  await page.locator('input[name="respiratory_rate"]').fill('16');
  await page.getByRole('group', { name: /Motif de consultation/ }).locator('textarea').fill('Contrôle infirmier');
  await page.getByRole('group', { name: 'Notes infirmières' }).locator('textarea').fill('Patient stable');

  await context.setOffline(true);
  await page.getByRole('button', { name: /Enregistrer l’évaluation|Enregistrer l'évaluation/ }).click();
  await expect(page.getByText(/Observation enregistrée hors ligne/)).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText(/En attente de synchronisation/)).toBeVisible();
  await expect(page.getByText('Patient actif en soins infirmiers')).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});
