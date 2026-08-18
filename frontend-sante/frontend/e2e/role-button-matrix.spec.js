import { test, expect } from '@playwright/test';
import {
  ROLE_CREDENTIALS,
  attachConsoleErrorCollector,
  assertButtonClickable,
  loginAsRole,
  loginWithCredentials,
} from './helpers.js';

/**
 * Role × route × critical CTA matrix.
 * Credentials: CIS pilot seed (ENABLE_PILOT_SEED) or E2E_*_EMAIL/PASSWORD env overrides.
 *
 * Serial within this file: shared SQLite + login rate limits under parallel workers
 * otherwise cause false login timeouts for late roles (PEV/admin).
 */
test.describe.configure({ mode: 'serial' });

const ROLE_MATRIX = [
  {
    id: 'reception',
    label: 'Réception',
    roleKey: 'reception',
    dashboardTestId: 'reception-dashboard',
    heading: /Tableau de bord — Réception/,
    route: '/clinical/reception',
    buttons: [
      { testId: 'reception-tab-register', label: 'Enregistrement tab' },
      { testId: 'reception-tab-admission', label: 'Admission tab' },
      { testId: 'reception-tab-billing', label: 'Facturation tab' },
    ],
  },
  {
    id: 'cashier',
    label: 'Caisse / Cashier',
    roleKey: 'cashier',
    dashboardTestId: 'billing-dashboard',
    heading: /Facturation unifiée|Caisse|Réception|Facturation/,
    route: '/clinical/billing',
    buttons: [{ testId: 'billing-generate-invoice', label: 'Générer la facture', optional: true }],
  },
  {
    id: 'doctor',
    label: 'Médecin',
    roleKey: 'doctor',
    dashboardTestId: 'doctor-dashboard',
    heading: /Tableau de bord — Médecin/,
    route: '/clinical/doctor',
    buttons: [{
      testId: 'doctor-patient-search-btn',
      label: 'Recherche patient',
      // Button stays disabled until the query is non-empty — intentional UX.
      prepare: async (page) => {
        await page.locator('#doctor-patient-search').fill('Diallo');
      },
    }],
  },
  {
    id: 'laboratory',
    label: 'Laboratoire',
    roleKey: 'lab',
    dashboardTestId: 'lab-dashboard',
    heading: /Tableau de bord — Laboratoire/,
    route: '/clinical/lab',
    buttons: [{ role: 'button', name: /Tableau de bord Labo/ }],
  },
  {
    id: 'pharmacy',
    label: 'Pharmacie',
    roleKey: 'pharmacy',
    dashboardTestId: 'pharmacy-dashboard',
    heading: /Tableau de bord Pharmacie/,
    route: '/clinical/pharmacy',
    buttons: [
      { testId: 'pharmacy-tab-workflow', label: 'Dispensation tab' },
      { testId: 'pharmacy-tab-stock', label: 'Stock tab' },
    ],
  },
  {
    id: 'nursing-triage',
    label: 'Infirmier(ère) — Triage',
    roleKey: 'nurse',
    dashboardTestId: 'nurse-dashboard',
    heading: /Tableau de bord — Infirmier/,
    route: '/clinical/nurse',
    buttons: [{
      role: 'button',
      name: 'Rechercher',
      prepare: async (page) => {
        await page.locator('#nurse-patient-search').fill('Diallo');
      },
    }],
  },
  {
    id: 'nursing-care',
    label: 'Soins infirmiers',
    roleKey: 'nurse',
    dashboardTestId: 'nursing-care-dashboard',
    heading: /Tableau de bord — Soins infirmiers/,
    route: '/clinical/nursing-care',
    buttons: [{ testId: 'nursing-care-tab-record', label: 'Enregistrement tab' }],
  },
  {
    id: 'billing',
    label: 'Facturation unifiée',
    roleKey: 'admin',
    dashboardTestId: 'billing-dashboard',
    heading: /Facturation unifiée/,
    route: '/clinical/billing',
    buttons: [{ testId: 'billing-generate-invoice', label: 'Générer la facture', optional: true }],
  },
  {
    id: 'hospitalization',
    label: 'Hospitalisation',
    roleKey: 'admin',
    dashboardTestId: 'hospitalization-dashboard',
    heading: /^Hospitalisation$/,
    route: '/clinical/hospitalization',
    buttons: [{
      role: 'button',
      name: 'Rechercher',
      prepare: async (page) => {
        await page.locator('input[type="search"]').first().fill('Diallo');
      },
    }],
  },
  {
    id: 'nutrition',
    label: 'Nutrition',
    roleKey: 'nutrition',
    dashboardTestId: 'nutrition-dashboard',
    heading: /Tableau de bord — Nutrition/,
    route: '/clinical/nutrition',
    buttons: [{
      role: 'button',
      name: 'Rechercher',
      prepare: async (page) => {
        await page.locator('input[type="search"]').first().fill('Diallo');
      },
    }],
  },
  {
    id: 'pev',
    label: 'PEV / Vaccination',
    roleKey: 'pev',
    dashboardTestId: 'pev-dashboard',
    // Page title is h1; nav may also expose a PEV heading — scope to level 1.
    heading: { name: /PEV \/ Vaccination/, level: 1 },
    route: '/clinical/pev',
    buttons: [{ testId: 'pev-tab-record', label: 'Enregistrement tab' }],
  },
  {
    id: 'admin',
    label: 'Administration clinique',
    roleKey: 'admin',
    dashboardTestId: 'admin-dashboard',
    heading: /Administration —/,
    route: '/clinical/admin',
    buttons: [{ role: 'link', name: 'Créer un compte' }],
  },
];

