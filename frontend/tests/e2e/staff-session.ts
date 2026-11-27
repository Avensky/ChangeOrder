import { expect, type Page } from '@playwright/test';

// All identities and credentials below are synthetic. No live project is used.
export async function mockAuth(page: Page, role: string, options: { reject?: boolean; badPassword?: boolean; expire?: boolean; staff401?: boolean } = {}) {
  const calls = { staff: 0, me: 0 };
  await page.route('https://u6-test.supabase.co/**', route => options.badPassword
    ? route.fulfill({ status: 400, json: { error_code: 'invalid_credentials', msg: 'Invalid login credentials' } })
    : route.fulfill({ json: {
      access_token: 'synthetic-access', refresh_token: 'synthetic-refresh',
      expires_in: options.expire ? 3 : 3600, token_type: 'bearer',
      user: { id: '11111111-1111-4111-8111-111111111111', aud: 'authenticated', app_metadata: { role: 'manager' }, user_metadata: { role: 'manager' } },
    } }));
  await page.route('**/api/v1/**', async route => {
    expect(route.request().headers().authorization).toBe('Bearer synthetic-access');
    if (new URL(route.request().url()).pathname.endsWith('/me')) {
      calls.me++;
      await route.fulfill(options.reject ? { status: 401, json: { detail: 'Sign in again' } } : { json: { id: 7, name: 'Verified Staff', role } });
    } else {
      calls.staff++;
      await route.fulfill(options.staff401 ? { status: 401, json: { detail: 'Sign in again' } } : { json: [] });
    }
  });
  return calls;
}
export async function signIn(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('staff@example.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}
