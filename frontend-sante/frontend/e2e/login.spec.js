import { test, expect } from '@playwright/test';
import { loginAsReception, waitForLoginForm } from './helpers.js';

test('reception demo account logs in and lands on the reception dashboard', async ({ page }) => {
  test.setTimeout(60_000);
  await waitForLoginForm(page);
  await loginAsReception(page);
  await expect(page).toHaveURL(/\/clinical\/reception/);
});