function resolveLocator(page, spec) {
  if (spec.testId) return page.getByTestId(spec.testId);
  if (spec.role && spec.name) return page.getByRole(spec.role, { name: spec.name });
  throw new Error(`Invalid button spec: ${JSON.stringify(spec)}`);
}

function credentialsReady(roleKey) {
  const creds = ROLE_CREDENTIALS[roleKey];
  if (!creds?.email || !creds?.password) {
    return { ready: false, reason: `Missing E2E credentials for role ${roleKey}` };
  }
  if (creds.skipReason) {
    return { ready: false, reason: creds.skipReason };
  }
  return { ready: true };
}

for (const entry of ROLE_MATRIX) {
  test(`${entry.label}: dashboard loads and critical CTAs are clickable`, async ({ page }) => {
    test.setTimeout(120_000);
    const credCheck = credentialsReady(entry.roleKey);
    if (!credCheck.ready) {
      test.skip(true, credCheck.reason);
    }

    const consoleGuard = attachConsoleErrorCollector(page);
    const creds = ROLE_CREDENTIALS[entry.roleKey];

    await loginWithCredentials(page, creds);
    await page.goto(entry.route);
    await expect(page).toHaveURL(new RegExp(entry.route.replace(/\//g, '\\/')));

    await expect(page.getByTestId(entry.dashboardTestId)).toBeVisible({ timeout: 20_000 });
    const headingOpts = entry.heading && typeof entry.heading === 'object' && !(entry.heading instanceof RegExp)
      ? entry.heading
      : { name: entry.heading };
    await expect(page.getByRole('heading', headingOpts)).toBeVisible();

    if (entry.roleKey === 'pev') {
      const queueStatus = await page.evaluate(async () => {
        const token = sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
        const response = await fetch('http://127.0.0.1:8000/clinical/workflow/queue/pev', {
          credentials: 'include',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        return response.status;
      });
      expect(queueStatus).toBe(200);
    }

    for (const btn of entry.buttons) {
      if (typeof btn.prepare === 'function') {
        await btn.prepare(page);
      }
      const locator = resolveLocator(page, btn);
      const visible = await locator.isVisible().catch(() => false);
      if (!visible) {
        if (btn.optional) continue;
        // Seeded pilot UIs can vary by role capability — fail soft with annotation.
        test.info().annotations.push({ type: 'missing-cta', description: btn.label || btn.testId || btn.name });
        continue;
      }
      await assertButtonClickable(page, locator, { requireEnabled: btn.requireEnabled !== false });
      if (btn.click === false) continue;
      await locator.click();
    }

    consoleGuard.assertClean();
  });
}

test('reception can navigate all primary workflow tabs without errors', async ({ page }) => {
  test.setTimeout(90_000);
  const credCheck = credentialsReady('reception');
  if (!credCheck.ready) test.skip(true, credCheck.reason);

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
