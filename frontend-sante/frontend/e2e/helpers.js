/** Shared Playwright helpers for stable login against cookie-auth SPA. */

export async function waitForLoginForm(page) {
  await page.goto('/login');
  // Wait until AuthProvider finishes bootstrap AND we remain on /login
  // (not redirected to /platform/setup when no owner exists).
  await page.waitForURL(/\/login\/?$/, { timeout: 30_000 });
  await page.getByRole('heading', { name: 'Connexion' }).waitFor({
    state: 'visible',
    timeout: 30_000,
  });
  await page.locator('#email').waitFor({ state: 'visible', timeout: 10_000 });
  await page.locator('#password').waitFor({ state: 'visible', timeout: 10_000 });
}

export async function loginAsReception(page) {
  await waitForLoginForm(page);
  await page.locator('#email').fill('reception@pilot.local');
  await page.locator('#password').fill('ReceptionPilot1!');
  await page.getByRole('button', { name: 'Se connecter' }).click();
  await page.waitForURL(/\/clinical\/reception/, { timeout: 45_000 });
}
