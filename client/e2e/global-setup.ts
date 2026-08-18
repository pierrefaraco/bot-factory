import { chromium, request as playwrightRequest } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { login, authHeaders, expectOk } from './support/api-client';

const BASE_URL = process.env['E2E_BASE_URL'] || 'http://localhost:443';
const AUTH_DIR = path.join(__dirname, '.auth');
const RUN_ID = Date.now();

// There is no API to promote a fresh account to Admin (server/ai_server/
// api_controllers/rest_users_admin.py's role-change route itself requires an
// existing Admin caller) -- the only Admin identity available is the one
// seeded at server startup from SUPER_ADMIN_LOGIN/SUPER_ADMIN_PASSWORD
// (server/.env). Point these at the same values, e.g.:
//   export E2E_ADMIN_EMAIL=$SUPER_ADMIN_LOGIN
//   export E2E_ADMIN_PASSWORD=$SUPER_ADMIN_PASSWORD
const ADMIN_EMAIL = process.env['E2E_ADMIN_EMAIL'];
const ADMIN_PASSWORD = process.env['E2E_ADMIN_PASSWORD'];

export default async function globalSetup(): Promise<void> {
  if (!ADMIN_EMAIL || !ADMIN_PASSWORD) {
    throw new Error(
      'E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD must be set to the same credentials as the ' +
        "server's SUPER_ADMIN_LOGIN / SUPER_ADMIN_PASSWORD (server/.env) -- there is no API " +
        'to create a fresh Admin account, so E2E admin coverage has to authenticate as the ' +
        'pre-seeded super-admin.'
    );
  }

  fs.mkdirSync(AUTH_DIR, { recursive: true });

  const api = await playwrightRequest.newContext({ baseURL: BASE_URL });

  const adminToken = await login(api, ADMIN_EMAIL, ADMIN_PASSWORD);

  // Pydantic's EmailStr (server/ai_server/api_controllers/rest_users_admin.py)
  // rejects RFC 2606 special-use TLDs (.local, .test, .example, .invalid) as
  // syntactically invalid, not just undeliverable -- .dev is a real gTLD, so
  // it passes that check without needing a reachable mailbox.
  const userEmail = `e2e-user-${RUN_ID}@bot-factory-e2e-tests.dev`;
  const userPassword = 'E2eUserPassw0rd!23';
  const guestEmail = `e2e-guest-${RUN_ID}@bot-factory-e2e-tests.dev`;
  const guestPassword = 'E2eGuestPassw0rd!23';

  // --- Dedicated USER account -------------------------------------------
  let res = await api.post('/api/users', {
    data: { name: 'E2E Test User', email: userEmail, password: userPassword },
  });
  await expectOk(res, 'Create E2E test user');

  const userToken = await login(api, userEmail, userPassword);

  res = await api.get('/api/users/me', { headers: authHeaders(userToken) });
  await expectOk(res, 'Fetch E2E test user id');
  const userId = (await res.json()).id as number;

  // --- Two bots owned by the test user (switching between them is what
  // the triple-network-call regression, bot-workspace.spec.ts, exercises) --
  res = await api.post('/api/bot', { headers: authHeaders(userToken), data: {} });
  await expectOk(res, 'Create E2E test bot #1');
  const botId = (await res.json()).id as number;

  res = await api.post('/api/bot', { headers: authHeaders(userToken), data: {} });
  await expectOk(res, 'Create E2E test bot #2');
  const botId2 = (await res.json()).id as number;

  // A bot owned by the Admin itself, to assign to its own guest below --
  // assigning one of the User's bots (a different owner) 500'd server-side
  // (bot_assignment_svc._perform_create), so this sidesteps that rather than
  // debugging an unrelated pre-existing backend issue.
  res = await api.post('/api/bot', { headers: authHeaders(adminToken), data: {} });
  await expectOk(res, 'Create E2E admin bot');
  const adminBotId = (await res.json()).id as number;

  // Also assign it to the dedicated User (not just the guest below): "My
  // Bots" now merges owned + assigned (bot_svc.get_owned_and_assigned_bots),
  // so this gives bot-workspace.spec.ts a bot the User can see but doesn't
  // own -- distinct from botId/botId2, which it owns outright.
  res = await api.patch(`/api/users/${userId}`, {
    headers: authHeaders(adminToken),
    data: { assigned_bot_ids: [adminBotId] },
  });
  await expectOk(res, 'Assign admin bot to E2E test user');

  // --- Dedicated GUEST, parented to the ADMIN account -----------------
  // GET /users/guests (used by admin.component.ts's "Guest management"
  // table) scopes to get_children_users(caller_id) -- it lists the
  // *caller's own* children regardless of role, not every guest in the
  // system. For admin.spec.ts to see this guest at all, the guest has to
  // be created by (and so parented to) the admin identity, not the
  // dedicated User -- an Admin still has unconditional access to manage
  // it either way (authorize_user_scope), this is purely about whose
  // "children" list it shows up in.
  res = await api.post('/api/users/guest', {
    headers: authHeaders(adminToken),
    data: { name: 'E2E Test Guest', email: guestEmail, password: guestPassword },
  });
  await expectOk(res, 'Create E2E test guest');

  res = await api.get('/api/users/guests', { headers: authHeaders(adminToken) });
  await expectOk(res, 'List E2E admin guests');
  const guests: Array<{ id: number; email: string }> = await res.json();
  const guest = guests.find((g) => g.email === guestEmail);
  if (!guest) {
    throw new Error(`Created guest ${guestEmail} not found in GET /users/guests response`);
  }
  const guestId = guest.id;

  // Guests are created inactive (user_admin_svc.py) -- activate so
  // guest-access.spec.ts can actually log in as this account.
  res = await api.put(`/api/users/${guestId}/activate`, { headers: authHeaders(adminToken) });
  await expectOk(res, 'Activate E2E test guest');

  // Assign the admin-owned bot so guest-access.spec.ts can assert the guest
  // sees exactly that one bot and neither of the User's (botId/botId2),
  // matching the real access-control model: a Guest sees only what a
  // User/Admin explicitly assigned it (see MEMORY.md).
  res = await api.patch(`/api/users/${guestId}`, {
    headers: authHeaders(adminToken),
    data: { assigned_bot_ids: [adminBotId] },
  });
  await expectOk(res, 'Assign bot to E2E test guest');

  const guestToken = await login(api, guestEmail, guestPassword);

  await api.dispose();

  // --- Persist each role's session as a Playwright storageState ----------
  // The app keeps its JWT in localStorage under the key "token" (see
  // client/src/app/services/auth.service.ts) rather than a cookie, so we
  // seed it directly instead of driving the login form 3 times.
  const browser = await chromium.launch();
  const sessions: Record<string, string> = { admin: adminToken, user: userToken, guest: guestToken };
  for (const [name, token] of Object.entries(sessions)) {
    const context = await browser.newContext({ baseURL: BASE_URL });
    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.evaluate((t) => localStorage.setItem('token', t), token);
    await context.storageState({ path: path.join(AUTH_DIR, `${name}.json`) });
    await context.close();
  }
  await browser.close();

  fs.writeFileSync(
    path.join(AUTH_DIR, 'fixtures.json'),
    JSON.stringify(
      {
        adminEmail: ADMIN_EMAIL,
        adminPassword: ADMIN_PASSWORD,
        userEmail,
        userId,
        guestEmail,
        guestId,
        botId,
        botId2,
        adminBotId,
      },
      null,
      2
    )
  );
}
