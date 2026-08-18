import { test, expect } from '@playwright/test';

import { loginAsRole } from './helpers.js';

test.describe.configure({ mode: 'serial' });

test('patient context survives deep links and refresh across clinical roles', async ({ browser, page }) => {
  test.setTimeout(180_000);
  await loginAsRole(page, 'reception');

  const unique = Date.now();
  const patient = await page.evaluate(async ({ uniqueValue }) => {
    const token = sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
    const response = await fetch('http://127.0.0.1:8000/clinical/reception/patients', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        first_name: `Contexte${uniqueValue}`,
        last_name: 'Patient',
        age: 34,
        gender: 'F',
        phone: `62${String(uniqueValue).slice(-7)}`,
        mother_name: 'Contexte Mère',
        visit_destination: 'Consultation externe',
      }),
    });
    if (!response.ok) throw new Error(`Patient setup failed: ${response.status} ${await response.text()}`);
    return response.json();
  }, { uniqueValue: unique });

  await page.context().clearCookies();

  for (const role of [
    { key: 'lab', route: '/clinical/lab', label: 'Patient actif au laboratoire' },
    { key: 'pharmacy', route: '/clinical/pharmacy', label: 'Patient actif à la pharmacie' },
    { key: 'nurse', route: '/clinical/nurse', label: 'Patient actif en soins infirmiers' },
  ]) {
    const roleContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
    const rolePage = await roleContext.newPage();
    await loginAsRole(rolePage, role.key);
    await rolePage.goto(`${role.route}?patient=${patient.id}`);
    const strip = rolePage.getByTestId('patient-safety-strip');
    await expect(strip).toBeVisible({ timeout: 20_000 });
    await expect(strip).toContainText('Patient');
    await expect(strip).toContainText(patient.patient_number);
    await expect(strip).toHaveAttribute('aria-label', role.label);

    await rolePage.reload();
    await expect(rolePage.getByTestId('patient-safety-strip')).toContainText(patient.patient_number);

    await rolePage.getByRole('button', { name: 'Fermer le dossier' }).click();
    await expect(rolePage).not.toHaveURL(/patient=/);
    await expect(rolePage.getByTestId('patient-safety-strip')).toHaveCount(0);
    await roleContext.close();
  }
});
