import { test, expect } from '@playwright/test';
import {
  fillRegistrationForm,
  loginAsReception,
  loginAsRole,
  logoutFromApp,
  countOutboxPending,
} from './helpers.js';

const PATIENTS_URL = '**/clinical/reception/his/patients';

async function queueOfflineRegistration(page, context, unique) {
  await loginAsReception(page);
  await fillRegistrationForm(page, {
    lastName: `OffNom${unique}`,
    firstName: `OffPrenom${unique}`,
    phone: `624${String(unique).slice(-6)}`,
  });
  await context.setOffline(true);
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-registration-queued')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('reception-patient-number')).toHaveCount(0);
}

test.describe('Offline failure / recovery matrix', () => {
  test('a) network loss before request queues durable outbox row', async ({ page, context }) => {
    test.setTimeout(120_000);
    await queueOfflineRegistration(page, context, Date.now());
    expect(await countOutboxPending(page)).toBeGreaterThanOrEqual(1);
  });

  test('b) network loss during in-flight request falls back to queue', async ({ page, context }) => {
    test.setTimeout(120_000);
    await loginAsReception(page);
    const unique = Date.now();
    await fillRegistrationForm(page, {
      lastName: `MidNom${unique}`,
      firstName: `MidPrenom${unique}`,
      phone: `625${String(unique).slice(-6)}`,
    });

    let intercepted = false;
    await page.route(PATIENTS_URL, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      intercepted = true;
      await context.setOffline(true);
      await route.abort('connectionfailed');
    });

    await page.getByTestId('reception-register-submit').click();
    await expect.poll(() => intercepted, { timeout: 15_000 }).toBe(true);
    await expect(page.getByTestId('reception-registration-queued')).toBeVisible({ timeout: 20_000 });
    await context.setOffline(false);
  });

  test('c) delayed server response while offline still reconciles dossier (best-effort)', async ({
    page,
    context,
  }) => {
    test.setTimeout(150_000);
    await loginAsReception(page);
    const unique = Date.now() + 1;
    await fillRegistrationForm(page, {
      lastName: `LateNom${unique}`,
      firstName: `LatePrenom${unique}`,
      phone: `626${String(unique).slice(-6)}`,
    });

    await page.route(PATIENTS_URL, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue();
        return;
      }
      await new Promise((r) => setTimeout(r, 2500));
      await route.continue();
    });

    await context.setOffline(true);
    await page.getByTestId('reception-register-submit').click();
    await expect(page.getByTestId('reception-registration-queued')).toBeVisible({ timeout: 20_000 });

    await context.setOffline(false);
    await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/, {
      timeout: 90_000,
    });
  });

  test('d) browser reload preserves pending outbox until sync', async ({ page, context }) => {
    test.setTimeout(150_000);
    await queueOfflineRegistration(page, context, Date.now() + 2);
    expect(await countOutboxPending(page)).toBeGreaterThanOrEqual(1);

    await page.reload();
    await expect(page.getByTestId('reception-dashboard')).toBeVisible({ timeout: 30_000 });
    expect(await countOutboxPending(page)).toBeGreaterThanOrEqual(1);

    await context.setOffline(false);
    await expect.poll(async () => countOutboxPending(page), { timeout: 90_000 }).toBe(0);
  });

  test('e) repeated reconnects eventually flush outbox', async ({ page, context }) => {
    test.setTimeout(180_000);
    await queueOfflineRegistration(page, context, Date.now() + 3);

    for (let i = 0; i < 3; i += 1) {
      await context.setOffline(false);
      await page.waitForTimeout(400);
      await context.setOffline(true);
      await page.waitForTimeout(400);
    }
    await context.setOffline(false);
    await expect.poll(async () => countOutboxPending(page), { timeout: 90_000 }).toBe(0);
  });

  test('f) duplicate offline submissions reuse single client request id', async ({ page, context }) => {
    test.setTimeout(120_000);
    await queueOfflineRegistration(page, context, Date.now() + 4);
    const afterFirst = await countOutboxPending(page);

    await page.getByTestId('reception-register-submit').click({ force: true }).catch(() => {});
    await page.waitForTimeout(500);
    expect(await countOutboxPending(page)).toBe(afterFirst);

    await context.setOffline(false);
    await expect.poll(async () => countOutboxPending(page), { timeout: 90_000 }).toBe(0);
  });

  test('g) logout/login as another user does not leak outbox', async ({ page, context }) => {
    test.setTimeout(150_000);
    await queueOfflineRegistration(page, context, Date.now() + 5);
    expect(await countOutboxPending(page)).toBeGreaterThanOrEqual(1);

    await logoutFromApp(page);
    await expect.poll(async () => countOutboxPending(page), { timeout: 15_000 }).toBe(0);

    await loginAsRole(page, 'doctor');
    await page.goto('/clinical/doctor');
    await expect(page.getByTestId('doctor-dashboard')).toBeVisible();
    expect(await countOutboxPending(page)).toBe(0);
    await expect(page.getByTestId('reception-registration-queued')).toHaveCount(0);
  });
});
