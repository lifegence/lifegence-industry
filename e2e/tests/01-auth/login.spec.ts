import { test, expect } from '@playwright/test';

test.describe('Industry — Auth + landing (P0) @smoke', () => {
  test('authenticated session reaches /desk', async ({ page }) => {
    await page.goto('/desk');
    await expect(page).toHaveURL(/\/desk/);
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('Patient Encounter list loads', async ({ page }) => {
    await page.goto('/desk/patient-encounter');
    await expect(page).toHaveURL(/\/desk\/patient-encounter/);
  });

  test('Trade Shipment list loads', async ({ page }) => {
    await page.goto('/desk/trade-shipment');
    await expect(page).toHaveURL(/\/desk\/trade-shipment/);
  });
});
