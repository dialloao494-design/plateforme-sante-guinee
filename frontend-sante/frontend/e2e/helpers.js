/* eslint-env node */
/** Shared Playwright helpers for stable login against cookie-auth SPA. */

/** @typedef {{ email: string, password: string, homePath: RegExp, skipReason?: string }} RoleCredential */

export const ROLE_CREDENTIALS = {
  reception: {
    email: (globalThis.process?.env || {}).E2E_RECEPTION_EMAIL || 'reception@pilot.local',
    password: (globalThis.process?.env || {}).E2E_RECEPTION_PASSWORD || 'ReceptionPilot1!',
    homePath: /\/clinical\/reception/,
  },
  cashier: {
    email: (globalThis.process?.env || {}).E2E_CASHIER_EMAIL || 'cashier@pilot.local',
    password: (globalThis.process?.env || {}).E2E_CASHIER_PASSWORD || 'CashierPilot1!',
    homePath: /\/clinical\/reception/,
  },
  doctor: {
    email: (globalThis.process?.env || {}).E2E_DOCTOR_EMAIL || 'dr.pilot@pilot.local',
    password: (globalThis.process?.env || {}).E2E_DOCTOR_PASSWORD || 'DoctorPilot1!',
    homePath: /\/clinical\/doctor/,
  },
  lab: {
    email: (globalThis.process?.env || {}).E2E_LAB_EMAIL || 'lab@pilot.local',
    password: (globalThis.process?.env || {}).E2E_LAB_PASSWORD || 'LabPilot123!',
    homePath: /\/clinical\/lab/,
  },
  pharmacy: {
    email: (globalThis.process?.env || {}).E2E_PHARMACY_EMAIL || 'pharmacy@pilot.local',
    password: (globalThis.process?.env || {}).E2E_PHARMACY_PASSWORD || 'PharmacyPilot1!',
    homePath: /\/clinical\/pharmacy/,
  },
  nurse: {
    email: (globalThis.process?.env || {}).E2E_NURSE_EMAIL || 'nurse@pilot.local',
    password: (globalThis.process?.env || {}).E2E_NURSE_PASSWORD || 'NursePilot1!',
    homePath: /\/clinical\/nurse/,
  },
  nutrition: {
    email: (globalThis.process?.env || {}).E2E_NUTRITION_EMAIL || 'nutrition@pilot.local',
    password: (globalThis.process?.env || {}).E2E_NUTRITION_PASSWORD || 'NutritionPilot1!',
    homePath: /\/clinical\/nutrition/,
  },
  pev: {
    email: (globalThis.process?.env || {}).E2E_PEV_EMAIL || 'pev@pilot.local',
    password: (globalThis.process?.env || {}).E2E_PEV_PASSWORD || 'PevPilot1!',
    homePath: /\/clinical\/pev/,
  },
  admin: {
    email: (globalThis.process?.env || {}).E2E_ADMIN_EMAIL || 'admin@pilot.local',
    password: (globalThis.process?.env || {}).E2E_ADMIN_PASSWORD || 'AdminPilot1!',
    homePath: /\/clinical\/admin/,
  },
};

export async function waitForLoginForm(page) {
  await page.goto('/login');
  await page.waitForURL(/\/login\/?$/, { timeout: 30_000 });
  await page.getByRole('heading', { name: 'Connexion' }).waitFor({
    state: 'visible',
    timeout: 30_000,
  });
  await page.locator('#email').waitFor({ state: 'visible', timeout: 10_000 });
  await page.locator('#password').waitFor({ state: 'visible', timeout: 10_000 });
}

/**
 * @param {import('@playwright/test').Page} page
 * @param {{ email: string, password: string, homePath?: RegExp }} creds
 */
export async function loginWithCredentials(page, { email, password, homePath }) {
  await waitForLoginForm(page);
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: 'Se connecter' }).click();
  if (homePath) {
    await page.waitForURL(homePath, { timeout: 45_000 });
  }
}

export async function loginAsReception(page) {
  await loginWithCredentials(page, ROLE_CREDENTIALS.reception);
}

/** @param {import('@playwright/test').Page} page */
export async function loginAsRole(page, roleKey) {
  const creds = ROLE_CREDENTIALS[roleKey];
  if (!creds?.email || !creds?.password) {
    throw new Error(`Missing credentials for role: ${roleKey}`);
  }
  await loginWithCredentials(page, creds);
}

/** @param {import('@playwright/test').Page} page */
export async function logoutFromApp(page) {
  const logoutBtn = page.getByRole('button', { name: 'Déconnexion' });
  if (await logoutBtn.isVisible().catch(() => false)) {
    await logoutBtn.click();
  } else {
    await page.goto('/login');
    await page.evaluate(() => {
      sessionStorage.clear();
    });
  }
  await page.waitForURL(/\/login\/?$/, { timeout: 30_000 });
}

/** Collect console page errors (excludes benign favicon/network noise). */
export function attachConsoleErrorCollector(page) {
  const errors = [];
  page.on('pageerror', (err) => errors.push(String(err)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (/favicon|404.*\.(png|ico)|ResizeObserver/i.test(text)) return;
      errors.push(text);
    }
  });
  return {
    assertClean() {
      if (errors.length) {
        throw new Error(`Unexpected console/page errors:\n${errors.join('\n')}`);
      }
    },
    get errors() {
      return errors;
    },
  };
}

/** @param {import('@playwright/test').Page} page */
export async function assertButtonClickable(page, locator) {
  await locator.waitFor({ state: 'visible', timeout: 15_000 });
  await locator.scrollIntoViewIfNeeded();
  if (await locator.isDisabled()) {
    throw new Error(`Expected enabled button: ${await locator.innerText().catch(() => 'button')}`);
  }
}

export async function fillRegistrationForm(page, { lastName, firstName, phone, dob = '1990-05-15' }) {
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

/** Count durable outbox rows still pending/in-flight for the active browser session. */
export async function countOutboxPending(page) {
  return page.evaluate(async () => {
    const DB_NAME = 'sante_offline_v2';
    const open = () =>
      new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME);
        req.onerror = () => reject(req.error);
        req.onsuccess = () => resolve(req.result);
      });
    try {
      const db = await open();
      if (!db.objectStoreNames.contains('outbox')) return 0;
      const rows = await new Promise((resolve, reject) => {
        const tx = db.transaction('outbox', 'readonly');
        const req = tx.objectStore('outbox').getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });
      db.close();
      return rows.filter((r) => ['pending', 'failed', 'in_flight'].includes(r.status)).length;
    } catch {
      return 0;
    }
  });
}
