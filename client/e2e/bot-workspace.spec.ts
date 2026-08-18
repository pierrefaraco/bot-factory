import { test, expect } from '@playwright/test';
import { loadFixtures } from './support/fixtures';

const fixtures = loadFixtures();

test.describe('Bot workspace (as a dedicated User with 2 bots)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workspace');
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.botId}` })).toBeVisible();
  });

  test('switching bots fires exactly one call each to knowledge and parameters-description', async ({ page }) => {
    // Regression for the "3 identical GET calls on bot click" bug: a
    // BehaviorSubject (communication.service.ts) replaying its last value to
    // a fresh subscriber, compounded by both an @Input/ngOnChanges reaction
    // AND a redundant ngOnInit subscription in KnowledgesComponent /
    // BotParamsComponent. Fixed by keeping ngOnChanges as the single trigger.
    const knowledgeCalls: string[] = [];
    const paramsCalls: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      // Scoped to the bot being switched *to*: a request for the previously
      // active bot that was merely still in flight when the listener
      // attached isn't part of what this test is checking.
      if (url === `${page.url().split('/workspace')[0]}/api/knowledge/${fixtures.botId2}`) {
        knowledgeCalls.push(url);
      }
      if (url.includes('/api/bot/parameters-description')) paramsCalls.push(url);
    });

    const botSwitched = page.waitForResponse((res) =>
      res.url().includes(`/api/bot/${fixtures.botId2}?view=full`)
    );
    await page.getByRole('button', { name: `Select bot ${fixtures.botId2}` }).click();
    await botSwitched; // let the switch fully settle before navigating tabs, avoids a click race
    await page.getByRole('button', { name: 'auto_stories Knowledge' }).click();
    await expect(page.getByRole('heading', { name: 'Knowledge tree' })).toBeVisible();

    await expect.poll(() => knowledgeCalls.length, { timeout: 3000 }).toBeGreaterThanOrEqual(1);
    expect(knowledgeCalls.length).toBe(1);
    expect(paramsCalls.length).toBeLessThanOrEqual(1);
  });

  test('Settings tab loads bot parameters without error', async ({ page }) => {
    await page.getByRole('button', { name: 'tune Settings' }).click();
    await expect(page.getByRole('tab', { name: 'Identity' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Bot name' })).toBeVisible();
  });

  test('a knowledge item with an empty name is selectable across its whole row', async ({ page }) => {
    // Regression for the dead-space bug: .node-container had no explicit
    // width, so it only spanned its content (icon + name). With an empty
    // name that's ~70px out of a ~640px row -- clicking anywhere else did
    // nothing. Fixed with `width: 100%` on .node-container.
    await page.getByRole('button', { name: 'auto_stories Knowledge' }).click();
    await page.getByRole('button', { name: 'add', exact: true }).click();

    const item = page.getByRole('tree').getByRole('treeitem').first();
    await expect(item).toBeVisible();

    const responsePromise = page.waitForResponse((res) =>
      /\/api\/knowledge\/\d+\/\d+$/.test(res.url())
    );
    await item.click(); // default click = center of the row's bounding box
    await responsePromise;

    await expect(page.getByText('Select an item in the knowledge tree')).not.toBeVisible();
  });

  test('Avatar tab renders the avatar builder when opened in-app', async ({ page }) => {
    await page.getByRole('button', { name: 'brush Avatar' }).click();
    await expect(page.getByRole('heading', { name: /^Avatar of/ })).toBeVisible();
  });

  test('an unrecognized ?tab= value falls back to a valid tab instead of a blank page', async ({ page }) => {
    // Regression: activeTab was assigned straight from the query param with
    // no validation, so a typo'd/stale value (e.g. the very natural-looking
    // ?tab=avatar, when the real key is ?tab=draw) matched no *ngIf branch
    // and left the whole content panel empty.
    await page.goto('/workspace?tab=avatar');
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.botId}` })).toBeVisible();
    await expect(page.getByRole('button', { name: 'dashboard Overview' })).toHaveClass(/active/);
    await expect(page.getByRole('heading', { name: /^Chat with/ })).toBeVisible();
  });

  test('"My Bots" lists bots the User owns and bots merely assigned to them', async ({ page }) => {
    // Regression: GET /bot/me only ever returned bot_svc.get_bots_by_user()
    // (owned only) for User/Admin -- a bot assigned to a User by someone
    // else (adminBotId here, see global-setup.ts) never showed up at all,
    // unlike for a Guest (always assigned-only). Fixed with
    // bot_svc.get_owned_and_assigned_bots(), merging both.
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.botId2}` })).toBeVisible();
    await expect(page.getByRole('button', { name: `Select bot ${fixtures.adminBotId}` })).toBeVisible();
  });

  test('"Delete selected bot" only appears for a bot the User actually owns', async ({ page }) => {
    // Regression: DELETE /api/bot/<id> is ownership-scoped server-side
    // (_can_modify_bot) -- now that "My Bots" also lists assigned-but-not-
    // owned bots, selecting one and hitting delete would otherwise be a
    // guaranteed 403.
    await page.getByRole('button', { name: `Select bot ${fixtures.botId}` }).click();
    await expect(page.getByRole('button', { name: /More actions for/ })).toBeVisible();

    const botSwitched = page.waitForResponse((res) =>
      res.url().includes(`/api/bot/${fixtures.adminBotId}?view=full`)
    );
    await page.getByRole('button', { name: `Select bot ${fixtures.adminBotId}` }).click();
    await botSwitched;
    await expect(page.getByRole('button', { name: /More actions for/ })).toHaveCount(0);
  });
});
