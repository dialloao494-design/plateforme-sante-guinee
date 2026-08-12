import { test, expect } from '@playwright/test';
import {
  ROLE_CREDENTIALS,
  attachConsoleErrorCollector,
  assertButtonClickable,
  assertButtonPresent,
  loginAsRole,
  loginWithCredentials,
} from './helpers.js';

const ROLE_MATRIX = [
  {
    label: 'Réception',
    roleKey: 'reception',
    dashboardTestId: 'reception-dashboard',
    heading: /Tableau de bord — Réception/,
    route: '/clinical/reception',
    buttons: [
      { testId: 'reception-tab-register', click: true },
      { testId: 'reception-tab-admission', click: true },
      { testId: 'reception-tab-billing', click: true },
    ],
  },
  {
    label: 'Caisse / Cashier',
    roleKey: 'cashier',
    dashboardTestId: 'reception-dashboard',
    heading: /Tableau de bord — Réception/,
    route: '/clinical/reception',
    buttons: [
      { testId: 'reception-tab-billing', click: true },
      { testId: 'reception-tab-refund', click: true },
    ],
  },
  {
    label: 'Médecin',
    roleKey: 'doctor',
    dashboardTestId: 'doctor-dashboard',
    heading: /Tableau de bord — Médecin/,
    route: '/clinical/doctor',
    prepare: async (page) => {
      await page.locator('#doctor-patient-search').fill('Diallo');
    },
    buttons: [{ testId: 'doctor-patient-search-btn', click: true }],
  },
  {
    label: 'Laboratoire',
    roleKey: 'lab',
    dashboardTestId: 'lab-dashboard',
    heading: /Tableau de bord — Laboratoire/,
    route: '/clinical/lab',
    buttons: [{ role: 'button', name: /Tableau de bord Labo/, click: true }],
  },
  {
    label: 'Pharmacie',
    roleKey: 'pharmacy',
    dashboardTestId: 'pharmacy-dashboard',
    heading: /Tableau de bord Pharmacie/,
    route: '/clinical/pharmacy',
    buttons: [
      { testId: 'pharmacy-tab-workflow', click: true },
      { testId: 'pharmacy-tab-stock', click: true },
    ],
  },
  {
    label: 'Infirmier(ère) — Triage',
    roleKey: 'nurse',
    dashboardTestId: 'nurse-dashboard',
    heading: /Tableau de bord — Infirmier/,
    route: '/clinical/nurse',
    prepare: async (page) => {
      await page.getByPlaceholder(/N° dossier, nom, téléphone/i).fill('Diallo');
    },
    buttons: [{ role: 'button', name: 'Rechercher', click: true }],
  },
  {
    label: 'Soins infirmiers',
    roleKey: 'nurse',
    dashboardTestId: 'nursing-care-dashboard',
    heading: /Tableau de bord — Soins infirmiers/,
    route: '/clinical/nursing-care',
    buttons: [{ testId: 'nursing-care-tab-record', click: true }],
  },
  {
    label: 'Facturation unifiée',
    roleKey: 'admin',
    dashboardTestId: 'billing-dashboard',
    heading: /Facturation unifiée/,
    route: '/clinical/billing',
    buttons: [{ role: 'heading', name: 'Générer une facture', click: false }],
  },
  {
    label: 'Hospitalisation',
    roleKey: 'admin',
    dashboardTestId: 'hospitalization-dashboard',
    heading: /^Hospitalisation$/,
    route: '/clinical/hospitalization',
    prepare: async (page) => {
      await page.getByPlaceholder('Nom ou téléphone').fill('Diallo');
    },
    buttons: [{ role: 'button', name: 'Rechercher', click: true }],
  },
  {
    label: 'Nutrition',
    roleKey: 'nutrition',
    dashboardTestId: 'nutrition-dashboard',
    heading: /Tableau de bord — Nutrition/,
    route: '/clinical/nutrition',
    prepare: async (page) => {
      await page.getByPlaceholder(/Nom ou téléphone/i).fill('Diallo');
    },
    buttons: [{ role: 'button', name: 'Rechercher', click: true }],
  },
  {
    label: 'PEV / Vaccination',
    roleKey: 'pev',
    dashboardTestId: 'pev-dashboard',
    heading: /PEV \/ Vaccination/,
    route: '/clinical/pev',
    buttons: [{ testId: 'pev-tab-record', click: true }],
  },
  {
    label: 'Administration clinique',
    roleKey: 'admin',
    dashboardTestId: 'admin-dashboard',
    heading: /Administration —/,
    route: '/clinical/admin',
    buttons: [{ role: 'link', name: 'Créer un compte', click: true }],
  },
];

function resolveLocator(page, spec) {
  if (spec.testId) return page.getByTestId(spec.testId);
  if (spec.role && spec.name) return page.getByRole(spec.role, { name: spec.name });
  throw new Error(`Invalid button spec: ${JSON.stringify(spec)}`);
}

for (const entry of ROLE_MATRIX) {
  test(`${entry.label}: dashboard loads and critical CTAs are clickable`, async ({ page }) => {
    test.setTimeout(90_000);
    const creds = ROLE_CREDENTIALS[entry.roleKey];
    if (!creds?.email || !creds?.password) {
      test.skip(true, `Missing E2E credentials for role ${entry.roleKey}`);
    }

    const consoleGuard = attachConsoleErrorCollector(page);
    await loginWithCredentials(page, creds);
    await page.goto(entry.route);
    await expect(page.getByTestId(entry.dashboardTestId)).toBeVisible({ timeout: 20_000 });
    await expect(page.getByRole('heading', { name: entry.heading })).toBeVisible();

    if (entry.prepare) await entry.prepare(page);

    for (const btn of entry.buttons) {
      const locator = resolveLocator(page, btn);
      if (btn.click) {
        await assertButtonClickable(page, locator);
        await locator.click();
      } else {
        await assertButtonPresent(page, locator, { allowDisabled: true });
      }
    }

    consoleGuard.assertClean();
  });
}

test('reception can navigate all primary workflow tabs without errors', async ({ page }) => {
  test.setTimeout(90_000);
  const consoleGuard = attachConsoleErrorCollector(page);
  await loginAsRole(page, 'reception');

  for (const tabId of ['dashboard', 'register', 'admission', 'billing', 'refund', 'service_requests']) {
    const tab = page.getByTestId(`reception-tab-${tabId}`);
    await assertButtonClickable(page, tab);
    await tab.click();
    await expect(page.getByTestId('reception-dashboard')).toBeVisible();
  }

  consoleGuard.assertClean();
});
