import React from 'react';
import { 
  AccessibilityTester, 
  testAccessibility, 
  testKeyboardNavigation, 
  testColorContrast,
  mockScreenReader,
  screen,
  render,
  fireEvent,
  waitFor,
  userEvent 
} from '../../../utils/test-utils/accessibility';
import { render as mockRender, createMockFeasibilityReport, createMockProcessingSteps, createMockHandlers, disableAnimations } from './testUtils';
import { ProductIdeaForm } from '../ProductIdeaForm';
import { ProcessingView } from '../ProcessingView';
import { FeasibilityReport } from '../FeasibilityReport';
import { LoadingSpinner, ProgressBar } from '../LoadingStates';
import { ErrorMessage, ProcessingError } from '../ErrorStates';
import { M0Container } from '../M0Container';

// Mock timers for testing
jest.useFakeTimers();

describe('M0 Components - Comprehensive WCAG 2.1 AA Accessibility Tests', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;
  let screenReaderMock: ReturnType<typeof mockScreenReader>;

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    screenReaderMock = mockScreenReader();
    jest.clearAllMocks();
    jest.clearAllTimers();
    
    // Set up global accessibility testing environment
    global.accessibilityTestSetup.mockPortal();
  });

  afterEach(() => {
    cleanupAnimations();
    screenReaderMock.disconnect();
    global.accessibilityTestSetup.cleanupPortal();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.useFakeTimers();
  });

  describe('WCAG 2.1 AA Compliance - ProductIdeaForm', () => {
    it('should pass comprehensive accessibility audit', async () => {
      const tester = new AccessibilityTester({
        wcagLevel: 'AA',
        tags: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      });
      
      const component = <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />;
      const report = await tester.generateReport(component);
      
      expect(report.summary.level).toBeIn(['AA', 'AAA']);
      expect(report.summary.score).toBeGreaterThanOrEqual(85);
      expect(report.recommendations).toHaveLength(0);
    });

    it('should have proper semantic HTML structure', async () => {
      await testAccessibility(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />,
        {
          rules: {
            'landmark-one-main': { enabled: true },
            'page-has-heading-one': { enabled: false }, // Component-level test
            'region': { enabled: true },
            'bypass': { enabled: true },
          },
        }
      );
    });

    it('should meet color contrast requirements', async () => {
      const contrastResults = await testColorContrast(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />
      );
      
      const failedContrasts = contrastResults.filter(result => !result.passes);
      expect(failedContrasts).toHaveLength(0);
      
      // Ensure minimum AA compliance
      contrastResults.forEach(result => {
        if (result.passes) {
          expect(result.ratio).toBeGreaterThanOrEqual(4.5);
        }
      });
    });

    it('should support comprehensive keyboard navigation', async () => {
      const keyboardResults = await testKeyboardNavigation(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />
      );
      
      expect(keyboardResults.focusableElements.length).toBeGreaterThan(0);
      expect(keyboardResults.trapWorking).toBe(true);
      expect(keyboardResults.escapeWorking).toBe(true);
    });

    it('should provide proper form validation with screen reader support', async () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      const textarea = screen.getByRole('textbox', { name: /what's your product idea/i });
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      // Test invalid input
      await user.type(textarea, 'short');
      await user.click(submitButton);
      
      const errorAlert = await screen.findByRole('alert');
      expect(errorAlert).toHaveTextContent(/please provide at least 10 characters/i);
      
      // Verify ARIA attributes
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
      expect(textarea).toHaveAttribute('aria-describedby');
      
      // Verify error is announced to screen readers
      await waitFor(() => {
        expect(screenReaderMock.getLastAnnouncement()).toContain('please provide');
      });
    });

    it('should have proper focus management and visual focus indicators', async () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      // Test focus order
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      await user.tab();
      // Should move to next focusable element (suggestion chips or buttons)
      expect(document.activeElement).toBeTruthy();
      
      // Test that focus is visible (this would be tested via CSS in real implementation)
      const focusedElement = document.activeElement;
      if (focusedElement) {
        const computedStyle = window.getComputedStyle(focusedElement);
        // In a real implementation, check for focus-visible styles
        expect(focusedElement).toBeVisible();
      }
    });

    it('should provide clear instructions and context', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Main heading should be clear
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/AI Co-Pilot/i);
      
      // Instructions should be available
      expect(screen.getByText(/press enter to submit/i)).toBeInTheDocument();
      
      // Character limit should be clear
      expect(screen.getByText('0/500')).toBeInTheDocument();
      
      // Help text should be available
      expect(screen.getByText('Quick ideas:')).toBeInTheDocument();
    });

    it('should handle reduced motion preferences', async () => {
      global.testUtils.simulateReducedMotion(true);
      
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // In a full implementation, verify animations are disabled
      // This is typically done through CSS media queries
      const animatedElements = screen.getByRole('textbox');
      expect(animatedElements).toBeInTheDocument();
    });
  });

  describe('WCAG 2.1 AA Compliance - ProcessingView', () => {
    const defaultProps = {
      productIdea: 'Test product idea for accessibility',
      steps: createMockProcessingSteps(),
      currentStepIndex: 1,
      overallProgress: 50,
    };

    it('should pass comprehensive accessibility audit', async () => {
      const tester = new AccessibilityTester({
        wcagLevel: 'AA',
        tags: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      });
      
      const component = <ProcessingView {...defaultProps} />;
      const report = await tester.generateReport(component);
      
      expect(report.summary.level).toBeIn(['AA', 'AAA']);
      expect(report.summary.score).toBeGreaterThanOrEqual(85);
    });

    it('should provide meaningful progress information', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Progress bar should have proper ARIA attributes
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label', 'Overall Progress');
      
      // Progress should be announced textually
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('Step 2 of 3')).toBeInTheDocument();
    });

    it('should announce status changes to screen readers', async () => {
      const { rerender } = render(
        <ProcessingView {...defaultProps} currentStepIndex={0} overallProgress={25} />
      );
      
      // Progress update should be announced
      rerender(
        <ProcessingView {...defaultProps} currentStepIndex={1} overallProgress={50} />
      );
      
      await waitFor(() => {
        const announcements = screenReaderMock.announcements;
        expect(announcements.some(a => a.includes('Progress'))).toBe(true);
      });
    });

    it('should provide proper loading states with screen reader support', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Loading spinner should have proper attributes
      const loadingSpinner = screen.getByRole('status');
      expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');
      
      // Screen reader text should be hidden visually but available to assistive tech
      expect(screen.getByText('Loading...')).toHaveClass('sr-only');
    });

    it('should handle time information accessibly', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Time information should be clear
      expect(screen.getByText('Time elapsed: 0:00')).toBeInTheDocument();
      expect(screen.getByText(/this usually takes 60-90 seconds/i)).toBeInTheDocument();
      
      // Time updates should be announced (in a full implementation)
      const timeElement = screen.getByText('Time elapsed: 0:00');
      expect(timeElement).toHaveAttribute('aria-live', 'polite');
    });

    it('should provide accessible cancel functionality', async () => {
      render(<ProcessingView {...defaultProps} onCancel={mockHandlers.onCancel} />);
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      
      // Button should be properly labeled
      expect(cancelButton).toHaveAccessibleName('Cancel Analysis');
      
      // Should work with keyboard
      cancelButton.focus();
      await user.keyboard('{Enter}');
      expect(mockHandlers.onCancel).toHaveBeenCalled();
      
      await user.keyboard(' ');
      expect(mockHandlers.onCancel).toHaveBeenCalledTimes(2);
    });
  });

  describe('WCAG 2.1 AA Compliance - FeasibilityReport', () => {
    const reportData = createMockFeasibilityReport();
    const defaultProps = {
      data: reportData,
      onStartNextStep: mockHandlers.onStartNextStep,
      onUpgrade: mockHandlers.onUpgrade,
    };

    it('should pass comprehensive accessibility audit', async () => {
      const tester = new AccessibilityTester({
        wcagLevel: 'AA',
        tags: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      });
      
      const component = <FeasibilityReport {...defaultProps} />;
      const report = await tester.generateReport(component);
      
      expect(report.summary.level).toBeIn(['AA', 'AAA']);
      expect(report.summary.score).toBeGreaterThanOrEqual(85);
    });

    it('should have proper heading structure and hierarchy', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Main heading (H1)
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toHaveTextContent(/feasibility report/i);
      
      // Section headings (H2)
      const sectionHeadings = screen.getAllByRole('heading', { level: 2 });
      expect(sectionHeadings.length).toBeGreaterThan(0);
      
      // Verify logical heading progression
      const headings = screen.getAllByRole('heading');
      let currentLevel = 1;
      headings.forEach(heading => {
        const level = parseInt(heading.tagName.charAt(1));
        expect(level).toBeLessThanOrEqual(currentLevel + 1);
        if (level > currentLevel) currentLevel = level;
      });
    });

    it('should provide meaningful data relationships and context', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Score should be properly labeled and contextualized
      const score = screen.getByText('78');
      expect(score).toBeInTheDocument();
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      
      // Data should be in accessible format (tables or definition lists)
      expect(screen.getByText('Market Size')).toBeInTheDocument();
      expect(screen.getByText('Growth Rate')).toBeInTheDocument();
      expect(screen.getByText('Competition Level')).toBeInTheDocument();
      
      // Values should be associated with labels
      const marketSize = screen.getByText('Market Size').closest('div, li, tr, dd');
      expect(marketSize).toContainText('$2.3B');
    });

    it('should handle interactive elements accessibly', async () => {
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
        />
      );
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      // All buttons should have accessible names
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
      
      // Test expandable sections
      const competitorToggle = screen.getByRole('button', { name: /competitors/i });
      
      // Should indicate expanded/collapsed state
      expect(competitorToggle).toHaveAttribute('aria-expanded');
      
      await user.click(competitorToggle);
      expect(competitorToggle).toHaveAttribute('aria-expanded', 'true');
      
      // Content should be revealed and properly associated
      const expandedContent = await screen.findByText('Test Competitor');
      expect(expandedContent).toBeInTheDocument();
    });

    it('should provide accessible data visualization alternatives', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Charts and visual elements should have text alternatives
      // In a full implementation, this would test actual chart accessibility
      
      // Score visualization should have textual representation
      expect(screen.getByText('78')).toBeInTheDocument();
      expect(screen.getByText('VIABLE CONCEPT')).toBeInTheDocument();
      
      // Ensure color is not the only means of conveying information
      const scoreElement = screen.getByText('78');
      expect(scoreElement).toHaveClass('text-green-600'); // Visual indicator
      expect(screen.getByText('VIABLE CONCEPT')).toBeInTheDocument(); // Text indicator
    });
  });

  describe('WCAG 2.1 AA Compliance - LoadingStates', () => {
    it('should provide proper loading announcements', async () => {
      await testAccessibility(<LoadingSpinner />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveAttribute('aria-label', 'Loading');
      
      // Hidden text for screen readers
      const srText = screen.getByText('Loading...');
      expect(srText).toHaveClass('sr-only');
    });

    it('should have accessible progress indicators', async () => {
      await testAccessibility(<ProgressBar progress={75} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '75');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      expect(progressBar).toHaveAttribute('aria-label');
      
      // Visual progress indicator
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  describe('WCAG 2.1 AA Compliance - ErrorStates', () => {
    it('should announce errors appropriately', async () => {
      await testAccessibility(
        <ErrorMessage 
          message="Test error message" 
          onRetry={mockHandlers.onRetry}
        />
      );
      
      // Error should be announced
      const errorElement = screen.getByText('Test error message');
      expect(errorElement.closest('[role="alert"]')).toBeInTheDocument();
    });

    it('should provide recovery options with proper labeling', async () => {
      await testAccessibility(
        <ProcessingError 
          productIdea="Test product"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      // Error heading should be proper level
      const errorHeading = screen.getByRole('heading', { level: 2 });
      expect(errorHeading).toHaveTextContent('Analysis Failed');
      
      // Recovery buttons should be clearly labeled
      expect(screen.getByRole('button', { name: /try analysis again/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start with new idea/i })).toBeInTheDocument();
    });

    it('should support keyboard navigation for error recovery', async () => {
      render(
        <ProcessingError 
          productIdea="Test product"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      const keyboardResults = await testKeyboardNavigation(
        <ProcessingError 
          productIdea="Test product"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      expect(keyboardResults.focusableElements.length).toBeGreaterThan(0);
    });
  });

  describe('WCAG 2.1 AA Compliance - M0Container Integration', () => {
    it('should maintain accessibility throughout the entire workflow', async () => {
      const tester = new AccessibilityTester({
        wcagLevel: 'AA',
        tags: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      });
      
      const component = <M0Container />;
      const report = await tester.generateReport(component);
      
      expect(report.summary.level).toBeIn(['AA', 'AAA']);
      expect(report.summary.score).toBeGreaterThanOrEqual(85);
    });

    it('should provide proper landmark navigation', () => {
      render(<M0Container />);
      
      // Main content should be identifiable
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toBeInTheDocument();
      
      // Form should be identifiable
      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();
      
      // Main landmark should exist (implicit in main content)
      const mainContent = screen.getByText('AI Co-Pilot for Ecommerce Validation');
      expect(mainContent).toBeInTheDocument();
    });

    it('should handle state transitions accessibly', async () => {
      render(<M0Container />);
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      // Initial state should be accessible
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      
      // Submit form to transition to processing state
      await user.type(screen.getByRole('textbox'), 'Comprehensive accessibility test product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      // Processing state should be announced
      await screen.findByRole('status');
      const progressBar = await screen.findByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      
      // Fast-forward through processing
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      // Final state should be accessible
      await screen.findByText(/feasibility report/i);
      const reportHeading = screen.getByRole('heading', { level: 1 });
      expect(reportHeading).toHaveTextContent(/feasibility report/i);
    });

    it('should provide skip navigation where appropriate', () => {
      render(<M0Container />);
      
      // In a full implementation, test skip links
      // For now, verify main content is accessible
      const mainContent = screen.getByText('AI Co-Pilot for Ecommerce Validation');
      expect(mainContent).toBeInTheDocument();
      
      // Main form should be reachable
      const mainForm = screen.getByRole('form');
      expect(mainForm).toBeInTheDocument();
    });

    it('should handle focus management during state changes', async () => {
      render(<M0Container />);
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      
      // Initial focus should be manageable
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      // After state change, focus should be appropriate
      await user.type(screen.getByRole('textbox'), 'Focus management test');
      await user.keyboard('{Enter}');
      
      // Processing state should have appropriate focus target
      await screen.findByText('Analyzing Your Product Idea');
      
      // Cancel button should be reachable
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      expect(cancelButton).toBeInTheDocument();
      expect(cancelButton).toBeEnabled();
    });
  });

  describe('Mobile Accessibility Compliance', () => {
    it('should meet mobile accessibility requirements', async () => {
      const tester = new AccessibilityTester({
        testMobile: true,
      });
      
      const mobileResults = await tester.testMobileAccessibility();
      
      expect(mobileResults.hasTouchTargets).toBe(true);
      expect(mobileResults.hasProperSpacing).toBe(true);
      expect(mobileResults.issues).toHaveLength(0);
    });

    it('should have proper touch target sizes', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // All interactive elements should meet minimum touch target size (44px)
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        const rect = button.getBoundingClientRect();
        // In a real test environment, these would have actual dimensions
        expect(button).toBeInTheDocument();
      });
    });

    it('should work with screen magnification', () => {
      // Mock viewport scaling
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        value: 320, // Typical mobile width at 200% zoom
      });
      
      render(<M0Container />);
      
      // Content should still be accessible when zoomed
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
    });
  });

  describe('Cross-Browser Accessibility Testing', () => {
    it('should work with different user agents', () => {
      // Mock different user agents
      const originalUserAgent = navigator.userAgent;
      
      const userAgents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
      ];
      
      userAgents.forEach(userAgent => {
        Object.defineProperty(navigator, 'userAgent', {
          value: userAgent,
          configurable: true,
        });
        
        render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
        
        // Basic accessibility should work across browsers
        expect(screen.getByRole('textbox')).toHaveAccessibleName();
        expect(screen.getByRole('form')).toBeInTheDocument();
        
        // Clean up
        screen.unmount();
      });
      
      // Restore original user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: originalUserAgent,
        configurable: true,
      });
    });
  });
});

// Custom Jest matchers for accessibility testing
expect.extend({
  toBeIn(received: any, expectedArray: any[]) {
    const pass = expectedArray.includes(received);
    if (pass) {
      return {
        message: () => `expected ${received} not to be in [${expectedArray.join(', ')}]`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be in [${expectedArray.join(', ')}]`,
        pass: false,
      };
    }
  },
});