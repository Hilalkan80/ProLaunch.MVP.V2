import { test, expect } from '@playwright/test';

test.describe('ProLaunch MVP - Basic functionality', () => {
  test('should load the homepage', async ({ page }) => {
    await page.goto('/');
    
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle');
    
    // Check that the page has loaded
    expect(await page.title()).toBeTruthy();
    
    // Check that the page is accessible
    await expect(page).toHaveURL('/');
  });

  test('should have proper meta tags', async ({ page }) => {
    await page.goto('/');
    
    // Check for viewport meta tag
    const viewportMeta = page.locator('meta[name="viewport"]');
    await expect(viewportMeta).toHaveAttribute('content', /width=device-width/);
  });

  test('should handle navigation', async ({ page }) => {
    await page.goto('/');
    
    // Wait for any client-side routing to be ready
    await page.waitForTimeout(1000);
    
    // The page should be responsive and not have any console errors
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleLogs.push(msg.text());
      }
    });
    
    // Navigate around (this will depend on your actual routes)
    await page.waitForLoadState('networkidle');
    
    // Check that there are no console errors
    expect(consoleLogs).toHaveLength(0);
  });
});