import { test, expect } from '@playwright/test';
import { loginAsReception } from './helpers.js';

test.describe.configure({ mode: 'serial' });

async function seedDeferredWork(page) {
  return page.evaluate(async () => {
    const { offlineDb } = await import('/src/offline/db.js');
    const profile = JSON.parse(sessionStorage.getItem('sg_auth_profile'));
    await offlineDb.outbox.add({
      client_request_id: 'policy-regression', owner_key: `${profile.id}:${profile.clinic_id}`,
      user_id: String(profile.id), clinic_id: String(profile.clinic_id),
      offline_data_epoch: profile.offline_data_epoch ?? 1,
      method: 'POST', url: '/clinical/consultations', entity_type: 'consultation',
      payload_json: '{"note":"must survive"}', status: 'pending',
      created_at: Date.now(), next_retry_at: Date.now() + 3600000,
    });
    return profile;
  });
}

async function pendingWork(page) {
  return page.evaluate(async () => {
    const { offlineDb } = await import('/src/offline/db.js');
    return offlineDb.outbox.where('client_request_id').equals('policy-regression').first();
  });
}

test('background authentication denial preserves unsent work and does not attempt token refresh', async ({ page }) => {
  await loginAsReception(page);
  const profile = await seedDeferredWork(page);
  let refreshes = 0;
  await page.route('**/auth/refresh', route => { refreshes += 1; return route.abort('internetdisconnected'); });
  await page.route('**/auth/me', route => route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"expired"}' }));
  const response = page.waitForResponse(r => r.url().endsWith('/auth/me') && r.status() === 401);
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await response;
  await expect.poll(async () => (await pendingWork(page))?.payload_json).toContain('must survive');
  expect(refreshes).toBe(0);
  expect(await page.evaluate(() => JSON.parse(sessionStorage.getItem('sg_auth_profile')).id)).toBe(profile.id);
  await expect(page.getByRole('heading', { name: 'Tableau de bord — Réception' })).toBeVisible();
});

test('logout discards an in-flight profile response', async ({ page }) => {
  await loginAsReception(page);
  const profile = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sg_auth_profile')));
  let captured;
  let announce;
  const requested = new Promise(resolve => { announce = resolve; });
  await page.route('**/auth/me', async route => { captured = route; announce(); });
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await requested;
  await page.getByRole('button', { name: 'Déconnexion', exact: true }).first().click();
  await expect(page).toHaveURL(/\/login/);
  await captured.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(profile) }).catch(() => {});
  expect(await page.evaluate(() => sessionStorage.getItem('sg_auth_profile'))).toBeNull();
  expect(await page.evaluate(() => sessionStorage.getItem('user_id'))).toBeNull();
  await expect(page.getByRole('heading', { name: 'Connexion', exact: true })).toBeVisible();
});

test('online-only policy reaches an open workstation and blocks offline writes and new patient cache warming', async ({ page, context }) => {
  await loginAsReception(page);
  const profile = await page.evaluate(() => JSON.parse(sessionStorage.getItem('sg_auth_profile')));
  await page.route('**/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...profile, offline_workstations_enabled: false }) }));
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect.poll(() => page.evaluate(() => JSON.parse(sessionStorage.getItem('sg_auth_profile')).offline_workstations_enabled)).toBe(false);
  const stored = await page.evaluate(async () => {
    const { cachePatientRecord } = await import('/src/offline/cache.js');
    const { offlineDb } = await import('/src/offline/db.js');
    await cachePatientRecord({ id: 'policy-test-no-cache', first_name: 'Do not persist' });
    return offlineDb.patients.where('patient_id').equals('policy-test-no-cache').count();
  });
  expect(stored).toBe(0);
  await context.setOffline(true);
  const result = await page.evaluate(async () => {
    const { default: http } = await import('/src/services/httpClient.js');
    try { const response = await http.post('/clinical/reception/his/patients', {}); return response.status; }
    catch { return 'failed'; }
  });
  expect(result).toBe('failed');
  await expect(page.getByText('Connexion requise · mode hors ligne désactivé', { exact: true })).toBeVisible();
  await test.info().attach('online-only-policy', { body: await page.screenshot(), contentType: 'image/png' });
});

test('reset policy quarantines pre-reset work in an open workstation', async ({ page }) => {
  await loginAsReception(page);
  const profile = await seedDeferredWork(page);
  await page.route('**/auth/me', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...profile, offline_data_epoch: (profile.offline_data_epoch ?? 1) + 1 }) }));
  await page.evaluate(() => window.dispatchEvent(new Event('focus')));
  await expect.poll(async () => (await pendingWork(page))?.status).toBe('dead');
  expect((await pendingWork(page)).payload_json).toContain('must survive');
});
