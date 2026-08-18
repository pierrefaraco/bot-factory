import { defineConfig } from '@playwright/test';
import * as path from 'path';

// The Angular dev server (ng serve --port 443, see package.json) proxies
// /api/* to the Flask backend (proxy.conf.json -> 127.0.0.1:444), so hitting
// this single baseURL exercises the exact same request path a real browser
// session uses -- no separate API base URL needed.
const BASE_URL = process.env['E2E_BASE_URL'] || 'http://localhost:443';
const AUTH_DIR = path.join(__dirname, 'e2e', '.auth');

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  // The 3 dedicated accounts (User/Admin/Guest) and the bots/guest they
  // share are mutated in place by admin.spec.ts (activate/deactivate) and
  // read by guest-access.spec.ts (assigned bots) -- running everything
  // serially keeps those specs from racing each other.
  fullyParallel: false,
  workers: 1,
  retries: process.env['CI'] ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  globalSetup: require.resolve('./e2e/global-setup.ts'),
  globalTeardown: require.resolve('./e2e/global-teardown.ts'),
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'unauthenticated',
      testMatch: /auth\.spec\.ts/,
    },
    {
      name: 'user',
      testMatch: /(bot-workspace|user-admin-access)\.spec\.ts/,
      use: { storageState: path.join(AUTH_DIR, 'user.json') },
    },
    {
      name: 'admin',
      testMatch: /admin\.spec\.ts/,
      use: { storageState: path.join(AUTH_DIR, 'admin.json') },
    },
    {
      name: 'guest',
      testMatch: /guest-access\.spec\.ts/,
      use: { storageState: path.join(AUTH_DIR, 'guest.json') },
    },
  ],
});
