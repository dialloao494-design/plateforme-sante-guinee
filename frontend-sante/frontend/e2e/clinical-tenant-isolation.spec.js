import { test, expect } from '@playwright/test';

import { loginAsRole, loginWithCredentials, logoutFromApp, waitForLoginForm } from './helpers.js';

const OWNER = {
  email: 'owner@e2e.local',
  password: 'E2eOwnerPass12!',
  homePath: /\/platform/,
};

async function api(page, path, options = {}) {
  return page.evaluate(async ({ apiPath, init }) => {
    const token = sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
    const response = await fetch(`http://127.0.0.1:8000${apiPath}`, {
      credentials: 'include',
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers || {}),
      },
    });
    const text = await response.text();
    return { status: response.status, body: text ? JSON.parse(text) : null };
  }, { apiPath: path, init: options });
}

async function createPatient(page, suffix) {
  const result = await api(page, '/clinical/reception/patients', {
    method: 'POST',
    body: JSON.stringify({
      first_name: `Iso${suffix}`,
      last_name: `Tenant${suffix}`,
      age: 29,
      gender: 'F',
      phone: `61${String(suffix).slice(-7).padStart(7, '0')}`,
      mother_name: 'Test isolation',
      visit_destination: 'Consultation externe',
    }),
  });
  expect(result.status).toBe(201);
  return result.body;
}

async function activateProvisionedStaff(page, credentials, homePath) {
  await waitForLoginForm(page);
  await page.locator('#email').fill(credentials.email);
  await page.locator('#password').fill(credentials.password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL(/\/account\/password/, { timeout: 30_000 });
  const permanentPassword = 'TenantIsoReady2!';
  await page.getByLabel('Mot de passe actuel (temporaire)').fill(credentials.password);
  await page.getByLabel('Nouveau mot de passe', { exact: true }).fill(permanentPassword);
  await page.getByLabel('Confirmer le nouveau mot de passe').fill(permanentPassword);
  await page.getByRole('button', { name: 'Mettre à jour le mot de passe' }).click();
  await page.waitForURL(homePath, { timeout: 30_000 });
  credentials.password = permanentPassword;
}

test('foreign-clinic patient stays inaccessible through URL, search, cached session, and history', async ({ browser, page }) => {
  test.setTimeout(240_000);
  const suffix = Date.now();
  await loginWithCredentials(page, OWNER);

  const clinic = await api(page, '/clinical/clinics', {
    method: 'POST',
    body: JSON.stringify({ name: `Clinique Isolation ${suffix}`, city: 'Conakry' }),
  });
  expect(clinic.status).toBe(201);

  const betaCredentials = {};
  for (const [key, role] of Object.entries({
    reception: 'receptionist', lab: 'lab_technician', pharmacy: 'pharmacist', nurse: 'nurse', pev: 'pev_agent',
  })) {
    const credentials = {
      email: `${key}.isolation.${suffix}@e2e.local`,
      password: 'TenantIsoPass1!',
    };
    const staff = await api(page, '/clinical/staff', {
      method: 'POST',
      body: JSON.stringify({ ...credentials, role, clinic_id: clinic.body.id }),
    });
    expect(staff.status).toBe(201);
    betaCredentials[key] = credentials;
  }
  const betaReceptionContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const betaReceptionPage = await betaReceptionContext.newPage();
  await activateProvisionedStaff(betaReceptionPage, betaCredentials.reception, /\/clinical\/reception/);
  await betaReceptionContext.close();
  const betaReceptionReadyContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const betaReceptionReadyPage = await betaReceptionReadyContext.newPage();
  await loginWithCredentials(betaReceptionReadyPage, { ...betaCredentials.reception, homePath: /\/clinical\/reception/ });
  const foreignPatient = await createPatient(betaReceptionReadyPage, suffix);
  await betaReceptionReadyContext.close();

  const alphaReceptionContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const alphaReceptionPage = await alphaReceptionContext.newPage();
  await loginAsRole(alphaReceptionPage, 'reception');
  const ownPatient = await createPatient(alphaReceptionPage, suffix + 1);
  await alphaReceptionContext.close();

  const routes = [
    { key: 'lab', route: '/clinical/lab', label: 'Patient actif au laboratoire' },
    { key: 'pharmacy', route: '/clinical/pharmacy', label: 'Patient actif à la pharmacie' },
    { key: 'nurse', route: '/clinical/nurse', label: 'Patient actif en soins infirmiers' },
    { key: 'pev', route: '/clinical/pev', label: 'Patient actif au PEV' },
  ];

  for (const module of routes) {
    const context = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
    const rolePage = await context.newPage();
    await loginAsRole(rolePage, module.key);
    await rolePage.goto(`${module.route}?patient=${foreignPatient.id}`);
    await expect(rolePage.getByTestId('patient-safety-strip')).toHaveCount(0, { timeout: 20_000 });
    await expect(rolePage.getByText(foreignPatient.patient_number, { exact: true })).toHaveCount(0);
    await context.close();
  }

  const betaLabActivationContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const betaLabActivationPage = await betaLabActivationContext.newPage();
  await activateProvisionedStaff(betaLabActivationPage, betaCredentials.lab, /\/clinical\/lab/);
  await betaLabActivationContext.close();
  const labContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const labPage = await labContext.newPage();
  await loginWithCredentials(labPage, { ...betaCredentials.lab, homePath: /\/clinical\/lab/ });
  await labPage.goto(`/clinical/lab?patient=${foreignPatient.id}`);
  await expect(labPage.getByTestId('patient-safety-strip')).toContainText(foreignPatient.patient_number);
  await logoutFromApp(labPage);

  await loginAsRole(labPage, 'lab');
  await labPage.goto(`/clinical/lab?patient=${foreignPatient.id}`);
  await expect(labPage.getByTestId('patient-safety-strip')).toHaveCount(0, { timeout: 20_000 });

  const search = labPage.getByLabel('Recherche patient');
  await search.fill(`Tenant${suffix}`);
  await expect(labPage.getByText('Aucun patient trouvé.')).toBeVisible({ timeout: 10_000 });
  await expect(labPage.getByText(foreignPatient.patient_number, { exact: true })).toHaveCount(0);

  await labPage.goto(`/clinical/lab?patient=${ownPatient.id}`);
  await expect(labPage.getByTestId('patient-safety-strip')).toHaveAttribute('aria-label', routes[0].label);
  await expect(labPage.getByTestId('patient-safety-strip')).toContainText(ownPatient.patient_number);
  await labPage.goto(`/clinical/lab?patient=${foreignPatient.id}`);
  await expect(labPage.getByTestId('patient-safety-strip')).toHaveCount(0, { timeout: 20_000 });
  await labPage.goBack();
  await expect(labPage.getByTestId('patient-safety-strip')).toContainText(ownPatient.patient_number);
  await labPage.goForward();
  await expect(labPage.getByTestId('patient-safety-strip')).toHaveCount(0, { timeout: 20_000 });
  await expect(labPage.getByText(foreignPatient.patient_number, { exact: true })).toHaveCount(0);
  await labContext.close();
});
