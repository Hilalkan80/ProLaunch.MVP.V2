import { test, expect, Page } from '@playwright/test';
import { MockApiHelper } from '../utils/mock-api-helper';

test.describe('M0 Components Integration Tests', () => {
  let mockApi: MockApiHelper;
  
  test.beforeEach(async ({ page }) => {
    mockApi = new MockApiHelper(page);
    await mockApi.setupMocks();
  });

  test.describe('End-to-End User Flows', () => {
    test('complete feasibility analysis flow', async ({ page }) => {
      // Navigate to M0 demo page
      await page.goto('/m0-demo');
      
      // Verify initial state
      await expect(page.getByTestId('m0-container')).toBeVisible();
      await expect(page.getByTestId('input-state')).toBeVisible();
      await expect(page.getByTestId('hero-title')).toContainText('AI Co-Pilot for Ecommerce Validation');
      
      // Fill in product idea
      const productIdea = 'Organic dog treats made from locally sourced ingredients';
      await page.getByTestId('product-idea-textarea').fill(productIdea);
      
      // Verify form validation
      await expect(page.getByTestId('submit-button')).toBeEnabled();
      await expect(page.getByTestId('character-counter')).toContainText(`${productIdea.length}/500`);
      
      // Submit form
      await page.getByTestId('submit-button').click();
      
      // Verify processing state
      await expect(page.getByTestId('processing-state')).toBeVisible();
      await expect(page.getByTestId('processing-title')).toContainText('Analyzing Your Product Idea');
      await expect(page.getByTestId('product-idea-display')).toContainText(productIdea);
      
      // Wait for processing to complete (with timeout)
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      // Verify success state
      await expect(page.getByTestId('feasibility-report')).toBeVisible();
      await expect(page.getByTestId('viability-score')).toBeVisible();
      await expect(page.getByTestId('market-insights')).toBeVisible();
      await expect(page.getByTestId('competitors-section')).toBeVisible();
      await expect(page.getByTestId('next-steps-section')).toBeVisible();
    });

    test('user flow with suggestion chips', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Click on a suggestion chip
      await page.getByTestId('suggestion-chip-organic-dog-treats').click();
      
      // Verify the textarea is populated
      await expect(page.getByTestId('product-idea-textarea')).toHaveValue('Organic dog treats');
      
      // Submit and verify flow continues
      await page.getByTestId('submit-button').click();
      await expect(page.getByTestId('processing-state')).toBeVisible();
    });

    test('complete flow with retry on network error', async ({ page }) => {
      // Setup network error first
      await mockApi.simulateNetworkError();
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Smart home gadget');
      await page.getByTestId('submit-button').click();
      
      // Verify network error state
      await expect(page.getByTestId('network-error-state')).toBeVisible();
      await expect(page.getByText('Connection failed')).toBeVisible();
      
      // Reset API to working state
      await mockApi.resetMocks();
      
      // Retry should happen automatically
      await expect(page.getByTestId('processing-state')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Component Interactions', () => {
    test('form validation and character counter', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const textarea = page.getByTestId('product-idea-textarea');
      const submitButton = page.getByTestId('submit-button');
      const characterCounter = page.getByTestId('character-counter');
      
      // Test empty state
      await expect(submitButton).toBeDisabled();
      await expect(characterCounter).toContainText('0/500');
      
      // Test too short
      await textarea.fill('short');
      await expect(page.getByTestId('product-idea-error')).toContainText('at least 10 characters');
      await expect(submitButton).toBeDisabled();
      
      // Test valid input
      await textarea.fill('This is a valid product idea description');
      await expect(page.getByTestId('product-idea-error')).not.toBeVisible();
      await expect(submitButton).toBeEnabled();
      
      // Test too long
      const longText = 'a'.repeat(501);
      await textarea.fill(longText);
      await expect(page.getByTestId('product-idea-error')).toContainText('under 500 characters');
      await expect(submitButton).toBeDisabled();
    });

    test('clear button functionality', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const textarea = page.getByTestId('product-idea-textarea');
      const clearButton = page.getByTestId('clear-button');
      
      // Clear button should be disabled initially
      await expect(clearButton).toBeDisabled();
      
      // Fill textarea
      await textarea.fill('Some product idea');
      await expect(clearButton).toBeEnabled();
      
      // Click clear
      await clearButton.click();
      await expect(textarea).toHaveValue('');
      await expect(clearButton).toBeDisabled();
    });

    test('keyboard shortcuts', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const textarea = page.getByTestId('product-idea-textarea');
      
      // Fill valid input
      await textarea.fill('Valid product idea for testing keyboard shortcuts');
      
      // Press Enter to submit
      await textarea.press('Enter');
      await expect(page.getByTestId('processing-state')).toBeVisible();
      
      // Reset and test Shift+Enter for new line
      await page.reload();
      await textarea.fill('Line 1');
      await textarea.press('Shift+Enter');
      await textarea.type('Line 2');
      
      const value = await textarea.inputValue();
      expect(value).toContain('\n');
    });

    test('processing step interactions', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Start processing
      await page.getByTestId('product-idea-textarea').fill('Test product for step interactions');
      await page.getByTestId('submit-button').click();
      
      // Verify processing view components
      await expect(page.getByTestId('processing-header')).toBeVisible();
      await expect(page.getByTestId('overall-progress')).toBeVisible();
      await expect(page.getByTestId('current-step-highlight')).toBeVisible();
      await expect(page.getByTestId('steps-list')).toBeVisible();
      
      // Verify time elapsed is updating
      const timeElapsed = page.getByTestId('time-elapsed');
      await expect(timeElapsed).toContainText('0:00');
      await page.waitForTimeout(2000);
      await expect(timeElapsed).toContainText('0:0');
      
      // Test cancel functionality
      const cancelButton = page.getByTestId('cancel-analysis-button');
      if (await cancelButton.isVisible()) {
        await cancelButton.click();
        await expect(page.getByTestId('input-state')).toBeVisible();
      }
    });
  });

  test.describe('State Management', () => {
    test('state transitions and persistence', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Test state transition from input to processing
      await page.getByTestId('product-idea-textarea').fill('State management test product');
      await page.getByTestId('submit-button').click();
      
      // Wait for processing
      await expect(page.getByTestId('processing-state')).toBeVisible();
      
      // Verify data persistence during processing
      await expect(page.getByTestId('product-idea-display')).toContainText('State management test product');
      
      // Wait for completion
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      // Verify data is still available in success state
      const reportContainer = page.getByTestId('feasibility-report');
      await expect(reportContainer).toBeVisible();
    });

    test('error state recovery', async ({ page }) => {
      // Simulate processing error
      await mockApi.simulateProcessingError();
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Error test product');
      await page.getByTestId('submit-button').click();
      
      // Wait for error state
      await expect(page.getByTestId('error-state')).toBeVisible();
      
      // Test retry functionality
      await mockApi.resetMocks();
      await page.getByTestId('retry-button').click();
      
      // Should go back to processing
      await expect(page.getByTestId('processing-state')).toBeVisible();
    });

    test('start over functionality', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Complete a full flow
      await page.getByTestId('product-idea-textarea').fill('Complete flow test product');
      await page.getByTestId('submit-button').click();
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      // Click start over
      await page.getByTestId('new-analysis-button').click();
      
      // Verify we're back to initial state
      await expect(page.getByTestId('input-state')).toBeVisible();
      await expect(page.getByTestId('product-idea-textarea')).toHaveValue('');
    });
  });

  test.describe('API Integration', () => {
    test('successful API responses', async ({ page }) => {
      const mockData = {
        productIdea: 'API test product',
        viabilityScore: 85,
        marketSize: '$3.5B',
        growthRate: '18% YoY'
      };
      
      await mockApi.mockSuccessfulAnalysis(mockData);
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill(mockData.productIdea);
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      // Verify API data is displayed correctly
      await expect(page.getByTestId('viability-score')).toContainText('85');
      await expect(page.getByText('$3.5B')).toBeVisible();
      await expect(page.getByText('18% YoY')).toBeVisible();
    });

    test('API timeout handling', async ({ page }) => {
      await mockApi.simulateTimeout();
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Timeout test product');
      await page.getByTestId('submit-button').click();
      
      // Should show network error after timeout
      await expect(page.getByTestId('network-error-state')).toBeVisible({ timeout: 35000 });
    });

    test('invalid API responses', async ({ page }) => {
      await mockApi.mockInvalidResponse();
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Invalid response test');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('error-state')).toBeVisible();
      await expect(page.getByText('Invalid response format')).toBeVisible();
    });
  });

  test.describe('Error Scenarios', () => {
    test('network connectivity issues', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Go offline
      await page.context().setOffline(true);
      
      await page.getByTestId('product-idea-textarea').fill('Offline test product');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('network-error-state')).toBeVisible();
      
      // Come back online
      await page.context().setOffline(false);
      await mockApi.resetMocks();
      
      // Should auto-retry
      await expect(page.getByTestId('processing-state')).toBeVisible({ timeout: 10000 });
    });

    test('server error responses', async ({ page }) => {
      await mockApi.mockServerError(500);
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Server error test');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('error-state')).toBeVisible();
      await expect(page.getByText('Server error')).toBeVisible();
    });

    test('rate limiting scenarios', async ({ page }) => {
      await mockApi.mockRateLimitError();
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Rate limit test');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('error-state')).toBeVisible();
      await expect(page.getByText('Too many requests')).toBeVisible();
    });
  });

  test.describe('Loading States', () => {
    test('form loading state', async ({ page }) => {
      await page.goto('/m0-demo');
      
      await page.getByTestId('product-idea-textarea').fill('Loading state test');
      await page.getByTestId('submit-button').click();
      
      // Verify loading state
      await expect(page.getByTestId('submit-button')).toContainText('Analyzing...');
      await expect(page.getByTestId('submit-button')).toBeDisabled();
      await expect(page.getByTestId('product-idea-textarea')).toBeDisabled();
    });

    test('processing steps loading', async ({ page }) => {
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Processing steps test');
      await page.getByTestId('submit-button').click();
      
      // Verify processing indicators
      await expect(page.getByTestId('processing-loader')).toBeVisible();
      await expect(page.getByTestId('overall-progress')).toBeVisible();
      
      // Check for step progression
      const steps = ['market-research', 'competitor-analysis', 'pricing-analysis'];
      for (const stepId of steps) {
        await expect(page.getByTestId(`processing-step-${stepId}`)).toBeVisible();
      }
    });

    test('skeleton loading for report data', async ({ page }) => {
      await mockApi.mockSlowResponse(5000);
      
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Slow loading test');
      await page.getByTestId('submit-button').click();
      
      // Should show processing state with loading indicators
      await expect(page.getByTestId('processing-state')).toBeVisible();
      await expect(page.locator('[data-testid*="loading"]')).toHaveCount({ greaterThan: 0 });
    });
  });

  test.describe('Share Functionality', () => {
    test('share URL generation', async ({ page }) => {
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Share test product');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      // Test share functionality
      const shareButton = page.getByTestId('share-button');
      if (await shareButton.isVisible()) {
        await shareButton.click();
        
        // Should open share modal or copy to clipboard
        await expect(page.getByTestId('share-modal')).toBeVisible();
        
        // Verify share URL is generated
        const shareUrl = page.getByTestId('share-url');
        await expect(shareUrl).toBeVisible();
        await expect(shareUrl).toContainText('/report/');
      }
    });

    test('export to PDF functionality', async ({ page }) => {
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Export PDF test');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      const exportButton = page.getByTestId('export-pdf-button');
      if (await exportButton.isVisible()) {
        // Set up download handler
        const downloadPromise = page.waitForEvent('download');
        await exportButton.click();
        
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toMatch(/\.pdf$/);
      }
    });

    test('export to JSON functionality', async ({ page }) => {
      await page.goto('/m0-demo');
      await page.getByTestId('product-idea-textarea').fill('Export JSON test');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('success-state')).toBeVisible({ timeout: 30000 });
      
      const exportJsonButton = page.getByTestId('export-json-button');
      if (await exportJsonButton.isVisible()) {
        const downloadPromise = page.waitForEvent('download');
        await exportJsonButton.click();
        
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toMatch(/\.json$/);
      }
    });
  });

  test.describe('Performance Tests', () => {
    test('page load performance', async ({ page }) => {
      const startTime = Date.now();
      await page.goto('/m0-demo');
      
      await expect(page.getByTestId('m0-container')).toBeVisible();
      const loadTime = Date.now() - startTime;
      
      // Page should load within 3 seconds
      expect(loadTime).toBeLessThan(3000);
    });

    test('form responsiveness', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const textarea = page.getByTestId('product-idea-textarea');
      
      // Measure typing responsiveness
      const startTime = Date.now();
      await textarea.type('Performance test input for measuring responsiveness');
      const typingTime = Date.now() - startTime;
      
      // Typing should be responsive (less than 100ms per character on average)
      expect(typingTime / 50).toBeLessThan(100);
    });

    test('processing animation performance', async ({ page }) => {
      await page.goto('/m0-demo');
      
      await page.getByTestId('product-idea-textarea').fill('Animation performance test');
      await page.getByTestId('submit-button').click();
      
      // Check that animations don't cause layout thrashing
      const processingView = page.getByTestId('processing-view');
      await expect(processingView).toBeVisible();
      
      // Verify smooth progress updates
      const progressBar = page.getByTestId('progress-bar');
      await expect(progressBar).toBeVisible();
    });
  });

  test.describe('Edge Cases', () => {
    test('extremely long product descriptions', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const longDescription = 'A'.repeat(500);
      await page.getByTestId('product-idea-textarea').fill(longDescription);
      
      // Should handle max length gracefully
      await expect(page.getByTestId('character-counter')).toContainText('500/500');
      await expect(page.getByTestId('submit-button')).toBeEnabled();
    });

    test('special characters and emoji handling', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const specialText = '🚀 Émojis & spéciål chäractërs! @#$%^&*()_+{}|:"<>?[]\\;\',./ test product';
      await page.getByTestId('product-idea-textarea').fill(specialText);
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('processing-state')).toBeVisible();
      await expect(page.getByTestId('product-idea-display')).toContainText('Émojis & spéciål');
    });

    test('rapid form interactions', async ({ page }) => {
      await page.goto('/m0-demo');
      
      const textarea = page.getByTestId('product-idea-textarea');
      
      // Rapid typing and clearing
      for (let i = 0; i < 5; i++) {
        await textarea.fill(`Test input ${i}`);
        await page.getByTestId('clear-button').click();
      }
      
      // Final input should work normally
      await textarea.fill('Final test input for rapid interactions');
      await expect(page.getByTestId('submit-button')).toBeEnabled();
    });

    test('browser back/forward navigation', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Fill form and submit
      await page.getByTestId('product-idea-textarea').fill('Navigation test product');
      await page.getByTestId('submit-button').click();
      
      // Wait for processing to start
      await expect(page.getByTestId('processing-state')).toBeVisible();
      
      // Navigate away and back
      await page.goto('/');
      await page.goBack();
      
      // Should return to initial state (not processing state)
      await expect(page.getByTestId('input-state')).toBeVisible();
    });

    test('window resize during processing', async ({ page }) => {
      await page.goto('/m0-demo');
      
      await page.getByTestId('product-idea-textarea').fill('Resize test product');
      await page.getByTestId('submit-button').click();
      
      await expect(page.getByTestId('processing-state')).toBeVisible();
      
      // Resize window during processing
      await page.setViewportSize({ width: 600, height: 800 });
      await page.waitForTimeout(1000);
      await page.setViewportSize({ width: 1200, height: 800 });
      
      // Processing should continue normally
      await expect(page.getByTestId('processing-view')).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('keyboard navigation', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Tab through form elements
      await page.keyboard.press('Tab'); // Focus on textarea
      await expect(page.getByTestId('product-idea-textarea')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Focus on clear button (if enabled)
      await page.keyboard.press('Tab'); // Focus on submit button
      await expect(page.getByTestId('submit-button')).toBeFocused();
    });

    test('screen reader compatibility', async ({ page }) => {
      await page.goto('/m0-demo');
      
      // Check for proper ARIA labels
      const textarea = page.getByTestId('product-idea-textarea');
      await expect(textarea).toHaveAttribute('id', 'productIdea');
      
      const label = page.getByTestId('product-idea-label');
      await expect(label).toHaveAttribute('for', 'productIdea');
      
      // Check for error announcements
      await textarea.fill('short');
      await expect(page.getByTestId('product-idea-error')).toHaveAttribute('role', 'alert');
    });

    test('focus management during state transitions', async ({ page }) => {
      await page.goto('/m0-demo');
      
      await page.getByTestId('product-idea-textarea').fill('Focus management test');
      await page.getByTestId('submit-button').click();
      
      // During processing, cancel button should be focusable
      await expect(page.getByTestId('processing-state')).toBeVisible();
      const cancelButton = page.getByTestId('cancel-analysis-button');
      if (await cancelButton.isVisible()) {
        await cancelButton.focus();
        await expect(cancelButton).toBeFocused();
      }
    });
  });
});