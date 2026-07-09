import { test, expect } from '@playwright/test';

/**
 * E2E smoke — compliance demo stand (no auth).
 * Run: npx playwright test e2e/compliance-stand.spec.ts
 * Env: FINSKALP_STAND_URL=http://localhost:8877
 */
const STAND = process.env.FINSKALP_STAND_URL || 'http://localhost:8877';

test.describe('FinSkalp demo stand', () => {
  test('dashboard loads with command center', async ({ page }) => {
    await page.goto(STAND);
    await expect(page.locator('h2')).toContainText(/Командный центр|ФинСкальп/i);
  });

  test('OSINT view accessible via nav', async ({ page }) => {
    await page.goto(STAND);
    await page.click('button[data-view="osint"]');
    await expect(page.locator('#viewOsint')).toBeVisible();
    await expect(page.getByText(/Центр расследований|ФинСкальп/i)).toBeVisible();
  });

  test('registries table filter', async ({ page }) => {
    await page.goto(STAND);
    await page.click('button[data-view="registries"]');
    await page.waitForSelector('#registryContent', { timeout: 10000 });
    const filter = page.locator('#registryFilter');
    if (await filter.count()) {
      await filter.fill('044');
    }
  });
});
