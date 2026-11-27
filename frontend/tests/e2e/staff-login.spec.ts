import { expect, test } from '@playwright/test';
import { mockAuth, signIn } from './staff-session';

type Role = 'field' | 'estimator' | 'manager';
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
