import { test, expect } from '@playwright/test';

test('production PWA reopens a protected clinical URL after complete network loss', async ({ page, context }) => {
  await page.goto('/login');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  // The first controlled navigation activates the production service worker.
  await page.reload();
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);

  // Model a workstation that authenticated and cached its identity while online.
  await page.evaluate(() => {
    const profile = {
      id: 9001,
      clinic_id: 17,
      clinic_name: 'Clinique hors ligne',
      email: 'reception.offline@test.local',
      full_name: 'Réception hors ligne',
      role: 'receptionist',
    };
    sessionStorage.setItem('user_id', String(profile.id));
    sessionStorage.setItem('user_role', profile.role);
    sessionStorage.setItem('sg_auth_profile', JSON.stringify(profile));
  });

  await context.setOffline(true);
  const response = await page.goto('/clinical/reception', { waitUntil: 'domcontentloaded' });
  expect(response).not.toBeNull();
  await expect(page.getByRole('heading', { name: 'Tableau de bord — Réception' })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/Hors ligne/).first()).toBeVisible();
  const cachedLogo = await page.evaluate(async () => {
    const response = await fetch('/branding/aasma-clinic-logo.png');
    return { ok: response.ok, size: (await response.blob()).size };
  });
  expect(cachedLogo.ok).toBe(true);
  expect(cachedLogo.size).toBeGreaterThan(1_000);
  expect(await page.title()).not.toContain('ERR_INTERNET_DISCONNECTED');
});
