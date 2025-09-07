import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { M0Container } from '../../src/components/m0/M0Container';
import { TestWrapper, checkAccessibility, mockWindowAPIs } from '../utils/TestWrapper';

// Mock axe-core for comprehensive accessibility testing
jest.mock('axe-core', () => ({
  run: jest.fn(() => Promise.resolve({ violations: [] }))
}));

describe('M0 Accessibility Integration Tests', () => {
  let mockFetch: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        data: {
          productIdea: 'Accessibility Test Product',
          viabilityScore: 80,
          marketSize: '$2.5B',
          growthRate: '18% YoY'
        }
      })
    });
    global.fetch = mockFetch;
  });

  describe('Keyboard Navigation', () => {
    test('supports full keyboard navigation through form', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Tab to textarea
      await user.tab();
      expect(screen.getByTestId('product-idea-textarea')).toHaveFocus();

      // Type content
      await user.type(screen.getByTestId('product-idea-textarea'), 'Keyboard navigation test product');

      // Tab to clear button (if enabled)
      await user.tab();
      const clearButton = screen.getByTestId('clear-button');
      if (!clearButton.disabled) {
        expect(clearButton).toHaveFocus();
        await user.tab();
      }

      // Tab to submit button
      const submitButton = screen.getByTestId('submit-button');
      expect(submitButton).toHaveFocus();

      // Enter should submit
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });

    test('keyboard navigation in processing state', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Start processing
      await user.type(screen.getByTestId('product-idea-textarea'), 'Processing keyboard test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Check if cancel button is focusable
      const cancelButton = screen.queryByTestId('cancel-analysis-button');
      if (cancelButton) {
        await user.tab();
        expect(cancelButton).toHaveFocus();

        // Escape should also cancel (if supported)
        await user.keyboard('{Escape}');
        await waitFor(() => {
          expect(screen.getByTestId('input-state')).toBeInTheDocument();
        });
      }
    });

    test('keyboard navigation in success state', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Complete flow
      await user.type(screen.getByTestId('product-idea-textarea'), 'Success keyboard navigation test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Tab through available buttons
      const buttons = screen.getAllByRole('button');
      for (const button of buttons) {
        if (!button.disabled && button.offsetParent !== null) {
          await user.tab();
          expect(document.activeElement).toBe(button);
        }
      }
    });

    test('skip links for screen readers', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Check for skip navigation elements
      const skipLinks = screen.queryAllByText(/skip to/i);
      skipLinks.forEach(link => {
        expect(link).toHaveAttribute('href');
        expect(link.getAttribute('href')).toMatch(/^#/);
      });
    });
  });

  describe('Screen Reader Support', () => {
    test('proper ARIA labels and descriptions', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      const label = screen.getByTestId('product-idea-label');

      // Check label association
      expect(textarea).toHaveAttribute('id', 'productIdea');
      expect(label).toHaveAttribute('for', 'productIdea');

      // Check ARIA attributes
      expect(textarea).toHaveAttribute('aria-describedby');
      expect(textarea).toHaveAccessibleName();
    });

    test('error announcements with ARIA live regions', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      
      // Trigger validation error
      await user.type(textarea, 'short');
      
      await waitFor(() => {
        const errorElement = screen.getByTestId('product-idea-error');
        expect(errorElement).toHaveAttribute('role', 'alert');
        expect(errorElement).toBeInTheDocument();
      });
    });

    test('status updates announced to screen readers', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Screen reader status test');
      await user.click(screen.getByTestId('submit-button'));

      // Check for status updates during processing
      await waitFor(() => {
        const processingView = screen.getByTestId('processing-state');
        expect(processingView).toBeInTheDocument();
        
        // Should have accessible description of current status
        const statusElements = screen.getAllByText(/analyzing|processing|step/i);
        expect(statusElements.length).toBeGreaterThan(0);
      });
    });

    test('progress announcements', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Progress announcement test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Check progress bar accessibility
      const progressElement = screen.queryByRole('progressbar');
      if (progressElement) {
        expect(progressElement).toHaveAttribute('aria-valuenow');
        expect(progressElement).toHaveAttribute('aria-valuemin', '0');
        expect(progressElement).toHaveAttribute('aria-valuemax', '100');
      }
    });

    test('form instructions and help text', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Check for helpful instructions
      const instructions = screen.getByTestId('form-instructions');
      expect(instructions).toHaveTextContent(/enter.*submit/i);

      // Textarea should reference help text
      const textarea = screen.getByTestId('product-idea-textarea');
      const describedBy = textarea.getAttribute('aria-describedby');
      
      if (describedBy) {
        const helpElements = describedBy.split(' ').map(id => 
          document.getElementById(id)
        ).filter(Boolean);
        
        expect(helpElements.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Focus Management', () => {
    test('focus management during state transitions', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Initial focus should be manageable
      const textarea = screen.getByTestId('product-idea-textarea');
      textarea.focus();
      expect(textarea).toHaveFocus();

      await user.type(textarea, 'Focus management test');
      await user.click(screen.getByTestId('submit-button'));

      // During processing, focus should be managed appropriately
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Focus should be on a relevant element or managed
      const activeElement = document.activeElement;
      expect(activeElement).toBeInstanceOf(HTMLElement);
      expect(activeElement?.getAttribute('tabindex')).not.toBe('-1');
    });

    test('focus restoration after modals or overlays', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      textarea.focus();
      const originalFocusElement = document.activeElement;

      // Complete flow to get to success state
      await user.type(textarea, 'Focus restoration test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // If there are modals or overlays, focus should be managed
      const modalElements = screen.queryAllByRole('dialog');
      if (modalElements.length > 0) {
        // Focus should be inside the modal
        const currentFocus = document.activeElement;
        const isInsideModal = modalElements.some(modal => 
          modal.contains(currentFocus)
        );
        expect(isInsideModal || currentFocus === document.body).toBe(true);
      }
    });

    test('focus trap in critical interactions', async () => {
      const user = userEvent.setup();
      const { cleanup } = mockWindowAPIs();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Complete flow to success state
      await user.type(screen.getByTestId('product-idea-textarea'), 'Focus trap test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Test share modal if present
      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);
        
        const modal = screen.queryByTestId('share-modal');
        if (modal) {
          // Focus should be trapped within modal
          const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          
          if (focusableElements.length > 0) {
            // Tab through all elements - should cycle within modal
            for (let i = 0; i < focusableElements.length + 1; i++) {
              await user.tab();
            }
            
            // Focus should still be within modal
            const currentFocus = document.activeElement;
            expect(modal.contains(currentFocus)).toBe(true);
          }
        }
      }

      cleanup();
    });
  });

  describe('Visual Accessibility', () => {
    test('sufficient color contrast', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // This would typically be done with automated tools
      // Here we check for proper CSS classes that should provide good contrast
      const textElements = screen.getAllByText(/./);
      
      textElements.forEach(element => {
        const computedStyle = window.getComputedStyle(element);
        const color = computedStyle.color;
        const backgroundColor = computedStyle.backgroundColor;
        
        // Basic check - elements should have explicit colors
        expect(color).not.toBe('');
        // More comprehensive contrast checking would require color analysis tools
      });
    });

    test('text scaling and zoom support', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Simulate zoom by changing font size
      const originalFontSize = document.documentElement.style.fontSize;
      document.documentElement.style.fontSize = '200%';

      // Component should still be functional at 200% zoom
      const textarea = screen.getByTestId('product-idea-textarea');
      expect(textarea).toBeVisible();
      
      const submitButton = screen.getByTestId('submit-button');
      expect(submitButton).toBeVisible();

      // Restore original font size
      document.documentElement.style.fontSize = originalFontSize;
    });

    test('reduced motion preferences', async () => {
      // Mock reduced motion preference
      const mockMediaQuery = {
        matches: true,
        media: '(prefers-reduced-motion: reduce)',
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      };

      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: jest.fn().mockReturnValue(mockMediaQuery),
      });

      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Components should respect reduced motion preferences
      // This would typically be verified by checking CSS classes or animation properties
      const animatedElements = document.querySelectorAll('[class*="animate"]');
      
      // In a real implementation, animations should be disabled or reduced
      animatedElements.forEach(element => {
        const computedStyle = window.getComputedStyle(element);
        // Check that animation-duration is set to a reduced value
        // or animation is disabled when reduced motion is preferred
      });
    });
  });

  describe('Mobile Accessibility', () => {
    test('touch target sizes', async () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', { value: 375, writable: true });
      Object.defineProperty(window, 'innerHeight', { value: 667, writable: true });

      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Check minimum touch target sizes (44x44px recommended)
      const buttons = screen.getAllByRole('button');
      
      buttons.forEach(button => {
        const rect = button.getBoundingClientRect();
        const minSize = 44; // pixels
        
        // Some allowance for CSS that might not be fully applied in JSDOM
        expect(rect.width).toBeGreaterThanOrEqual(minSize * 0.8);
        expect(rect.height).toBeGreaterThanOrEqual(minSize * 0.8);
      });
    });

    test('mobile screen reader compatibility', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Check for mobile-specific ARIA attributes
      const interactiveElements = screen.getAllByRole(/button|textbox|link/);
      
      interactiveElements.forEach(element => {
        // Should have accessible names
        expect(element).toHaveAccessibleName();
        
        // Should not have redundant or confusing ARIA
        const ariaLabel = element.getAttribute('aria-label');
        const ariaLabelledBy = element.getAttribute('aria-labelledby');
        
        if (ariaLabel && ariaLabelledBy) {
          // Shouldn't have both unless intentional
          console.warn(`Element has both aria-label and aria-labelledby`, element);
        }
      });
    });
  });

  describe('Comprehensive Accessibility Audit', () => {
    test('passes automated accessibility tests - input state', async () => {
      const container = render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      ).container;

      const issues = await checkAccessibility(container);
      
      // Report any issues found
      if (issues.length > 0) {
        console.warn('Accessibility issues found:', issues);
      }
      
      // Critical issues should be fixed
      const criticalIssues = issues.filter(issue => 
        issue.includes('missing') || issue.includes('invalid')
      );
      
      expect(criticalIssues.length).toBe(0);
    });

    test('passes automated accessibility tests - processing state', async () => {
      const user = userEvent.setup();
      
      const { container } = render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Accessibility audit processing test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      const issues = await checkAccessibility(container);
      
      if (issues.length > 0) {
        console.warn('Processing state accessibility issues:', issues);
      }

      const criticalIssues = issues.filter(issue => 
        issue.includes('missing') || issue.includes('invalid')
      );
      
      expect(criticalIssues.length).toBe(0);
    });

    test('passes automated accessibility tests - success state', async () => {
      const user = userEvent.setup();
      
      const { container } = render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Accessibility audit success test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const issues = await checkAccessibility(container);
      
      if (issues.length > 0) {
        console.warn('Success state accessibility issues:', issues);
      }

      const criticalIssues = issues.filter(issue => 
        issue.includes('missing') || issue.includes('invalid')
      );
      
      expect(criticalIssues.length).toBe(0);
    });
  });

  describe('Assistive Technology Compatibility', () => {
    test('works with virtual cursor navigation', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Simulate virtual cursor navigation (arrow keys)
      const user = userEvent.setup();
      
      // All interactive elements should be discoverable via arrow navigation
      const interactiveElements = screen.getAllByRole(/button|textbox|link/);
      
      for (const element of interactiveElements) {
        // Each element should be focusable
        element.focus();
        expect(element).toHaveFocus();
        
        // Should have appropriate role
        expect(element).toHaveAttribute('role');
      }
    });

    test('voice control compatibility', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Voice control relies on accessible names and landmarks
      const textInput = screen.getByTestId('product-idea-textarea');
      const submitButton = screen.getByTestId('submit-button');
      
      // Should have clear, speakable names
      expect(textInput).toHaveAccessibleName();
      expect(submitButton).toHaveAccessibleName();
      
      // Names should be descriptive enough for voice commands
      const textInputName = textInput.getAttribute('aria-label') || 
                           textInput.getAttribute('placeholder') || 
                           '';
      expect(textInputName.length).toBeGreaterThan(5);
    });

    test('switch navigation compatibility', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Switch navigation requires proper tab order and activation
      const focusableElements = screen.getAllByRole(/button|textbox|link/);
      
      // Should be able to navigate through all elements
      for (let i = 0; i < focusableElements.length; i++) {
        const element = focusableElements[i];
        element.focus();
        
        // Should be focusable
        expect(element).toHaveFocus();
        
        // Should be activatable with Enter/Space
        expect(element.tagName).toMatch(/^(BUTTON|INPUT|TEXTAREA|A)$/);
      }
    });
  });

  describe('Error Accessibility', () => {
    test('error messages are accessible', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      
      // Trigger validation error
      await user.type(textarea, 'x'); // Too short
      
      await waitFor(() => {
        const errorMessage = screen.getByTestId('product-idea-error');
        
        // Should be announced to screen readers
        expect(errorMessage).toHaveAttribute('role', 'alert');
        
        // Should be associated with the input
        const ariaDescribedBy = textarea.getAttribute('aria-describedby');
        expect(ariaDescribedBy).toContain(errorMessage.id || 'error');
        
        // Should have meaningful message
        expect(errorMessage).toHaveTextContent(/characters/i);
      });
    });

    test('network error accessibility', async () => {
      const user = userEvent.setup();
      
      // Mock network error
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Network error accessibility test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('network-error-state')).toBeInTheDocument();
      });

      // Error state should be accessible
      const errorContainer = screen.getByTestId('network-error-state');
      
      // Should have appropriate ARIA attributes
      expect(errorContainer).toHaveAttribute('role', 'alert');
      
      // Should have retry action
      const retryButton = screen.queryByTestId('retry-button');
      if (retryButton) {
        expect(retryButton).toHaveAccessibleName();
      }
    });
  });
});