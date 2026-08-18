import { defineConfig, devices } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const REPO_ROOT = new URL('../../', import.meta.url).pathname;
const E2E_DB_DIR = mkdtempSync(join(tmpdir(), 'sg-e2e-'));
const E2E_DB_PATH = join(E2E_DB_DIR, 'e2e.db');
// actions/setup-python exposes `python3` without creating a repository .venv.
// Local development keeps using the project's isolated interpreter.
const E2E_PYTHON = process.env.E2E_PYTHON || (process.env.CI ? 'python3' : './.venv/bin/python');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  // Cap workers in CI: many parallel logins hammer the shared e2e API + SQLite.
  workers: process.env.CI ? 2 : undefined,
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
      // Fresh disposable SQLite DB per run avoids leftover locks / schema drift.
      // Longer timeout: cold Alembic + ensure_* on CI can exceed 60s.
      command: `${E2E_PYTHON} -m uvicorn main:app --host 127.0.0.1 --port 8000`,
      cwd: REPO_ROOT,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        DATABASE_URL: `sqlite:///${E2E_DB_PATH}`,
        SECRET_KEY: 'e2e-test-secret-key-32-characters-min',
        ENVIRONMENT: 'development',
        ENABLE_PILOT_SEED: 'true',
        ENABLE_STARTUP_TEST_USER: 'false',
        // Prevent Login → /platform/setup redirect from detaching the form mid-fill.
        ENABLE_PLATFORM_OWNER_BOOTSTRAP: 'true',
        PLATFORM_OWNER_EMAIL: 'owner@e2e.local',
        PLATFORM_OWNER_PASSWORD: 'E2eOwnerPass12!',
        AUTH_COOKIE_SAMESITE: 'lax',
        AUTH_COOKIE_SECURE: 'false',
        // Parallel Playwright logins share one IP — avoid false 429s in CI.
        RATE_LIMIT_LOGIN: '1000/minute',
        RATE_LIMIT_DEFAULT: '2000/minute',
      },
    },
    {
      command: 'npm run dev -- --port 5173',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_API_URL: 'http://127.0.0.1:8000',
      },
    },
  ],
});
