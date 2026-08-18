import { test, expect } from '@playwright/test';

// Unauthenticated project (no storageState) -- exercises /auth directly.

test.describe('Authentication', () => {
  test('login form renders with email, password and a submit button', async ({ page }) => {
    await page.goto('/auth');
    await expect(page.getByRole('heading', { name: 'Welcome' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Email' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Password' })).toBeVisible();
    await expect(page.locator('form.auth-form').getByRole('button', { name: 'Sign in' })).toBeVisible();
  });

  test('invalid credentials show the error dialog instead of failing silently', async ({ page }) => {
    // Regression for 8945d6c ("fix(auth): show the invalid-credentials
    // popup instead of silently failing"): errorInterceptor
    // (jwt.interceptor.ts) special-cases /auth/login 401s so
    // ErrorNotificationService still shows its dialog for them, even though
    // 401s are suppressed everywhere else (they normally mean "session
    // expired", not "this specific request failed").
    await page.goto('/auth');
    await page.getByRole('textbox', { name: 'Email' }).fill('nobody@bot-factory.local');
    await page.getByRole('textbox', { name: 'Password' }).fill('definitely-wrong-password');
    await page.locator('form.auth-form').getByRole('button', { name: 'Sign in' }).click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Something went wrong')).toBeVisible();

    // And the SPA must still be sitting on /auth, not stuck mid-navigation.
    await expect(page).toHaveURL(/\/auth$/);
  });
});
