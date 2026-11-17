import { expect, test, type Page } from '@playwright/test';

// All identities and credentials below are synthetic. No live project is used.
type Role = 'field' | 'estimator' | 'manager';
async function mockAuth(page: Page, role: string, options: { reject?: boolean; badPassword?: boolean; expire?: boolean; staff401?: boolean } = {}) {
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
async function signIn(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email', { exact: true }).fill('staff@example.com');
  await page.getByLabel('Password', { exact: true }).fill('synthetic-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}
for (const role of ['field', 'estimator', 'manager'] as Role[]) {
  test(`${role} uses the verified API role and can sign out`, async ({ page }) => {
    const calls = await mockAuth(page, role);
    await page.goto('/');
    await expect(page.getByText('Staff sign-in', { exact: true })).toBeVisible();
    expect(calls.staff).toBe(0);
    await signIn(page);
    const heading = role === 'field' ? 'Field submissions' : role === 'estimator' ? 'Estimator review' : 'Work authorizations';
    await expect(page.getByText(heading, { exact: true }).filter({ visible: true }).first()).toBeVisible();
    await page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).first().click();
    await expect(page.getByText('Signed in as ' + role, { exact: true })).toBeVisible();
    expect(calls.me).toBe(1);
    expect(calls.staff).toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: 'Preview role', exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => Object.keys(localStorage).some(key => key.includes('supabase') || key.includes('auth-token')))).toBe(false);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await expect(page.getByText('Staff sign-in', { exact: true })).toBeVisible();
  });
}
for (const scenario of ['rejected', 'unknown-role', 'wrong-password'] as const) {
  test(`${scenario} cannot open a staff workspace`, async ({ page }) => {
    const calls = await mockAuth(page, scenario === 'unknown-role' ? 'gc' : 'manager', { reject: scenario === 'rejected', badPassword: scenario === 'wrong-password' });
    await signIn(page);
    await expect(page.getByRole('alert')).toBeVisible();
    expect(calls.staff).toBe(0);
    await expect(page.getByLabel('Password', { exact: true })).toHaveValue('');
  });
}
test('expired session returns to login', async ({ page }) => {
  await mockAuth(page, 'manager', { expire: true });
  await signIn(page);
  await expect(page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).first()).toBeVisible();
  await expect(page.getByText('Staff sign-in', { exact: true })).toBeVisible({ timeout: 7000 });
});
test('staff 401 clears the session', async ({ page }) => {
  const calls = await mockAuth(page, 'manager', { staff401: true });
  await signIn(page);
  await expect.poll(() => calls.staff).toBeGreaterThan(0);
  await expect(page.getByText('Staff sign-in', { exact: true })).toBeVisible();
});
test('reload requires a fresh sign-in', async ({ page }) => {
  await mockAuth(page, 'manager'); await signIn(page);
  await expect(page.getByRole('button', { name: 'Settings', exact: true }).filter({ visible: true }).first()).toBeVisible();
  await page.reload();
  await expect(page.getByText('Staff sign-in', { exact: true })).toBeVisible();
});
test('GC link stays anonymous and opening it never decides', async ({ page }) => {
  let staff = 0, writes = 0, auth = 0;
  await page.route('https://u6-test.supabase.co/**', route => { auth++; return route.abort(); });
  await page.route('**/api/v1/**', async route => {
    if (!route.request().url().includes('/approval-session')) staff++;
    if (route.request().method() !== 'GET') writes++;
    expect(route.request().headers().authorization).toBeUndefined();
    await route.fulfill({ json: { title: 'Public GC proposal', status: 'awaiting_gc', description: 'Reviewed scope', amount: 10, impact_days: 1, photo_keys: [] } });
  });
  await page.goto('/approve?token=synthetic-link');
  await expect(page.getByText('Public GC proposal', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Approve change', exact: true })).toBeVisible();
  expect({ staff, writes, auth }).toEqual({ staff: 0, writes: 0, auth: 0 });
});

test('unknown public route renders without a workspace', async ({ page }) => {
  await page.goto('/does-not-exist');
  await expect(page.getByText('Page not found', { exact: true })).toBeVisible();
});
