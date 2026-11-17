import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: { channel: 'chromium', baseURL: 'http://127.0.0.1:8123', viewport: { width: 390, height: 844 } },
  webServer: {
    command: 'npm run e2e:serve',
    url: 'http://127.0.0.1:8123',
    timeout: 180_000,
    reuseExistingServer: false,
    env: {
      EXPO_NO_TELEMETRY: '1',
      EXPO_NO_CACHE: '1',
      EXPO_PUBLIC_API_URL: 'http://127.0.0.1:8000',
      EXPO_PUBLIC_SUPABASE_URL: 'https://u6-test.supabase.co',
      EXPO_PUBLIC_SUPABASE_ANON_KEY: 'public-test-key',
    },
  },
});
