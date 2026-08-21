import { test, expect } from '@playwright/test';
import { countOutboxPending, loginAsReception } from './helpers.js';

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
  await expect(page.getByTestId('reception-patient-local-id')).toContainText(/offline_/);
  await expect(page.getByTestId('reception-register-submit')).toBeDisabled();
  await expect(page.getByTestId('reception-patient-number')).toHaveCount(0);

  // The provisional patient must be usable for billing before a server dossier
  // exists. Both rows remain durable and patient registration replays first.
  await page.getByTestId('reception-tab-billing').click();
  await expect(page.getByText('ID local', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Consultation externe/ }).click();
  await page.getByRole('button', { name: 'Créer facture', exact: true }).click();
  await expect(page.getByRole('status')).toContainText(/Facture enregistrée hors ligne/i);
  const invoiceItems = page.locator('.reception-his-billing-lines').first();
  await expect(invoiceItems).toContainText(/100[\s\u202f]?000 GNF/);
  await expect(invoiceItems.getByText('0 GNF', { exact: true })).toHaveCount(0);
  await expect.poll(() => countOutboxPending(page)).toBe(2);

  // Payment is a local-first write too: acknowledgement and invoice totals
  // update immediately, while replay waits for the invoice ID reconciliation.
  const paymentStartedAt = Date.now();
  await page.getByRole('button', { name: 'Enregistrer les paiements' }).click();
  await expect(page.getByRole('status')).toContainText(/Paiement enregistré hors ligne/i);
  expect(Date.now() - paymentStartedAt).toBeLessThan(2_500);
  await expect(page.getByText('Historique des paiements')).toBeVisible();
  await expect(page.locator('.reception-his-payment-history')).toContainText(/100[\s\u202f]?000 GNF/);
  await expect.poll(() => countOutboxPending(page)).toBe(3);

  // Reconnect and wait for patient → invoice → payment replay in that order.
  await context.setOffline(false);
  // Trigger sync (auto-sync may take up to 15s; also rely on online event).
  await page.waitForTimeout(500);
  await expect.poll(() => countOutboxPending(page), { timeout: 60_000 }).toBe(0);
  await page.getByTestId('reception-tab-register').click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, {
    timeout: 60_000,
  });
  await expect(page.getByTestId('reception-registration-success')).toBeVisible();
});

test('an existing cached patient can be found, admitted, and invoiced offline', async ({ page, context }) => {
  test.setTimeout(150_000);
  await loginAsReception(page);

  const unique = Date.now();
  const phone = `627${String(unique).slice(-6)}`;
  await fillRegistrationForm(page, {
    lastName: `ExistantNom${unique}`,
    firstName: `ExistantPrenom${unique}`,
    phone,
  });
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, {
    timeout: 30_000,
  });

  // Registration opens and caches the canonical patient. Closing the dossier
  // proves the subsequent selection is served by the offline directory rather
  // than retained React state.
  await page.getByRole('button', { name: 'Fermer le dossier' }).click();
  await context.setOffline(true);
  await page.getByTestId('reception-tab-dashboard').click();
  await page.getByRole('button', { name: /Total patients/ }).click();
  await expect(page.locator('.reception-his-queue-panel')).toContainText(phone, { timeout: 5_000 });

  await page.getByLabel('Recherche patient').fill(phone);
  await page.getByRole('button', { name: 'Rechercher' }).click();
  const result = page.locator('.reception-his-search-results li').first();
  await expect(result).toContainText(phone, { timeout: 5_000 });
  await result.getByRole('button').click();
  await expect(page.getByRole('heading', { name: 'Nouvelle admission' })).toBeVisible();

  await page.getByRole('checkbox', { name: 'Consultation externe' }).check();
  const admissionStartedAt = Date.now();
  await page.getByRole('button', { name: 'Créer l’admission' }).click();
  await expect(page.getByRole('status')).toContainText(/Admission enregistrée hors ligne/i);
  expect(Date.now() - admissionStartedAt).toBeLessThan(2_500);
  await expect(page.getByRole('heading', { name: 'Facturation' })).toBeVisible();

  await page.getByRole('button', { name: /Consultation externe.*100/ }).click();
  const invoiceStartedAt = Date.now();
  await page.getByRole('button', { name: 'Créer facture', exact: true }).click();
  await expect(page.getByRole('status')).toContainText(/Facture enregistrée hors ligne/i);
  expect(Date.now() - invoiceStartedAt).toBeLessThan(2_500);
  const invoiceItems = page.locator('.reception-his-billing-lines').first();
  await expect(invoiceItems).toContainText(/100[\s\u202f]?000 GNF/);
  await expect(invoiceItems.getByText('0 GNF', { exact: true })).toHaveCount(0);
  await expect.poll(() => countOutboxPending(page)).toBe(2);

  await context.setOffline(false);
  await expect.poll(() => countOutboxPending(page), { timeout: 60_000 }).toBe(0);
});

