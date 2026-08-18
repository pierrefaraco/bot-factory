import { test, expect } from '@playwright/test';

// "user" project storageState -- the dedicated regular User account.

test.describe('Administration access (as a plain User)', () => {
  test('the Users tab is hidden, but Overview (own guests) still works', async ({ page }) => {
    // Regression: GET /users (the Users tab's data source) is
    // role_required([ADMIN_ROLE]) -- a User caller always got a guaranteed
    // 403 from it, yet AdminComponent fired it unconditionally on
    // ngOnInit and showed the tab button to everyone. A User's own guest
    // management (Overview tab, GET /users/guests) IS meant to work, so
    // that one stays.
    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: 'User management' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'people Users' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Guest management' })).toBeVisible();
  });

  test('a User never calls GET /users', async ({ page }) => {
    const calls: string[] = [];
    page.on('request', (req) => {
      if (/\/api\/users$/.test(req.url()) && req.method() === 'GET') {
        calls.push(req.url());
      }
    });
    await page.goto('/admin');
    await expect(page.getByRole('heading', { name: 'User management' })).toBeVisible();
    expect(calls).toEqual([]);
  });

  test('GET /users is rejected outright for a User at the API level', async ({ page }) => {
    // Defense-in-depth check independent of the UI: role_required([ADMIN_ROLE])
    // on the route itself, not just the frontend hiding the button.
    await page.goto('/admin');
    const status = await page.evaluate(async () => {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } });
      return res.status;
    });
    expect(status).toBe(403);
  });
});
