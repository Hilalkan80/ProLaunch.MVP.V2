import React from 'react';
import { screen, act } from '@testing-library/react';
import { render, disableAnimations } from './testUtils';
import { 
  LoadingSpinner, 
  ProgressBar, 
  LoadingDots, 
  Skeleton, 
  TypingIndicator, 
  PulseLoader 
} from '../LoadingStates';

// Mock timers for animation testing
jest.useFakeTimers();

describe('LoadingStates Components', () => {
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

  describe('LoadingSpinner', () => {
    it('should render with default props', () => {
      render(<LoadingSpinner />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toBeInTheDocument();
      expect(spinner).toHaveAttribute('aria-label', 'Loading');
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should apply correct size classes', () => {
      const sizes = ['sm', 'md', 'lg'] as const;
      const expectedClasses = ['h-4 w-4', 'h-6 w-6', 'h-8 w-8'];
      
      sizes.forEach((size, index) => {
        const { rerender } = render(<LoadingSpinner size={size} />);
        const spinner = screen.getByRole('status');
        expect(spinner).toHaveClass(expectedClasses[index]);
      });
    });

    it('should apply custom className', () => {
      const customClass = 'custom-spinner-class';
      render(<LoadingSpinner className={customClass} />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass(customClass);
    });

    it('should have proper accessibility attributes', () => {
      render(<LoadingSpinner />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveAttribute('aria-label', 'Loading');
      
      const srText = screen.getByText('Loading...');
      expect(srText).toHaveClass('sr-only');
    });

    it('should have animation classes', () => {
      render(<LoadingSpinner />);
      
      const spinner = screen.getByRole('status');
      expect(spinner).toHaveClass('animate-spin');
      expect(spinner).toHaveClass('rounded-full');
      expect(spinner).toHaveClass('border-2');
    });
  });

  describe('ProgressBar', () => {
    it('should render with default props', () => {
      render(<ProgressBar progress={50} />);
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
      
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('Progress')).toBeInTheDocument();
    });

    it('should hide percentage when showPercentage is false', () => {
      render(<ProgressBar progress={75} showPercentage={false} />);
      
      expect(screen.queryByText('75%')).not.toBeInTheDocument();
      expect(screen.queryByText('Progress')).not.toBeInTheDocument();
    });

    it('should apply correct size classes', () => {
      const sizes = ['sm', 'md', 'lg'] as const;
      const expectedClasses = ['h-2', 'h-3', 'h-4'];
      
      sizes.forEach((size, index) => {
        render(<ProgressBar progress={50} size={size} />);
        const progressBar = screen.getByRole('progressbar');
        expect(progressBar).toHaveClass(expectedClasses[index]);
      });
    });

    it('should apply correct color classes', () => {
      const colors = ['blue', 'green', 'yellow', 'red'] as const;
      const expectedClasses = ['bg-blue-600', 'bg-green-600', 'bg-yellow-500', 'bg-red-600'];
      
      colors.forEach((color, index) => {
        render(<ProgressBar progress={50} color={color} />);
        const progressBar = screen.getByRole('progressbar');
        expect(progressBar).toHaveClass(expectedClasses[index]);
      });
    });

    it('should animate progress changes', () => {
      const { rerender } = render(<ProgressBar progress={0} />);
      
      // Initial progress should animate to actual value
      expect(screen.getByText('0%')).toBeInTheDocument();
      
      act(() => {
        jest.advanceTimersByTime(150); // Wait for animation delay
      });
      
      expect(screen.getByText('0%')).toBeInTheDocument();
      
      // Change progress
      rerender(<ProgressBar progress={100} />);
      
      act(() => {
        jest.advanceTimersByTime(150);
      });
      
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('should clamp progress values to 0-100 range', () => {
      // Test negative value
      render(<ProgressBar progress={-10} />);
      act(() => {
        jest.advanceTimersByTime(150);
      });
      
      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
      
      // Test value over 100
      const { rerender } = render(<ProgressBar progress={150} />);
      act(() => {
        jest.advanceTimersByTime(150);
      });
      
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
    });

    it('should apply custom className', () => {
      const customClass = 'custom-progress-class';
      render(<ProgressBar progress={50} className={customClass} />);
      
      const container = screen.getByText('Progress').closest('.custom-progress-class');
      expect(container).toBeInTheDocument();
    });
  });

  describe('LoadingDots', () => {
    it('should render with default props', () => {
      render(<LoadingDots />);
      
      const dotsContainer = screen.getByRole('status', { hidden: true }) || 
                           screen.getByText('').parentElement?.parentElement;
      expect(dotsContainer).toBeInTheDocument();
    });

    it('should render three dots', () => {
      const { container } = render(<LoadingDots />);
      
      const dots = container.querySelectorAll('.animate-pulse');
      expect(dots).toHaveLength(3);
    });

    it('should apply correct size classes', () => {
      const sizes = ['sm', 'md', 'lg'] as const;
      const expectedClasses = ['h-1 w-1', 'h-2 w-2', 'h-3 w-3'];
      
      sizes.forEach((size, index) => {
        const { container } = render(<LoadingDots size={size} />);
        const dots = container.querySelectorAll('.animate-pulse');
        dots.forEach(dot => {
          expect(dot).toHaveClass(expectedClasses[index]);
        });
      });
    });

    it('should apply custom className', () => {
      const customClass = 'custom-dots-class';
      const { container } = render(<LoadingDots className={customClass} />);
      
      const dotsContainer = container.querySelector(`.${customClass}`);
      expect(dotsContainer).toBeInTheDocument();
    });

    it('should have staggered animation delays', () => {
      const { container } = render(<LoadingDots />);
      
      const dots = container.querySelectorAll('.animate-pulse');
      expect(dots[0]).toHaveStyle('animation-delay: 0ms');
      expect(dots[1]).toHaveStyle('animation-delay: 150ms');
      expect(dots[2]).toHaveStyle('animation-delay: 300ms');
    });
  });

  describe('Skeleton', () => {
    it('should render with default props (single line)', () => {
      const { container } = render(<Skeleton />);
      
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      expect(skeletonElements).toHaveLength(1);
      expect(skeletonElements[0]).toHaveClass('bg-gray-200', 'rounded', 'h-4', 'w-full');
    });

    it('should render multiple lines', () => {
      const { container } = render(<Skeleton lines={3} />);
      
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      expect(skeletonElements).toHaveLength(3);
    });

    it('should make last line shorter when multiple lines', () => {
      const { container } = render(<Skeleton lines={3} />);
      
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      const lastLine = skeletonElements[skeletonElements.length - 1];
      
      expect(lastLine).toHaveClass('w-3/4');
      
      // Other lines should be full width
      for (let i = 0; i < skeletonElements.length - 1; i++) {
        expect(skeletonElements[i]).toHaveClass('w-full');
      }
    });

    it('should apply custom height', () => {
      const customHeight = 'h-8';
      const { container } = render(<Skeleton height={customHeight} />);
      
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      expect(skeletonElements[0]).toHaveClass(customHeight);
    });

    it('should apply custom className', () => {
      const customClass = 'custom-skeleton-class';
      const { container } = render(<Skeleton className={customClass} />);
      
      const skeletonContainer = container.querySelector(`.${customClass}`);
      expect(skeletonContainer).toBeInTheDocument();
    });

    it('should have proper animation class', () => {
      const { container } = render(<Skeleton />);
      
      const animatedContainer = container.querySelector('.animate-pulse');
      expect(animatedContainer).toBeInTheDocument();
    });
  });

  describe('TypingIndicator', () => {
    it('should render with default props', () => {
      render(<TypingIndicator />);
      
      expect(screen.getByText('AI is typing')).toBeInTheDocument();
    });

    it('should include loading dots', () => {
      const { container } = render(<TypingIndicator />);
      
      // Should contain dots (from LoadingDots component)
      const dots = container.querySelectorAll('.animate-pulse');
      expect(dots.length).toBeGreaterThan(0);
    });

    it('should apply custom className', () => {
      const customClass = 'custom-typing-class';
      const { container } = render(<TypingIndicator className={customClass} />);
      
      const typingContainer = container.querySelector(`.${customClass}`);
      expect(typingContainer).toBeInTheDocument();
    });

    it('should have proper layout structure', () => {
      const { container } = render(<TypingIndicator />);
      
      const flexContainer = container.querySelector('.flex.items-center.space-x-1');
      expect(flexContainer).toBeInTheDocument();
    });
  });

  describe('PulseLoader', () => {
    it('should render with default props', () => {
      const { container } = render(<PulseLoader />);
      
      const pulseContainer = container.querySelector('.relative');
      expect(pulseContainer).toBeInTheDocument();
      
      const pulseElements = container.querySelectorAll('.rounded-full');
      expect(pulseElements).toHaveLength(2); // One pulsing, one static
    });

    it('should apply correct size classes', () => {
      const sizes = ['sm', 'md', 'lg'] as const;
      const expectedClasses = ['h-8 w-8', 'h-12 w-12', 'h-16 w-16'];
      
      sizes.forEach((size, index) => {
        const { container } = render(<PulseLoader size={size} />);
        const sizedElements = container.querySelectorAll(`.${expectedClasses[index].split(' ')[0]}`);
        expect(sizedElements.length).toBeGreaterThan(0);
      });
    });

    it('should apply correct color classes', () => {
      const colors = ['blue', 'green', 'gray'] as const;
      const expectedClasses = ['bg-blue-600', 'bg-green-600', 'bg-gray-400'];
      
      colors.forEach((color, index) => {
        const { container } = render(<PulseLoader color={color} />);
        const coloredElements = container.querySelectorAll(`.${expectedClasses[index]}`);
        expect(coloredElements.length).toBeGreaterThan(0);
      });
    });

    it('should have pulsing animation', () => {
      const { container } = render(<PulseLoader />);
      
      const pulsingElement = container.querySelector('.animate-ping');
      expect(pulsingElement).toBeInTheDocument();
      expect(pulsingElement).toHaveClass('opacity-75');
    });

    it('should apply custom className', () => {
      const customClass = 'custom-pulse-class';
      const { container } = render(<PulseLoader className={customClass} />);
      
      const pulseContainer = container.querySelector(`.${customClass}`);
      expect(pulseContainer).toBeInTheDocument();
    });

    it('should have proper layered structure', () => {
      const { container } = render(<PulseLoader />);
      
      const relativeContainer = container.querySelector('.relative');
      const absoluteElement = container.querySelector('.absolute.inset-0');
      const staticElement = container.querySelector('.relative:not(.absolute)');
      
      expect(relativeContainer).toBeInTheDocument();
      expect(absoluteElement).toBeInTheDocument();
      expect(staticElement).toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    it('should work well together in complex layouts', () => {
      render(
        <div>
          <LoadingSpinner size="sm" />
          <ProgressBar progress={75} size="lg" color="green" />
          <LoadingDots size="md" />
          <Skeleton lines={2} height="h-6" />
          <TypingIndicator />
          <PulseLoader size="lg" color="blue" />
        </div>
      );
      
      // All components should render without conflicts
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText('AI is typing')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('should maintain proper accessibility when combined', () => {
      render(
        <div>
          <LoadingSpinner />
          <ProgressBar progress={50} />
        </div>
      );
      
      const statusElements = screen.getAllByRole('status');
      const progressBar = screen.getByRole('progressbar');
      
      expect(statusElements.length).toBeGreaterThan(0);
      expect(progressBar).toBeInTheDocument();
      
      // Each should have proper ARIA attributes
      statusElements.forEach(element => {
        expect(element).toHaveAttribute('aria-label');
      });
      
      expect(progressBar).toHaveAttribute('aria-valuenow');
    });
  });

  describe('Performance', () => {
    it('should not cause memory leaks with timers', () => {
      const { unmount } = render(<ProgressBar progress={0} />);
      
      const clearTimeoutSpy = jest.spyOn(global, 'clearTimeout');
      unmount();
      
      // ProgressBar uses setTimeout for animation delay
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('should handle rapid prop changes gracefully', () => {
      const { rerender } = render(<ProgressBar progress={0} />);
      
      // Rapidly change progress
      for (let i = 0; i <= 100; i += 10) {
        rerender(<ProgressBar progress={i} />);
      }
      
      // Should not throw errors
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    it('should clean up properly on unmount', () => {
      const components = [
        <LoadingSpinner key="spinner" />,
        <ProgressBar key="progress" progress={50} />,
        <LoadingDots key="dots" />,
        <Skeleton key="skeleton" />,
        <TypingIndicator key="typing" />,
        <PulseLoader key="pulse" />
      ];
      
      components.forEach(component => {
        const { unmount } = render(component);
        expect(() => unmount()).not.toThrow();
      });
    });
  });

  describe('Animation States', () => {
    it('should have consistent animation classes across components', () => {
      const { container } = render(
        <div>
          <LoadingDots />
          <Skeleton />
          <PulseLoader />
        </div>
      );
      
      const animatedElements = container.querySelectorAll('.animate-pulse, .animate-ping, .animate-spin');
      expect(animatedElements.length).toBeGreaterThan(0);
    });

    it('should support animation disable for testing', () => {
      // Animation cleanup is called in beforeEach, so animations should be disabled
      const { container } = render(<LoadingSpinner />);
      
      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
      
      // The disableAnimations function should have added CSS to disable animations
      const styleElements = document.head.querySelectorAll('style');
      const hasAnimationDisableStyle = Array.from(styleElements).some(style => 
        style.innerHTML.includes('animation-duration: 0s')
      );
      expect(hasAnimationDisableStyle).toBe(true);
    });
  });

  describe('Data TestIds', () => {
    it('should have testids for LoadingSpinner', () => {
      render(<LoadingSpinner />);
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('should have testids for ProgressBar', () => {
      render(<ProgressBar progress={50} />);
      expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
      expect(screen.getByTestId('progress-bar-header')).toBeInTheDocument();
      expect(screen.getByTestId('progress-label')).toBeInTheDocument();
      expect(screen.getByTestId('progress-percentage')).toBeInTheDocument();
      expect(screen.getByTestId('progress-bar-track')).toBeInTheDocument();
      expect(screen.getByTestId('progress-bar-fill')).toBeInTheDocument();
    });

    it('should have testids for LoadingDots', () => {
      render(<LoadingDots />);
      expect(screen.getByTestId('loading-dots')).toBeInTheDocument();
      expect(screen.getByTestId('loading-dot-1')).toBeInTheDocument();
      expect(screen.getByTestId('loading-dot-2')).toBeInTheDocument();
      expect(screen.getByTestId('loading-dot-3')).toBeInTheDocument();
    });

    it('should have testids for Skeleton', () => {
      render(<Skeleton lines={3} />);
      expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
      expect(screen.getByTestId('skeleton-line-1')).toBeInTheDocument();
      expect(screen.getByTestId('skeleton-line-2')).toBeInTheDocument();
      expect(screen.getByTestId('skeleton-line-3')).toBeInTheDocument();
    });

    it('should have testids for TypingIndicator', () => {
      render(<TypingIndicator />);
      expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('typing-text')).toBeInTheDocument();
    });

    it('should have testids for PulseLoader', () => {
      render(<PulseLoader />);
      expect(screen.getByTestId('pulse-loader')).toBeInTheDocument();
      expect(screen.getByTestId('pulse-loader-ring')).toBeInTheDocument();
      expect(screen.getByTestId('pulse-loader-core')).toBeInTheDocument();
    });
  });

  describe('Ref Forwarding', () => {
    it('should forward ref for LoadingSpinner', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<LoadingSpinner ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'loading-spinner');
    });

    it('should forward ref for ProgressBar', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<ProgressBar progress={50} ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'progress-bar');
    });

    it('should forward ref for LoadingDots', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<LoadingDots ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'loading-dots');
    });

    it('should forward ref for Skeleton', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<Skeleton ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'skeleton-loader');
    });

    it('should forward ref for TypingIndicator', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<TypingIndicator ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'typing-indicator');
    });

    it('should forward ref for PulseLoader', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<PulseLoader ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'pulse-loader');
    });
  });

  describe('Component DisplayNames', () => {
    it('should have proper displayNames', () => {
      expect(LoadingSpinner.displayName).toBe('LoadingSpinner');
      expect(ProgressBar.displayName).toBe('ProgressBar');
      expect(LoadingDots.displayName).toBe('LoadingDots');
      expect(Skeleton.displayName).toBe('Skeleton');
      expect(TypingIndicator.displayName).toBe('TypingIndicator');
      expect(PulseLoader.displayName).toBe('PulseLoader');
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle ProgressBar with extreme values gracefully', () => {
      const extremeValues = [-100, -1, 0, 0.5, 50.7, 99.9, 100, 101, 1000];
      
      extremeValues.forEach(value => {
        render(<ProgressBar progress={value} />);
        const progressBar = screen.getByRole('progressbar');
        
        const clampedValue = Math.max(0, Math.min(100, value));
        const roundedValue = Math.round(clampedValue);
        
        act(() => {
          jest.advanceTimersByTime(150);
        });
        
        expect(progressBar).toHaveAttribute('aria-valuenow', roundedValue.toString());
      });
    });

    it('should handle Skeleton with zero lines', () => {
      const { container } = render(<Skeleton lines={0} />);
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      expect(skeletonElements).toHaveLength(0);
    });

    it('should handle Skeleton with negative lines', () => {
      const { container } = render(<Skeleton lines={-1} />);
      const skeletonElements = container.querySelectorAll('.animate-pulse > div');
      expect(skeletonElements).toHaveLength(0);
    });

    it('should handle empty or invalid className gracefully', () => {
      const components = [
        <LoadingSpinner key="spinner" className="" />,
        <ProgressBar key="progress" progress={50} className={null as any} />,
        <LoadingDots key="dots" className={undefined as any} />
      ];
      
      components.forEach(component => {
        expect(() => render(component)).not.toThrow();
      });
    });

    it('should handle rapid re-renders without memory leaks', () => {
      const TestComponent = ({ show }: { show: boolean }) => (
        show ? (
          <div>
            <LoadingSpinner />
            <ProgressBar progress={Math.random() * 100} />
            <PulseLoader />
          </div>
        ) : null
      );
      
      const { rerender } = render(<TestComponent show={true} />);
      
      // Rapidly toggle component visibility
      for (let i = 0; i < 10; i++) {
        rerender(<TestComponent show={i % 2 === 0} />);
      }
      
      // Should not throw or cause memory leaks
      expect(() => {
        rerender(<TestComponent show={false} />);
      }).not.toThrow();
    });

    it('should maintain consistent behavior across different screen sizes', () => {
      const originalInnerWidth = window.innerWidth;
      
      [320, 768, 1024, 1920].forEach(width => {
        Object.defineProperty(window, 'innerWidth', {
          writable: true,
          configurable: true,
          value: width,
        });
        
        render(
          <div>
            <LoadingSpinner />
            <ProgressBar progress={75} />
            <LoadingDots />
          </div>
        );
        
        // Components should render consistently
        expect(screen.getByRole('status')).toBeInTheDocument();
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
        expect(screen.getByText('75%')).toBeInTheDocument();
      });
      
      // Restore original window width
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: originalInnerWidth,
      });
    });
  });
});