import { test, expect, Page } from '@playwright/test';
import { loadFixtures } from './support/fixtures';

const fixtures = loadFixtures();

function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => {
    // Chromium logs failed network requests (missing favicon, etc.) as
    // console "error" entries too -- unrelated browser-level noise, not an
    // application bug, so it's excluded from this check.
    if (msg.type() === 'error' && !msg.text().startsWith('Failed to load resource')) {
      errors.push(msg.text());
    }
  });
  return errors;
}

test.describe('Administration (as the seeded super-admin)', () => {
  test('loading /admin triggers no console errors', async ({ page }) => {
    // Regression for NG0100 (ExpressionChangedAfterItHasBeenCheckedError):
    // the `paginatedUsers` getter read a @ViewChild that isn't resolved
    // until after the first change-detection pass, returning `undefined`
    // then `[]` within the same tick. Fixed with `?? []` in the getter.
    const errors = collectPageErrors(page);
    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: 'User management' })).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('the summary cards (Total/Active guests, Assigned bots) are gone', async ({ page }) => {
    // Scoped to the card classes, not their label text: "Assigned bots"
    // would otherwise substring/case-insensitively match the Overview
    // tab's still-present "Assigned Bots" column header.
    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: 'User management' })).toBeVisible();
    await expect(page.locator('.quick-summary')).toHaveCount(0);
    await expect(page.locator('.summary-card')).toHaveCount(0);
  });

  test('the dedicated E2E guest is listed', async ({ page }) => {
    await page.goto('/admin');
    // admin.component.html renders the same guest table twice (Overview tab
    // + Users tab), toggling visibility with a CSS class rather than *ngIf,
    // so both copies exist in the DOM at once -- .first() picks the visible
    // (Overview, active by default) one.
    await expect(page.getByRole('cell', { name: fixtures.guestEmail }).first()).toBeVisible();
  });

  test('toggling guest activation twice fires no console errors', async ({ page }) => {
    // Regression: a stray data-bs-toggle="dropdown" on the plain
    // activate/deactivate button (not a real Bootstrap dropdown) made
    // Bootstrap register a Dropdown instance on it. Angular's *ngFor (no
    // trackBy) destroys and recreates every row after the list reloads,
    // orphaning that instance -> "Cannot read properties of null (reading
    // 'classList')" on the next click. Fixed by removing the attribute from
    // that button while keeping it on the real dropdown trigger (more_vert).
    const errors = collectPageErrors(page);
    await page.goto('/admin');

    const row = page.locator('.tab-pane.active').getByRole('row', { name: new RegExp(fixtures.guestEmail) });
    const toggleButton = row.getByRole('button', { name: 'more' }).first();

    const deactivated = page.waitForResponse((res) => /\/api\/users\/\d+\/deactivate$/.test(res.url()));
    await toggleButton.click();
    await deactivated; // wait for the *ngFor list to actually re-render before clicking again

    const reactivated = page.waitForResponse((res) => /\/api\/users\/\d+\/activate$/.test(res.url()));
    await toggleButton.click();
    await reactivated;

    expect(errors).toEqual([]);
  });

  test('the row action menu (Edit/Assign Bot/Change Password/Delete) still opens', async ({ page }) => {
    // Regression guard for the fix above: removing data-bs-toggle from the
    // wrong button must not also break the *real* dropdown, which still
    // needs it -- CustomDropDownMenuComponent has no open/close logic of
    // its own, it's driven entirely by Bootstrap's .dropdown/.show markup.
    await page.goto('/admin');
    const activePane = page.locator('.tab-pane.active');
    const row = activePane.getByRole('row', { name: new RegExp(fixtures.guestEmail) });
    await row.getByRole('button', { name: 'more' }).last().click();

    // Every row's menu items are always in the DOM (Bootstrap toggles a CSS
    // class, not *ngIf), so scope to this row's own dropdown rather than
    // page-wide -- otherwise every other guest's (and the duplicate tab's)
    // hidden copies match too.
    // Scoped to .item-label: the mat-icon ligature text ("delete") and the
    // label div ("Delete") both independently contain-match a bare
    // getByText('Delete'), since Playwright counts ancestor and descendant
    // as separate matches when both contain the string.
    const menu = row.locator('app-custom-dropdown-menu').locator('.item-label');
    await expect(menu.getByText('Edit User')).toBeVisible();
    await expect(menu.getByText('Assign Bot')).toBeVisible();
    await expect(menu.getByText('Change Password')).toBeVisible();
    await expect(menu.getByText('Delete')).toBeVisible();
  });

  test('Users tab shows every platform user, not just the admin\'s own guests, with correct role/parent data', async ({ page }) => {
    // Regression: this tab used to bind to the exact same `guestUsers` data
    // source as Overview (GET /users/guests, scoped to the caller's own
    // children) -- copy-pasted markup ("All users" heading, but a guest-only
    // dataset) that never actually called GET /users (admin-only, every
    // platform user).
    await page.goto('/admin');
    await page.getByRole('button', { name: 'people Users' }).click();

    // .first(): each <td appColumn> cell wraps its content in a nested
    // .centered-cell div, and Playwright counts the ancestor <td> and that
    // descendant div as two separate role="cell" matches when both contain
    // the same text (same pattern already hit for "Delete" above).
    // The dedicated E2E User is nobody's guest -- it would never appear on
    // the guest-only Overview tab, proving this one pulls a wider dataset.
    await expect(page.getByRole('cell', { name: fixtures.userEmail }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: fixtures.guestEmail }).first()).toBeVisible();

    // "Parent" column: the dedicated guest is parented to the Admin (see
    // global-setup.ts), and the dedicated User has no parent (self-
    // registered, parent_id -1) -- user_admin_svc.py's _perform_get_all
    // resolves parent_id -> parent_email server-side, since the parent can
    // itself be an Admin (excluded from this same list, so the frontend
    // can't always resolve it by matching parent_id locally).
    const guestRow = page.getByRole('row', { name: new RegExp(fixtures.guestEmail) });
    await expect(guestRow.getByText(fixtures.adminEmail)).toBeVisible();

    const userRow = page.getByRole('row', { name: new RegExp(fixtures.userEmail) });
    await expect(userRow.getByText('No parent')).toBeVisible();

    // "Bots" column: different relationship depending on role. The
    // dedicated Guest has 1 bot assigned to it (adminBotId, see
    // global-setup.ts); the dedicated User owns 2 (botId, botId2) --
    // scoped to the 5th <td> (Activate, Email, Role, Parent, Bots,
    // Actions) since a bare count like "2" would otherwise be ambiguous.
    await expect(guestRow.locator('td:nth-child(5)')).toHaveText('1');
    await expect(userRow.locator('td:nth-child(5)')).toHaveText('2');
  });

  test('changing a user\'s role updates it via PUT /users/<id>/role, and the admin\'s own row never appears', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: 'people Users' }).click();

    const userRow = page.getByRole('row', { name: new RegExp(fixtures.userEmail) });
    const roleSelect = userRow.getByRole('combobox');
    await expect(roleSelect).toHaveValue('User');

    const roleChanged = page.waitForResponse(
      (res) => res.url().endsWith(`/api/users/${fixtures.userId}/role`) && res.request().method() === 'PUT'
    );
    await roleSelect.selectOption('Guest');
    await roleChanged;
    await expect(roleSelect).toHaveValue('Guest');

    // Revert, so this test is repeatable and doesn't leave the fixture in a
    // different state than global-setup.ts created it in.
    const reverted = page.waitForResponse(
      (res) => res.url().endsWith(`/api/users/${fixtures.userId}/role`) && res.request().method() === 'PUT'
    );
    await roleSelect.selectOption('User');
    await reverted;

    // _perform_get_all excludes every Admin row, including the caller's
    // own -- not just disabled, entirely absent (see the dedicated test
    // for GET /users below), so there's nothing to self-protect against
    // in the UI: the row this would apply to simply never renders.
    // Scoped to the Email column specifically (2nd <td>, after Activate):
    // a bare row-text match would also catch guests whose "Parent" column
    // (4th <td>) happens to show the admin's email too.
    const emailColumnCells = page.locator('.tab-pane.active table tbody tr td:nth-child(2)');
    await expect(emailColumnCells.filter({ hasText: fixtures.adminEmail })).toHaveCount(0);
  });

  test('the Activate column deactivates/reactivates a plain User from the Users tab', async ({ page }) => {
    // Regression: only the Overview tab (guests) had an Activate toggle --
    // the Users tab had no way to deactivate a plain User at all despite
    // PUT /users/<id>/deactivate working for any role via authorize_user_scope.
    await page.goto('/admin');
    await page.getByRole('button', { name: 'people Users' }).click();

    const userRow = page.getByRole('row', { name: new RegExp(fixtures.userEmail) });
    const toggleButton = userRow.getByRole('button', { name: 'more' }).first();

    const deactivated = page.waitForResponse(
      (res) => res.url().endsWith(`/api/users/${fixtures.userId}/deactivate`) && res.request().method() === 'PUT'
    );
    await toggleButton.click();
    await deactivated;

    const reactivated = page.waitForResponse(
      (res) => res.url().endsWith(`/api/users/${fixtures.userId}/activate`) && res.request().method() === 'PUT'
    );
    await toggleButton.click();
    await reactivated;
  });

  test('promoting a user to Admin via PUT /users/<id>/role is rejected outright', async ({ page }) => {
    // Regression: RoleChangeRequest (rest_users_admin.py) no longer accepts
    // "Admin" as a target role at all -- there is now no API path to create
    // a second Admin account, period. (authorize_user_scope's "no admin
    // acts on another admin" rule stays in the code as defense-in-depth for
    // whatever *does* get seeded as a second Admin some other way, e.g. a
    // future DB migration, but that's no longer reachable from this route
    // and isn't covered here to avoid stranding a fixture -- see git log
    // for the version of this test that verified it live.)
    await page.goto('/admin'); // storageState's localStorage token only applies once a page has loaded this origin

    const status = await page.evaluate(async (userId) => {
      const token = localStorage.getItem('token');
      const res = await fetch(`/api/users/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: 'Admin' }),
      });
      return res.status;
    }, fixtures.userId);

    expect(status).toBe(400);

    // The dedicated User's role must be untouched by the rejected attempt.
    const res = await page.evaluate(async () => {
      const token = localStorage.getItem('token');
      const r = await fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } });
      return r.json();
    });
    const target = res.users.find((u: { id: number }) => u.id === fixtures.userId);
    expect(target.roles).toBe('User');
  });

  test('GET /users and GET /users/role/Admin only ever return the caller\'s own Admin account', async ({ page }) => {
    // Regression: GET /users/role/<role> is a *separate* method
    // (_perform_get_by_role) from GET /users (_perform_get_all) and
    // accepts role=Admin same as any other role -- it was a second,
    // completely unfiltered way to list every Admin in the system,
    // bypassing the exclusion added to _perform_get_all. There's no API
    // path left to create a second real Admin to prove the exclusion case
    // positively, so this asserts the invariant that holds regardless:
    // every "Admin" row returned by either endpoint is the caller's own.
    await page.goto('/admin');

    const result = await page.evaluate(async () => {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const [allRes, roleRes] = await Promise.all([
        fetch('/api/users', { headers }),
        fetch('/api/users/role/Admin', { headers }),
      ]);
      const [all, byRole] = await Promise.all([allRes.json(), roleRes.json()]);
      return { allUsers: all.users, adminsByRole: byRole.users };
    });

    const adminsFromAllUsers = result.allUsers.filter((u: { roles: string }) => u.roles === 'Admin');
    for (const admin of [...adminsFromAllUsers, ...result.adminsByRole]) {
      expect(admin.email).toBe(fixtures.adminEmail);
    }
  });
});
