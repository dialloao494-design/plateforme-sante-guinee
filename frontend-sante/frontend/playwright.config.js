import { defineConfig, devices } from '@playwright/test';

const REPO_ROOT = new URL('../../', import.meta.url).pathname;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }]] : 'list',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    // Cookie-auth SPA: keep browser context cookies between navigations.
    ignoreHTTPSErrors: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: 'python3 -m uvicorn main:app --port 8000',
      cwd: REPO_ROOT,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        DATABASE_URL: 'sqlite:///./e2e.db',
        SECRET_KEY: 'e2e-test-secret-key-32-characters-min',
        ENVIRONMENT: 'development',
        ENABLE_PILOT_SEED: 'true',
        ENABLE_STARTUP_TEST_USER: 'false',
        // Prevent Login → /platform/setup redirect from detaching the form mid-fill.
        ENABLE_PLATFORM_OWNER_BOOTSTRAP: 'true',
        PLATFORM_OWNER_EMAIL: 'owner@e2e.local',
        PLATFORM_OWNER_PASSWORD: 'E2eOwnerPass12!',
      },
    },
    {
      command: 'npm run dev -- --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        VITE_API_URL: 'http://127.0.0.1:8000',
      },
    },
  ],
});
