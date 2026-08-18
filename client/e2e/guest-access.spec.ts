import { test, expect } from '@playwright/test';
import { loadFixtures } from './support/fixtures';

const fixtures = loadFixtures();

test.describe('Access control (as the dedicated Guest)', () => {
  test('a Guest only sees the bot explicitly assigned to it', async ({ page }) => {
    // Encodes the constraint from this project's access-control model: a
    // Guest gets exactly what a User/Admin assigned it. global-setup.ts
    // assigns only its own admin-owned bot (adminBotId) to this guest --
    // neither of the unrelated dedicated User's bots (botId/botId2) should
    // ever be visible here.
    await page.goto('/workspace');
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.adminBotId}` })).toBeVisible();
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.botId}` })).toHaveCount(0);
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.botId2}` })).toHaveCount(0);
  });

  test('selecting a bot as a Guest never calls knowledge, parameters-description, avatar, create or delete', async ({ page }) => {
    // Regression: GET /api/knowledge/<id>, GET /api/bot/parameters-
    // description, PATCH /api/avatar, POST /api/bot and DELETE
    // /api/bot/<id> are all role_required([ADMIN_ROLE, USER_ROLE])
    // server-side -- GUEST is deliberately excluded. <app-knowledges>/
    // <app-bot-params>/<app-bot-draw> used to be rendered unconditionally on
    // hasSelectedBot regardless of role, both "Create a new bot" buttons
    // were visible to everyone, and the "More actions" menu (delete) had no
    // role check either, so a Guest selecting a bot (or clicking around)
    // could fire requests guaranteed to 403. Fixed by gating the Settings/
    // Knowledge/Avatar tabs, their child components, both create-bot
    // buttons and the delete menu on `!isGuest` (bot-workspace.component.ts).
    const restrictedCalls: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      const method = req.method();
      if (
        /\/api\/knowledge\/\d+$/.test(url) ||
        url.includes('/api/bot/parameters-description') ||
        (url.includes('/api/avatar') && method === 'PATCH') ||
        (url.endsWith('/api/bot') && method === 'POST') ||
        (/\/api\/bot\/\d+$/.test(url) && method === 'DELETE')
      ) {
        restrictedCalls.push(`${method} ${url}`);
      }
    });

    await page.goto('/workspace');
    await expect(page.getByRole('button', { name: 'add_circle Create a new bot' })).toHaveCount(0);

    await page.getByRole('button', { name: `Select bot ${fixtures.adminBotId}` }).click();
    await expect(page.getByRole('heading', { name: /^Chat with/ })).toBeVisible();

    await expect(page.getByRole('button', { name: 'tune Settings' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'auto_stories Knowledge' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'brush Avatar' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /More actions for/ })).toHaveCount(0);
    expect(restrictedCalls).toEqual([]);
  });

  test('a Guest cannot list another user\'s guests via the admin API', async ({ page }) => {
    // GET /users/guests is role_required([ADMIN_ROLE, USER_ROLE]) -- GUEST
    // must be rejected at the decorator, before any parent_id logic runs.
    // Auth is a JWT in localStorage (not a cookie -- see auth.service.ts),
    // so this has to run through page.evaluate to pick up the same
    // Authorization header the app's own HttpInterceptor would attach;
    // page.request wouldn't see it.
    await page.goto('/workspace');
    const status = await page.evaluate(async () => {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/users/guests', {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.status;
    });
    expect(status).toBe(403);
  });
});
