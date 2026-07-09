import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: process.env.FINSKALP_STAND_URL || 'http://localhost:8877',
    trace: 'on-first-retry',
  },
});
