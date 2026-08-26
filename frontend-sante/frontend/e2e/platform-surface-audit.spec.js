import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

import { attachConsoleErrorCollector, loginAsRole } from './helpers.js';

const SURFACES = [
  {
    role: 'patient',
    routes: ['/dashboard', '/my-records', '/appointments', '/doctors', '/teleconsultation', '/notifications', '/account/profile', '/account/password'],
  },
  {
    role: 'platformOwner',
    routes: ['/platform/clinics', '/platform/settings', '/platform/system', '/platform/accounts', '/account/profile', '/account/password'],
  },
  {
    role: 'admin',
    routes: ['/clinical', '/clinical/admin', '/clinical/pev', '/clinical/nursing-care', '/clinical/patient-history', '/clinical/hospitalization', '/clinical/billing', '/clinical/discharge', '/clinical/radiology', '/clinical/nutrition', '/clinical/notifications', '/clinical/reports', '/account/profile', '/account/password'],
  },
  {
    role: 'doctor',
    routes: ['/clinical/doctor', '/clinical/prescriptions', '/clinical/patient-history', '/clinical/hospitalization', '/clinical/discharge', '/clinical/radiology', '/clinical/nutrition', '/clinical/pev', '/clinical/notifications', '/doctor/dashboard', '/doctor/appointments', '/doctor/messages', '/teleconsultation', '/notifications', '/patients', '/account/profile', '/account/password'],
  },
  { role: 'reception', routes: ['/clinical/reception', '/clinical/patient-history', '/clinical/pev', '/clinical/hospitalization', '/clinical/billing', '/clinical/discharge', '/clinical/notifications', '/clinical/reports', '/account/profile', '/account/password'] },
  { role: 'nurse', routes: ['/clinical/nurse', '/clinical/nursing-care', '/clinical/patient-history', '/clinical/hospitalization', '/account/profile', '/account/password'] },
  { role: 'lab', routes: ['/clinical/lab', '/clinical/radiology', '/account/profile', '/account/password'] },
  { role: 'pharmacy', routes: ['/clinical/pharmacy', '/account/profile', '/account/password'] },
  { role: 'nutrition', routes: ['/clinical/nutrition', '/account/profile', '/account/password'] },
  { role: 'pev', routes: ['/clinical/pev', '/account/profile', '/account/password'] },
  { role: 'cashier', routes: ['/clinical/reception', '/clinical/billing', '/clinical/reports', '/account/profile', '/account/password'] },
];

async function visibleControlDefects(page) {
  return page.locator('input, select, textarea').evaluateAll((controls) => controls
    .filter((control) => {
      if (control.type === 'hidden' || control.disabled) return false;
      const style = window.getComputedStyle(control);
      return style.display !== 'none' && style.visibility !== 'hidden' && control.getClientRects().length > 0;
    })
    .filter((control) => {
      if (control.labels?.length) return false;
      if (control.getAttribute('aria-label')?.trim()) return false;
      if (control.getAttribute('aria-labelledby')?.trim()) return false;
      return true;
    })
    .map((control) => ({
      tag: control.tagName.toLowerCase(),
      type: control.getAttribute('type') || '',
      id: control.id || '',
      name: control.getAttribute('name') || '',
      placeholder: control.getAttribute('placeholder') || '',
    })));
}

async function auditCurrentSurface(page, route, width) {
  await expect(page).toHaveURL(new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  await expect(page.locator('#main-content')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('#main-content h1').first(), `${route} needs one visible page title`).toBeVisible();

  const overflow = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    page: document.documentElement.scrollWidth,
  }));
  expect(overflow.page, `${route} overflows horizontally at ${width}px`).toBeLessThanOrEqual(overflow.viewport + 1);

  const unnamedButtons = await page.locator('button').evaluateAll((buttons) => buttons
    .filter((button) => button.getClientRects().length > 0)
    .filter((button) => !(button.getAttribute('aria-label') || button.textContent || '').trim())
    .length);
  expect(unnamedButtons, `${route} contains visible buttons without accessible names`).toBe(0);

  expect(await visibleControlDefects(page), `${route} contains visible unlabeled form controls`).toEqual([]);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const blocking = results.violations.filter((violation) => violation.id !== 'color-contrast'
    && ['serious', 'critical'].includes(violation.impact));
  expect(blocking, `${route} contains blocking accessibility violations`).toEqual([]);
}

for (const surface of SURFACES) {
  test(`${surface.role} surfaces pass full desktop and mobile UI acceptance`, async ({ page }) => {
    test.setTimeout(240_000);
    const consoleGuard = attachConsoleErrorCollector(page);
    await loginAsRole(page, surface.role);

    for (const route of surface.routes) {
      await test.step(`${route} — desktop`, async () => {
        await page.setViewportSize({ width: 1440, height: 1000 });
        await page.goto(route);
        await page.waitForLoadState('networkidle').catch(() => {});
        await auditCurrentSurface(page, route, 1440);
      });
      await test.step(`${route} — mobile`, async () => {
        await page.setViewportSize({ width: 390, height: 844 });
        await auditCurrentSurface(page, route, 390);
      });
    }

    consoleGuard.assertClean();
  });
}
