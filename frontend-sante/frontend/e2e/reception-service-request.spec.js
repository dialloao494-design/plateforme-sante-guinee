import { test, expect } from '@playwright/test';
import {
  attachConsoleErrorCollector,
  fillRegistrationForm,
  loginAsReception,
} from './helpers.js';

test.describe.configure({ mode: 'serial' });

test('service-request workspace stays coherent and creates a catalogue-backed request', async ({ page }) => {
  test.setTimeout(120_000);
  const consoleGuard = attachConsoleErrorCollector(page);
  await loginAsReception(page);

  const unique = Date.now();
  await fillRegistrationForm(page, {
    lastName: `Service${unique}`,
    firstName: 'Parcours',
    phone: `624${String(unique).slice(-6)}`,
  });
  await page.getByTestId('reception-register-submit').click();
  await expect(page.getByTestId('reception-patient-number')).toContainText(/PAT-\d{3}-\d{6}/);

  await page.getByTestId('reception-tab-service_requests').click();
  await expect(page.getByTestId('service-request-workspace')).toBeVisible();
  await expect(page.getByLabel('Rechercher une demande')).toBeVisible();
  await expect(page.getByLabel('Statut du registre')).toBeVisible();
  await expect(page.getByTestId('service-request-catalog')).toBeVisible();

  const activeTabStyle = await page.getByTestId('reception-tab-service_requests').evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      background: style.backgroundColor,
      radius: style.borderRadius,
      bottomWidth: style.borderBottomWidth,
      bottomStyle: style.borderBottomStyle,
    };
  });
  expect(activeTabStyle.radius).toBe('0px');
  expect(activeTabStyle.bottomWidth).toBe('3px');
  expect(activeTabStyle.bottomStyle).toBe('solid');
  expect(activeTabStyle.background).toBe('rgba(0, 0, 0, 0)');

  // The disposable clinic has no lab catalogue; the built-in clinical service
  // catalogue still exercises the authorized, price-controlled request path.
  await page.getByLabel('Catégorie').selectOption('service');
  await page.getByRole('button', { name: /Injection ·/ }).click();
  await expect(page.getByText(/Sélection enregistrée/)).toBeVisible();
  await page.getByRole('button', { name: 'Créer la demande' }).click();
  await expect(page.getByText(/Demande enregistrée \(DSR-/)).toBeVisible();
  await expect(page.locator('.service-request-item')).toHaveCount(1);

  consoleGuard.assertClean();
});

test('service-request controls reflow without horizontal page overflow', async ({ page }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsReception(page);
  await page.getByTestId('reception-tab-service_requests').click();

  await expect(page.getByTestId('service-request-workspace')).toBeVisible();
  const layout = await page.evaluate(() => {
    const filters = getComputedStyle(document.querySelector('[data-testid="service-request-filters"]'));
    const setup = getComputedStyle(document.querySelector('[data-testid="service-request-setup"]'));
    return {
      pageOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      filterColumns: filters.gridTemplateColumns.split(' ').length,
      setupColumns: setup.gridTemplateColumns.split(' ').length,
    };
  });

  expect(layout.pageOverflow).toBe(false);
  expect(layout.filterColumns).toBe(1);
  expect(layout.setupColumns).toBe(1);
});
