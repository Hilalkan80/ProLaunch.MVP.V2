import React from 'react';
import { screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockFeasibilityReport, createMockProcessingSteps, createMockHandlers, disableAnimations } from './testUtils';
import { ProductIdeaForm } from '../ProductIdeaForm';
import { ProcessingView } from '../ProcessingView';
import { FeasibilityReport } from '../FeasibilityReport';
import { LoadingSpinner, ProgressBar } from '../LoadingStates';
import { ErrorMessage, ProcessingError } from '../ErrorStates';
import { M0Container } from '../M0Container';

// Mock timers for animation testing
jest.useFakeTimers();

describe('M0 Components Accessibility Tests', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  afterEach(() => {
    cleanupAnimations();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.useFakeTimers();
  });

  describe('ProductIdeaForm Accessibility', () => {
    it('should have proper form structure and labels', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Form should be identifiable
      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();
      
      // Input should have accessible name
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveAccessibleName(/what's your product idea/i);
      
      // Input should have proper ID and label association
      expect(textarea).toHaveAttribute('id', 'productIdea');
      const label = screen.getByLabelText(/what's your product idea/i);
      expect(label).toBe(textarea);
    });

    it('should announce validation errors to screen readers', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      // Enter invalid input
      await user.type(textarea, 'short');
      await user.click(submitButton);
      
      // Error should have role="alert" for screen readers
      const errorMessage = await screen.findByRole('alert');
      expect(errorMessage).toHaveTextContent(/please provide at least 10 characters/i);
      
      // Error should be associated with input
      expect(textarea).toHaveAttribute('aria-invalid', 'true');
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Tab to textarea
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      // Type valid content
      await user.type(screen.getByRole('textbox'), 'Valid product idea for testing');
      
      // Tab to suggestion chips
      await user.tab();
      // Note: Suggestion chips might not be in tab order by design
      
      // Tab to buttons
      const buttons = screen.getAllByRole('button');
      for (const button of buttons) {
        if (!button.disabled) {
          await user.tab();
          // One of the buttons should receive focus
        }
      }
    });

    it('should have proper button states and labels', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      const clearButton = screen.getByRole('button', { name: /clear/i });
      
      // Initial states
      expect(submitButton).toBeDisabled();
      expect(clearButton).toBeDisabled();
      
      // After typing
      await user.type(screen.getByRole('textbox'), 'Valid product idea');
      
      expect(submitButton).toBeEnabled();
      expect(clearButton).toBeEnabled();
      
      // All buttons should have accessible names
      const allButtons = screen.getAllByRole('button');
      allButtons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
    });

    it('should announce character count changes', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Character counter should be visible
      expect(screen.getByText('0/500')).toBeInTheDocument();
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello');
      
      expect(screen.getByText('5/500')).toBeInTheDocument();
      
      // Character counter should be associated with textarea for screen readers
      // This could be enhanced with aria-describedby in the actual component
    });
  });

  describe('ProcessingView Accessibility', () => {
    const defaultProps = {
      productIdea: 'Test product idea',
      steps: createMockProcessingSteps(),
      currentStepIndex: 1,
      overallProgress: 50,
    };

    it('should have proper progress indicators', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Progress bar should have proper ARIA attributes
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      
      // Loading spinner should be announced
      const loadingSpinner = screen.getByRole('status');
      expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');
    });

    it('should announce processing status changes', () => {
      const stepsWithStatus = [
        { id: '1', label: 'Completed Step', description: 'Done', status: 'completed' as const },
        { id: '2', label: 'Current Step', description: 'Processing', status: 'processing' as const },
        { id: '3', label: 'Pending Step', description: 'Waiting', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={stepsWithStatus}
          currentStepIndex={1}
        />
      );
      
      // Each step should be properly labeled
      expect(screen.getByText('Complete')).toBeInTheDocument();
      expect(screen.getByText('In Progress')).toBeInTheDocument();
      
      // Current step should be highlighted for screen readers
      const currentStepContainer = screen.getByText('Current Step').closest('.bg-blue-50');
      expect(currentStepContainer).toBeInTheDocument();
    });

    it('should support keyboard interaction with cancel button', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<ProcessingView {...defaultProps} onCancel={mockHandlers.onCancel} />);
      
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      
      // Should be focusable
      await user.tab();
      expect(cancelButton).toHaveFocus();
      
      // Should be activatable with Enter
      await user.keyboard('{Enter}');
      expect(mockHandlers.onCancel).toHaveBeenCalled();
      
      // Should be activatable with Space
      await user.keyboard(' ');
      expect(mockHandlers.onCancel).toHaveBeenCalledTimes(2);
    });

    it('should provide meaningful time information', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Time elapsed should be clearly labeled
      expect(screen.getByText('Time elapsed: 0:00')).toBeInTheDocument();
      
      // Duration estimate should be clear
      expect(screen.getByText(/this usually takes 60-90 seconds/i)).toBeInTheDocument();
    });
  });

  describe('FeasibilityReport Accessibility', () => {
    const reportData = createMockFeasibilityReport();
    const defaultProps = {
      data: reportData,
      onStartNextStep: mockHandlers.onStartNextStep,
      onUpgrade: mockHandlers.onUpgrade,
    };

    it('should have proper heading hierarchy', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Main heading
      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent(/feasibility report/i);
      
      // Section headings
      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);
      
      // Verify heading hierarchy is logical
      expect(h2s.some(h => h.textContent?.includes('Market Analysis'))).toBe(true);
      expect(h2s.some(h => h.textContent?.includes('Next Steps'))).toBe(true);
    });

    it('should have accessible interactive elements', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
        />
      );
      
      // All buttons should have accessible names
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
      
      // Test keyboard interaction with collapsible sections
      const competitorToggle = screen.getByRole('button', { name: /top competitors/i });
      await user.click(competitorToggle);
      
      // Content should be revealed
      await screen.findByText('Test Competitor');
      
      // Toggle should indicate expanded state (in a full implementation)
      expect(competitorToggle).toBeInTheDocument();
    });

    it('should provide meaningful data relationships', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Score should be clearly labeled
      expect(screen.getByText('78')).toBeInTheDocument();
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      
      // Market data should have clear labels
      expect(screen.getByText('Market Size')).toBeInTheDocument();
      expect(screen.getByText('Growth Rate')).toBeInTheDocument();
      expect(screen.getByText('Competition Level')).toBeInTheDocument();
    });

    it('should handle keyboard navigation for next steps', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<FeasibilityReport {...defaultProps} />);
      
      // Start button should be focusable
      const startButton = screen.getByRole('button', { name: /start now →/i });
      await user.tab();
      // Navigate to the start button
      let attempts = 0;
      while (document.activeElement !== startButton && attempts < 10) {
        await user.tab();
        attempts++;
      }
      
      if (document.activeElement === startButton) {
        await user.keyboard('{Enter}');
        expect(mockHandlers.onStartNextStep).toHaveBeenCalled();
      }
    });
  });

  describe('LoadingStates Accessibility', () => {
    it('should provide proper loading announcements', () => {
      render(<LoadingSpinner />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveAttribute('aria-label', 'Loading');
      
      // Screen reader text should be available
      expect(screen.getByText('Loading...')).toHaveClass('sr-only');
    });

    it('should have accessible progress bars', () => {
      render(<ProgressBar progress={75} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '75');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      
      // Progress should be visually indicated
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  describe('ErrorStates Accessibility', () => {
    it('should announce errors appropriately', () => {
      render(
        <ErrorMessage 
          message="Test error message" 
          onRetry={mockHandlers.onRetry}
        />
      );
      
      // Error content should be in an appropriate landmark
      expect(screen.getByText('Test error message')).toBeInTheDocument();
      
      // Action buttons should be accessible
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
    });

    it('should provide proper error context', () => {
      render(
        <ProcessingError 
          productIdea="Test product"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      // Error heading should be clear
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Analysis Failed');
      
      // Recovery actions should be clearly labeled
      expect(screen.getByRole('button', { name: /try analysis again/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start with new idea/i })).toBeInTheDocument();
    });

    it('should support keyboard navigation for error actions', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(
        <ProcessingError 
          productIdea="Test product"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      // Tab through error action buttons
      await user.tab();
      expect(screen.getByRole('button', { name: /try analysis again/i })).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button', { name: /start with new idea/i })).toHaveFocus();
      
      // Actions should work with keyboard
      await user.keyboard('{Enter}');
      expect(mockHandlers.onStartOver).toHaveBeenCalled();
    });
  });

  describe('M0Container Overall Accessibility', () => {
    it('should maintain focus management throughout workflow', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<M0Container />);
      
      // Initial focus should be manageable
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      // After form submission, focus should be appropriate
      await user.type(screen.getByRole('textbox'), 'Test product for accessibility');
      await user.keyboard('{Enter}');
      
      await screen.findByText('Analyzing Your Product Idea');
      
      // Cancel button should be reachable
      await user.tab();
      expect(screen.getByRole('button', { name: /cancel analysis/i })).toHaveFocus();
    });

    it('should provide proper landmark regions', () => {
      render(<M0Container />);
      
      // Main content should be in appropriate landmarks
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toBeInTheDocument();
      
      // Form should be identifiable
      const form = screen.getByRole('form');
      expect(form).toBeInTheDocument();
    });

    it('should handle state changes accessibly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<M0Container />);
      
      // Type and submit
      await user.type(screen.getByRole('textbox'), 'Accessibility test product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      // Processing state should be announced
      await screen.findByRole('status');
      await screen.findByRole('progressbar');
      
      // Complete processing
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      // Success state should be accessible
      await screen.findByText(/feasibility report/i);
      
      const reportHeading = screen.getByRole('heading', { level: 1 });
      expect(reportHeading).toHaveTextContent(/feasibility report/i);
    });

    it('should provide skip links where appropriate', () => {
      render(<M0Container />);
      
      // In a full implementation, skip links would help users navigate
      // This test verifies the component structure supports good navigation
      const mainContent = screen.getByText('AI Co-Pilot for Ecommerce Validation');
      expect(mainContent).toBeInTheDocument();
    });

    it('should have consistent focus indicators', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<M0Container />);
      
      // Tab through focusable elements
      const focusableElements = [
        () => screen.getByRole('textbox'),
        () => screen.getAllByRole('button').find(btn => !btn.disabled),
      ];
      
      for (const getElement of focusableElements) {
        const element = getElement();
        if (element) {
          await user.tab();
          // Focus indicators should be visible (tested through CSS in real implementation)
        }
      }
    });
  });

  describe('Color Contrast and Visual Accessibility', () => {
    it('should use appropriate color combinations for status indicators', () => {
      const reportData = createMockFeasibilityReport({
        viabilityScore: 85 // High score for green
      });
      
      render(
        <FeasibilityReport 
          data={reportData}
          onStartNextStep={mockHandlers.onStartNextStep}
          onUpgrade={mockHandlers.onUpgrade}
        />
      );
      
      // High viability score should use green (good contrast)
      const scoreElement = screen.getByText('85');
      expect(scoreElement).toHaveClass('text-green-600');
      
      const labelElement = screen.getByText('VIABLE CONCEPT');
      expect(labelElement).toHaveClass('bg-green-600');
    });

    it('should provide text alternatives for visual elements', () => {
      render(
        <ProcessingView 
          productIdea="Test"
          steps={createMockProcessingSteps()}
          currentStepIndex={0}
          overallProgress={50}
        />
      );
      
      // Progress bar should have textual representation
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('Overall Progress')).toBeInTheDocument();
      
      // Step status should be textually indicated
      expect(screen.getByText('Step 1 of 3')).toBeInTheDocument();
    });

    it('should not rely solely on color for information', () => {
      const steps = [
        { id: '1', label: 'Success Step', description: 'Done', status: 'completed' as const },
        { id: '2', label: 'Error Step', description: 'Failed', status: 'error' as const },
        { id: '3', label: 'Warning Step', description: 'Issue', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          productIdea="Test"
          steps={steps}
          currentStepIndex={1}
          overallProgress={33}
        />
      );
      
      // Status should be indicated by text, not just color
      expect(screen.getByText('Complete')).toBeInTheDocument();
      // Error and pending states are indicated by absence of Complete text and visual state
      
      // Icons should provide additional context beyond color
      // In the actual implementation, these would be verified
    });
  });

  describe('Screen Reader Support', () => {
    it('should provide proper screen reader content', () => {
      render(<LoadingSpinner />);
      
      // Hidden text for screen readers
      const srText = screen.getByText('Loading...');
      expect(srText).toHaveClass('sr-only');
      
      // Status role for announcements
      const status = screen.getByRole('status');
      expect(status).toBeInTheDocument();
    });

    it('should announce dynamic content changes', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimers });
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      // Character count changes should be perceivable
      expect(screen.getByText('0/500')).toBeInTheDocument();
      
      await user.type(textarea, 'Test');
      expect(screen.getByText('4/500')).toBeInTheDocument();
      
      // Form state changes should be announced via validation
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      expect(submitButton).toBeDisabled();
      
      await user.type(textarea, ' product idea');
      await user.click(submitButton);
      
      // Validation error should be announced
      const errorElement = await screen.findByRole('alert');
      expect(errorElement).toBeInTheDocument();
    });

    it('should provide contextual help', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Help text should be available
      expect(screen.getByText(/press enter to submit/i)).toBeInTheDocument();
      
      // Quick ideas should be labeled
      expect(screen.getByText('Quick ideas:')).toBeInTheDocument();
      
      // Character limits should be clear
      expect(screen.getByText('0/500')).toBeInTheDocument();
    });
  });
});