test('a browser restart recovers an interrupted patient synchronization', async ({ page, context }) => {
  test.setTimeout(120_000);
  await loginAsReception(page);
  await expect(page.getByRole('heading', { name: 'Vue d’ensemble' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Actualiser les données' })).toBeVisible();
  await expect(page.getByText(/Mis à jour à|Mise à jour non disponible/)).toBeVisible();
  const unique = Date.now();
  const phone = `625${String(unique).slice(-6)}`;
  await fillRegistrationForm(page, {
    lastName: `RestartNom${unique}`,
    firstName: `RestartPrenom${unique}`,
    phone,
  });

  await context.setOffline(true);
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-registration-queued')).toBeVisible();

  // Model a crash after the row was claimed but before the HTTP response was
  // persisted. Closing the page prevents the old runtime from finishing it.
  await page.evaluate(async () => {
    const db = await new Promise((resolve, reject) => {
      const request = indexedDB.open('sante_offline_v2');
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    await new Promise((resolve, reject) => {
      const tx = db.transaction('outbox', 'readwrite');
      const store = tx.objectStore('outbox');
      const request = store.getAll();
      request.onsuccess = () => {
        const registration = request.result.find((row) => row.entity_type === 'patient');
        registration.status = 'in_flight';
        registration.updated_at = 1;
        store.put(registration);
      };
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  });
  await page.close();
  await context.setOffline(false);

  const restarted = await context.newPage();
  await restarted.goto('/clinical/reception');
  await expect(restarted.getByRole('heading', { name: 'Tableau de bord — Réception' })).toBeVisible();
  await expect.poll(() => countOutboxPending(restarted), { timeout: 60_000 }).toBe(0);
  await restarted.getByLabel('Recherche patient').fill(phone);
  await restarted.getByRole('button', { name: 'Rechercher' }).click();
  await expect(restarted.getByText(/N° dossier PAT-\d{3}-\d{6}/)).toBeVisible({ timeout: 30_000 });
});

test('concurrent offline registrations from two devices do not create duplicate patients', async ({ browser }) => {
  test.setTimeout(150_000);
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();
  try {
    await Promise.all([loginAsReception(pageA), loginAsReception(pageB)]);
    const unique = Date.now();
    const patient = {
      lastName: `ConcurrentNom${unique}`,
      firstName: `ConcurrentPrenom${unique}`,
      phone: `626${String(unique).slice(-6)}`,
    };
    await Promise.all([
      fillRegistrationForm(pageA, patient),
      fillRegistrationForm(pageB, patient),
    ]);
    await Promise.all([contextA.setOffline(true), contextB.setOffline(true)]);
    await Promise.all([
      pageA.getByTestId('reception-register-submit').click(),
      pageB.getByTestId('reception-register-submit').click(),
    ]);
    await Promise.all([
      expect(pageA.getByTestId('reception-registration-queued')).toBeVisible(),
      expect(pageB.getByTestId('reception-registration-queued')).toBeVisible(),
    ]);

    await Promise.all([contextA.setOffline(false), contextB.setOffline(false)]);
    await Promise.all([
      expect.poll(() => countOutboxPending(pageA), { timeout: 60_000 }).toBe(0),
      expect.poll(() => countOutboxPending(pageB), { timeout: 60_000 }).toBe(0),
    ]);

    // One request wins and the other device adopts that same canonical dossier.
    // The backend patient search must still contain one patient only.
    const conflictCount = await Promise.all([pageA, pageB].map((candidate) => candidate.evaluate(async () => {
      const db = await new Promise((resolve, reject) => {
        const request = indexedDB.open('sante_offline_v2');
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      const rows = await new Promise((resolve, reject) => {
        const tx = db.transaction('conflicts', 'readonly');
        const request = tx.objectStore('conflicts').getAll();
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });
      db.close();
      return rows.filter((row) => !row.resolved).length;
    })));
    expect(conflictCount[0] + conflictCount[1]).toBe(0);

    const dossierA = await pageA.getByTestId('reception-patient-number').textContent();
    const dossierB = await pageB.getByTestId('reception-patient-number').textContent();
    expect(dossierA).toMatch(/PAT-\d{3}-\d{6}/);
    expect(dossierB).toBe(dossierA);

    await pageA.getByLabel('Recherche patient').fill(patient.phone);
    await pageA.getByRole('button', { name: 'Rechercher' }).click();
    await expect(pageA.locator('.reception-his-search-results li')).toHaveCount(1);
    await expect(pageA.locator('.reception-his-search-results')).toContainText(/PAT-\d{3}-\d{6}/);
  } finally {
    await Promise.all([contextA.close(), contextB.close()]);
  }
});
