import { APIRequestContext, request as playwrightRequest } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { login, authHeaders } from './support/api-client';

const BASE_URL = process.env['E2E_BASE_URL'] || 'http://localhost:443';
const AUTH_DIR = path.join(__dirname, '.auth');

/** Deletes are otherwise fire-and-forget, so a transient failure (a dropped
 * connection, a slow-to-settle prior request) leaves a dedicated test
 * account/bot behind with nothing in the run's output pointing at why. One
 * retry after a short pause, then a loud warning (not a thrown error --
 * teardown failing shouldn't mask whether the actual tests passed). A 404
 * means it's already gone, which counts as success for cleanup purposes. */
async function deleteWithRetry(
  api: APIRequestContext,
  url: string,
  headers: Record<string, string>
): Promise<void> {
  for (let attempt = 1; attempt <= 2; attempt++) {
    const res = await api.delete(url, { headers });
    if (res.ok() || res.status() === 404) return;
    if (attempt === 2) {
      console.warn(`[e2e teardown] Failed to delete ${url}: ${res.status()} ${await res.text()}`);
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

export default async function globalTeardown(): Promise<void> {
  const fixturesPath = path.join(AUTH_DIR, 'fixtures.json');
  if (!fs.existsSync(fixturesPath)) {
    return; // global-setup never got far enough to create anything
  }
  const fixtures = JSON.parse(fs.readFileSync(fixturesPath, 'utf-8'));

  const api = await playwrightRequest.newContext({ baseURL: BASE_URL });
  try {
    const adminToken = await login(api, fixtures.adminEmail, fixtures.adminPassword);
    const headers = authHeaders(adminToken);

    // The guest is parented to the admin account (see global-setup.ts), and
    // we never delete the admin itself, so user_admin_svc.py's "can't delete
    // a user with active children" guard never applies here -- order is
    // just cleanup hygiene (bots/guest before the dedicated parent User).
    await deleteWithRetry(api, `/api/bot/${fixtures.botId}`, headers);
    await deleteWithRetry(api, `/api/bot/${fixtures.botId2}`, headers);
    await deleteWithRetry(api, `/api/bot/${fixtures.adminBotId}`, headers);
    await deleteWithRetry(api, `/api/users/${fixtures.guestId}`, headers);
    await deleteWithRetry(api, `/api/users/${fixtures.userId}`, headers);
  } finally {
    await api.dispose();
  }

  fs.rmSync(AUTH_DIR, { recursive: true, force: true });
}
