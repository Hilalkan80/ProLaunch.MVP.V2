import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockProcessingSteps, createMockHandlers, disableAnimations } from './testUtils';
import { ProcessingView } from '../ProcessingView';

// Mock the timer functions
jest.useFakeTimers();

describe('ProcessingView', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  const defaultProps = {
    productIdea: 'Organic dog treats for health-conscious pet owners',
    steps: createMockProcessingSteps(),
    currentStepIndex: 0,
    overallProgress: 30,
  };

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

  describe('Rendering', () => {
    it('should render with default props', () => {
      render(<ProcessingView {...defaultProps} />);
      
      expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      expect(screen.getByText('"Organic dog treats for health-conscious pet owners"')).toBeInTheDocument();
      expect(screen.getByText('Overall Progress')).toBeInTheDocument();
      expect(screen.getByText('Step 1 of 3')).toBeInTheDocument();
    });

    it('should truncate long product ideas', () => {
      const longIdea = 'A'.repeat(100);
      render(
        <ProcessingView 
          {...defaultProps} 
          productIdea={longIdea} 
        />
      );
      
      const truncatedText = screen.getByText(`"${'A'.repeat(60)}..."`);
      expect(truncatedText).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      const customClass = 'custom-processing-class';
      render(
        <ProcessingView 
          {...defaultProps} 
          className={customClass} 
        />
      );
      
      const container = screen.getByText('Analyzing Your Product Idea').closest('.custom-processing-class');
      expect(container).toBeInTheDocument();
    });

    it('should display all processing steps', () => {
      const steps = [
        { id: '1', label: 'Step One', description: 'First step desc', status: 'completed' as const },
        { id: '2', label: 'Step Two', description: 'Second step desc', status: 'processing' as const },
        { id: '3', label: 'Step Three', description: 'Third step desc', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={1}
        />
      );
      
      expect(screen.getByText('Step One')).toBeInTheDocument();
      expect(screen.getByText('Step Two')).toBeInTheDocument();
      expect(screen.getByText('Step Three')).toBeInTheDocument();
    });
  });

  describe('Timer Functionality', () => {
    it('should display elapsed time and update every second', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Initially shows 0:00
      expect(screen.getByText('Time elapsed: 0:00')).toBeInTheDocument();
      
      // After 1 second
      act(() => {
        jest.advanceTimersByTime(1000);
      });
      expect(screen.getByText('Time elapsed: 0:01')).toBeInTheDocument();
      
      // After 65 seconds (1:05)
      act(() => {
        jest.advanceTimersByTime(64000);
      });
      expect(screen.getByText('Time elapsed: 1:05')).toBeInTheDocument();
    });

    it('should format time correctly for different durations', () => {
      render(<ProcessingView {...defaultProps} />);
      
      // Test various time formats
      const testCases = [
        { seconds: 0, expected: '0:00' },
        { seconds: 1, expected: '0:01' },
        { seconds: 59, expected: '0:59' },
        { seconds: 60, expected: '1:00' },
        { seconds: 61, expected: '1:01' },
        { seconds: 3661, expected: '61:01' }, // Over an hour
      ];
      
      testCases.forEach(({ seconds, expected }) => {
        act(() => {
          jest.advanceTimersByTime(seconds * 1000);
        });
        expect(screen.getByText(`Time elapsed: ${expected}`)).toBeInTheDocument();
      });
    });

    it('should clean up timer on unmount', () => {
      const { unmount } = render(<ProcessingView {...defaultProps} />);
      
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      unmount();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe('Progress Display', () => {
    it('should show overall progress percentage', () => {
      render(<ProcessingView {...defaultProps} overallProgress={75} />);
      
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('should show correct step counter', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          currentStepIndex={2}
          steps={createMockProcessingSteps(5)}
        />
      );
      
      expect(screen.getByText('Step 3 of 5')).toBeInTheDocument();
    });

    it('should handle step index bounds correctly', () => {
      const steps = createMockProcessingSteps(3);
      
      // Test with index beyond steps length
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={5}
        />
      );
      
      expect(screen.getByText('Step 3 of 3')).toBeInTheDocument();
    });
  });

  describe('Step Status Display', () => {
    it('should display completed steps with checkmark', () => {
      const steps = [
        { id: '1', label: 'Completed Step', description: 'Done', status: 'completed' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      const checkIcon = screen.getByRole('img', { hidden: true }); // SVG icons are often hidden from screen readers
      expect(checkIcon).toBeInTheDocument();
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });

    it('should display processing steps with spinner', () => {
      const steps = [
        { id: '1', label: 'Processing Step', description: 'In progress', status: 'processing' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      expect(screen.getByRole('status')).toBeInTheDocument(); // LoadingSpinner has role="status"
      expect(screen.getByText('In Progress')).toBeInTheDocument();
    });

    it('should display error steps with error icon', () => {
      const steps = [
        { id: '1', label: 'Failed Step', description: 'Error occurred', status: 'error' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      // Error state should have appropriate styling
      expect(screen.getByText('Failed Step')).toHaveClass('text-red-800');
    });

    it('should display pending steps with step number', () => {
      const steps = [
        { id: '1', label: 'Pending Step', description: 'Waiting', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      expect(screen.getByText('1')).toBeInTheDocument(); // Step number in circle
    });
  });

  describe('Current Step Highlight', () => {
    it('should highlight current step', () => {
      const steps = [
        { id: '1', label: 'Current Step', description: 'Now processing', status: 'processing' as const, duration: 30 },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      const highlightedSection = screen.getByText('Current Step').closest('.bg-blue-50');
      expect(highlightedSection).toBeInTheDocument();
      expect(screen.getByText('Estimated time: ~30 seconds')).toBeInTheDocument();
    });

    it('should show estimated time for processing step with duration', () => {
      const steps = [
        { id: '1', label: 'Timed Step', description: 'With duration', status: 'processing' as const, duration: 45 },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      expect(screen.getByText('Estimated time: ~45 seconds')).toBeInTheDocument();
    });

    it('should not show estimated time for non-processing steps', () => {
      const steps = [
        { id: '1', label: 'Completed Step', description: 'Done', status: 'completed' as const, duration: 45 },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      expect(screen.queryByText('Estimated time:')).not.toBeInTheDocument();
    });
  });

  describe('Cancel Functionality', () => {
    it('should render cancel button when onCancel is provided', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          onCancel={mockHandlers.onCancel}
        />
      );
      
      expect(screen.getByRole('button', { name: /cancel analysis/i })).toBeInTheDocument();
    });

    it('should not render cancel button when onCancel is not provided', () => {
      render(<ProcessingView {...defaultProps} />);
      
      expect(screen.queryByRole('button', { name: /cancel analysis/i })).not.toBeInTheDocument();
    });

    it('should call onCancel when cancel button is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <ProcessingView 
          {...defaultProps} 
          onCancel={mockHandlers.onCancel}
        />
      );
      
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      await user.click(cancelButton);
      
      expect(mockHandlers.onCancel).toHaveBeenCalledTimes(1);
    });
  });

  describe('Step Visual States', () => {
    it('should apply correct background colors for different step states', () => {
      const steps = [
        { id: '1', label: 'Completed', description: 'Done', status: 'completed' as const },
        { id: '2', label: 'Processing', description: 'Current', status: 'processing' as const },
        { id: '3', label: 'Pending', description: 'Waiting', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={1}
        />
      );
      
      // Completed step should have green background
      const completedStep = screen.getByText('Completed').closest('.bg-green-50');
      expect(completedStep).toBeInTheDocument();
      
      // Current step should have blue background
      const currentStep = screen.getByText('Processing').closest('.bg-blue-50');
      expect(currentStep).toBeInTheDocument();
      
      // Pending step should have gray background
      const pendingStep = screen.getByText('Pending').closest('.bg-gray-50');
      expect(pendingStep).toBeInTheDocument();
    });

    it('should apply correct text colors for different step states', () => {
      const steps = [
        { id: '1', label: 'Completed', description: 'Done', status: 'completed' as const },
        { id: '2', label: 'Processing', description: 'Current', status: 'processing' as const },
        { id: '3', label: 'Error', description: 'Failed', status: 'error' as const },
        { id: '4', label: 'Pending', description: 'Waiting', status: 'pending' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={1}
        />
      );
      
      expect(screen.getByText('Completed')).toHaveClass('text-green-800');
      expect(screen.getByText('Processing')).toHaveClass('text-blue-800');
      expect(screen.getByText('Error')).toHaveClass('text-red-800');
      expect(screen.getByText('Pending')).toHaveClass('text-gray-600');
    });
  });

  describe('Loading Animation', () => {
    it('should show animated loading dots', () => {
      render(<ProcessingView {...defaultProps} />);
      
      const loadingDots = screen.getAllByText('.', { exact: false })[0]?.parentElement;
      expect(loadingDots).toBeInTheDocument();
    });

    it('should show time estimate message', () => {
      render(<ProcessingView {...defaultProps} />);
      
      expect(screen.getByText(/this usually takes 60-90 seconds/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      render(<ProcessingView {...defaultProps} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '30');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    });

    it('should have accessible loading spinner', () => {
      render(<ProcessingView {...defaultProps} />);
      
      const loadingSpinner = screen.getByRole('status');
      expect(loadingSpinner).toHaveAttribute('aria-label', 'Loading');
    });

    it('should support keyboard navigation for cancel button', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      render(
        <ProcessingView 
          {...defaultProps} 
          onCancel={mockHandlers.onCancel}
        />
      );
      
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      
      await user.tab();
      expect(cancelButton).toHaveFocus();
      
      await user.keyboard('{Enter}');
      expect(mockHandlers.onCancel).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty steps array', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={[]}
          currentStepIndex={0}
        />
      );
      
      expect(screen.getByText('Step 1 of 0')).toBeInTheDocument();
    });

    it('should handle negative currentStepIndex', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          currentStepIndex={-1}
        />
      );
      
      expect(screen.getByText('Step 1 of 3')).toBeInTheDocument();
    });

    it('should handle progress over 100%', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          overallProgress={150}
        />
      );
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
    });

    it('should handle negative progress', () => {
      render(
        <ProcessingView 
          {...defaultProps} 
          overallProgress={-10}
        />
      );
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    });

    it('should handle steps without duration', () => {
      const steps = [
        { id: '1', label: 'No Duration Step', description: 'Processing', status: 'processing' as const },
      ];
      
      render(
        <ProcessingView 
          {...defaultProps} 
          steps={steps}
          currentStepIndex={0}
        />
      );
      
      expect(screen.queryByText(/estimated time/i)).not.toBeInTheDocument();
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily when timer updates', () => {
      const renderSpy = jest.fn();
      const TestComponent = (props: any) => {
        renderSpy();
        return <ProcessingView {...props} />;
      };
      
      render(<TestComponent {...defaultProps} />);
      
      const initialRenderCount = renderSpy.mock.calls.length;
      
      act(() => {
        jest.advanceTimersByTime(5000); // 5 seconds
      });
      
      // Component should update for timer, but efficiently
      expect(renderSpy.mock.calls.length).toBeGreaterThan(initialRenderCount);
    });

    it('should handle rapid prop changes gracefully', () => {
      const { rerender } = render(<ProcessingView {...defaultProps} />);
      
      // Rapid progress updates
      for (let i = 0; i <= 100; i += 10) {
        rerender(
          <ProcessingView 
            {...defaultProps} 
            overallProgress={i}
            currentStepIndex={Math.floor(i / 50)}
          />
        );
      }
      
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });
});