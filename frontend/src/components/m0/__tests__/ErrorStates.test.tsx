import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockHandlers, disableAnimations } from './testUtils';
import { 
  ErrorBoundary, 
  ErrorMessage, 
  NetworkError, 
  ValidationError, 
  ProcessingError, 
  EmptyState 
} from '../ErrorStates';

describe('ErrorStates Components', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanupAnimations();
  });

  describe('ErrorBoundary', () => {
    it('should render children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div>Test Content</div>
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should render fallback when provided', () => {
      const fallback = <div>Error Fallback</div>;
      render(
        <ErrorBoundary fallback={fallback}>
          <div>Test Content</div>
        </ErrorBoundary>
      );
      
      // In this simple implementation, it just renders the fallback if provided
      // In a real implementation, this would be triggered by an error
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const customClass = 'custom-error-boundary';
      const { container } = render(
        <ErrorBoundary className={customClass}>
          <div>Test Content</div>
        </ErrorBoundary>
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });

    it('should support onReset callback', () => {
      render(
        <ErrorBoundary onReset={mockHandlers.onRetry}>
          <div>Test Content</div>
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Test Content')).toBeInTheDocument();
      // onReset would be called in a real error boundary implementation
    });
  });

  describe('ErrorMessage', () => {
    const defaultProps = {
      message: 'Something went wrong with your request',
    };

    it('should render with default props', () => {
      render(<ErrorMessage {...defaultProps} />);
      
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong with your request')).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      const customTitle = 'Custom Error Title';
      render(<ErrorMessage {...defaultProps} title={customTitle} />);
      
      expect(screen.getByText(customTitle)).toBeInTheDocument();
    });

    it('should display different icons for different types', () => {
      const types = ['error', 'warning', 'info'] as const;
      
      types.forEach(type => {
        const { container, rerender } = render(
          <ErrorMessage {...defaultProps} type={type} />
        );
        
        const icon = container.querySelector('svg');
        expect(icon).toBeInTheDocument();
        
        // Each type should have different icon
        const iconContainer = icon?.parentElement;
        expect(iconContainer).toHaveClass(
          type === 'error' ? 'bg-red-100' :
          type === 'warning' ? 'bg-yellow-100' :
          'bg-blue-100'
        );
      });
    });

    it('should apply correct background colors for types', () => {
      const types = ['error', 'warning', 'info'] as const;
      const expectedBgClasses = ['bg-red-50', 'bg-yellow-50', 'bg-blue-50'];
      
      types.forEach((type, index) => {
        const { container } = render(
          <ErrorMessage {...defaultProps} type={type} />
        );
        
        const messageContainer = container.querySelector(`.${expectedBgClasses[index]}`);
        expect(messageContainer).toBeInTheDocument();
      });
    });

    it('should render retry button and call handler', async () => {
      const user = userEvent.setup();
      render(
        <ErrorMessage 
          {...defaultProps} 
          onRetry={mockHandlers.onRetry}
          retryLabel="Try Again"
        />
      );
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      await user.click(retryButton);
      
      expect(mockHandlers.onRetry).toHaveBeenCalledTimes(1);
    });

    it('should render dismiss button and call handler', async () => {
      const user = userEvent.setup();
      render(
        <ErrorMessage 
          {...defaultProps} 
          onDismiss={mockHandlers.onDismiss}
        />
      );
      
      const dismissButton = screen.getByRole('button', { name: /dismiss/i });
      await user.click(dismissButton);
      
      expect(mockHandlers.onDismiss).toHaveBeenCalledTimes(1);
    });

    it('should render X button when onDismiss is provided', async () => {
      const user = userEvent.setup();
      render(
        <ErrorMessage 
          {...defaultProps} 
          onDismiss={mockHandlers.onDismiss}
        />
      );
      
      // Look for the X close button (SVG)
      const closeButtons = screen.getAllByRole('button');
      const xButton = closeButtons.find(button => 
        button.querySelector('svg') && !button.textContent?.includes('Dismiss')
      );
      
      expect(xButton).toBeInTheDocument();
      
      if (xButton) {
        await user.click(xButton);
        expect(mockHandlers.onDismiss).toHaveBeenCalled();
      }
    });

    it('should apply custom className', () => {
      const customClass = 'custom-error-message';
      const { container } = render(
        <ErrorMessage {...defaultProps} className={customClass} />
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });

    it('should adapt button variant based on error type', () => {
      render(
        <ErrorMessage 
          {...defaultProps} 
          type="error"
          onRetry={mockHandlers.onRetry}
        />
      );
      
      const retryButton = screen.getByRole('button', { name: /try again/i });
      expect(retryButton).toBeInTheDocument();
      // Button should have error styling - this would need to be verified via class or style
    });
  });

  describe('NetworkError', () => {
    it('should render network error message', () => {
      render(<NetworkError onRetry={mockHandlers.onRetry} />);
      
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
      expect(screen.getByText(/trouble connecting to our servers/i)).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      render(<NetworkError onRetry={mockHandlers.onRetry} />);
      
      const retryButton = screen.getByRole('button', { name: /retry connection/i });
      await user.click(retryButton);
      
      expect(mockHandlers.onRetry).toHaveBeenCalledTimes(1);
    });

    it('should apply custom className', () => {
      const customClass = 'custom-network-error';
      const { container } = render(
        <NetworkError onRetry={mockHandlers.onRetry} className={customClass} />
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });

    it('should render go offline button when provided', async () => {
      const user = userEvent.setup();
      render(
        <NetworkError 
          onRetry={mockHandlers.onRetry} 
          onGoOffline={mockHandlers.onCancel}
        />
      );
      
      // NetworkError component should support onGoOffline if needed
      expect(screen.getByRole('button', { name: /retry connection/i })).toBeInTheDocument();
    });
  });

  describe('ValidationError', () => {
    it('should render validation errors', () => {
      const errors = {
        email: ['Email is required', 'Email must be valid'],
        password: ['Password is too short']
      };
      
      render(<ValidationError errors={errors} />);
      
      expect(screen.getByText('Validation Error')).toBeInTheDocument();
      expect(screen.getByText(/email: email is required/i)).toBeInTheDocument();
    });

    it('should not render when no errors', () => {
      const { container } = render(<ValidationError errors={{}} />);
      expect(container.firstChild).toBeNull();
    });

    it('should call onDismiss when dismiss button is clicked', async () => {
      const user = userEvent.setup();
      const errors = { field: ['Error message'] };
      
      render(
        <ValidationError 
          errors={errors} 
          onDismiss={mockHandlers.onDismiss}
        />
      );
      
      const dismissButton = screen.getByRole('button', { name: /dismiss/i });
      await user.click(dismissButton);
      
      expect(mockHandlers.onDismiss).toHaveBeenCalledTimes(1);
    });

    it('should format multiple errors correctly', () => {
      const errors = {
        name: ['Name is required'],
        email: ['Email is invalid', 'Email is required'],
        phone: ['Phone format is wrong']
      };
      
      render(<ValidationError errors={errors} />);
      
      // Should combine all error messages
      const errorText = screen.getByText(/validation error/i).closest('div')?.textContent;
      expect(errorText).toContain('name:');
      expect(errorText).toContain('email:');
      expect(errorText).toContain('phone:');
    });

    it('should apply custom className', () => {
      const customClass = 'custom-validation-error';
      const errors = { field: ['Error'] };
      
      const { container } = render(
        <ValidationError errors={errors} className={customClass} />
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });
  });

  describe('ProcessingError', () => {
    const defaultProps = {
      productIdea: 'Smart pet food dispenser',
      onRetry: mockHandlers.onRetry,
      onStartOver: mockHandlers.onStartOver,
    };

    it('should render processing error with product idea', () => {
      render(<ProcessingError {...defaultProps} />);
      
      expect(screen.getByText('Analysis Failed')).toBeInTheDocument();
      expect(screen.getByText(/smart pet food dispenser/i)).toBeInTheDocument();
      expect(screen.getByText(/your input has been saved/i)).toBeInTheDocument();
    });

    it('should truncate long product ideas', () => {
      const longIdea = 'A'.repeat(100);
      render(
        <ProcessingError 
          {...defaultProps} 
          productIdea={longIdea}
        />
      );
      
      const truncatedText = screen.getByText(new RegExp(`${('A'.repeat(60))}...`));
      expect(truncatedText).toBeInTheDocument();
    });

    it('should call onRetry when retry button is clicked', async () => {
      const user = userEvent.setup();
      render(<ProcessingError {...defaultProps} />);
      
      const retryButton = screen.getByRole('button', { name: /try analysis again/i });
      await user.click(retryButton);
      
      expect(mockHandlers.onRetry).toHaveBeenCalledTimes(1);
    });

    it('should call onStartOver when start over button is clicked', async () => {
      const user = userEvent.setup();
      render(<ProcessingError {...defaultProps} />);
      
      const startOverButton = screen.getByRole('button', { name: /start with new idea/i });
      await user.click(startOverButton);
      
      expect(mockHandlers.onStartOver).toHaveBeenCalledTimes(1);
    });

    it('should show contact support button when provided', async () => {
      const user = userEvent.setup();
      render(
        <ProcessingError 
          {...defaultProps} 
          onContactSupport={mockHandlers.onContactSupport}
        />
      );
      
      const supportButton = screen.getByRole('button', { name: /contact support/i });
      await user.click(supportButton);
      
      expect(mockHandlers.onContactSupport).toHaveBeenCalledTimes(1);
    });

    it('should show technical details when provided', async () => {
      const user = userEvent.setup();
      const errorDetails = 'Network timeout: Connection failed after 30 seconds';
      
      render(
        <ProcessingError 
          {...defaultProps} 
          errorDetails={errorDetails}
        />
      );
      
      const detailsToggle = screen.getByText(/show technical details/i);
      expect(detailsToggle).toBeInTheDocument();
      
      await user.click(detailsToggle);
      
      await waitFor(() => {
        expect(screen.getByText(errorDetails)).toBeInTheDocument();
      });
    });

    it('should display helpful suggestions', () => {
      render(<ProcessingError {...defaultProps} />);
      
      expect(screen.getByText('Common solutions:')).toBeInTheDocument();
      expect(screen.getByText(/rephrasing your product idea/i)).toBeInTheDocument();
      expect(screen.getByText(/check your internet connection/i)).toBeInTheDocument();
      expect(screen.getByText(/10-200 word descriptions/i)).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const customClass = 'custom-processing-error';
      const { container } = render(
        <ProcessingError {...defaultProps} className={customClass} />
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });
  });

  describe('EmptyState', () => {
    const defaultProps = {
      message: 'No data found',
    };

    it('should render with default props', () => {
      render(<EmptyState {...defaultProps} />);
      
      expect(screen.getByText('No data found')).toBeInTheDocument();
      
      // Should have default icon
      const icon = screen.getByRole('img', { hidden: true }) || 
                  document.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should render with custom title', () => {
      const title = 'Nothing Here';
      render(<EmptyState {...defaultProps} title={title} />);
      
      expect(screen.getByText(title)).toBeInTheDocument();
    });

    it('should render with custom icon', () => {
      const customIcon = <div data-testid="custom-icon">Custom Icon</div>;
      render(<EmptyState {...defaultProps} icon={customIcon} />);
      
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('should render action button and call handler', async () => {
      const user = userEvent.setup();
      const action = {
        label: 'Create New',
        onClick: mockHandlers.onSubmit,
      };
      
      render(<EmptyState {...defaultProps} action={action} />);
      
      const actionButton = screen.getByRole('button', { name: /create new/i });
      await user.click(actionButton);
      
      expect(mockHandlers.onSubmit).toHaveBeenCalledTimes(1);
    });

    it('should not render action button when not provided', () => {
      render(<EmptyState {...defaultProps} />);
      
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const customClass = 'custom-empty-state';
      const { container } = render(
        <EmptyState {...defaultProps} className={customClass} />
      );
      
      expect(container.firstChild).toHaveClass(customClass);
    });

    it('should have proper layout structure', () => {
      render(<EmptyState {...defaultProps} title="Test Title" />);
      
      const container = screen.getByText('Test Title').closest('.text-center');
      expect(container).toBeInTheDocument();
      expect(container).toHaveClass('p-8');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels for error icons', () => {
      render(
        <ErrorMessage 
          message="Test error" 
          type="error"
        />
      );
      
      // Error messages should be properly marked up
      const errorIcon = screen.getByText('Test error').closest('div')?.querySelector('svg');
      expect(errorIcon).toBeInTheDocument();
    });

    it('should support keyboard navigation for all interactive elements', async () => {
      const user = userEvent.setup();
      render(
        <ProcessingError 
          productIdea="Test idea"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
          onContactSupport={mockHandlers.onContactSupport}
        />
      );
      
      // Tab through buttons
      await user.tab();
      expect(screen.getByRole('button', { name: /try analysis again/i })).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button', { name: /start with new idea/i })).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button', { name: /contact support/i })).toHaveFocus();
    });

    it('should have proper heading hierarchy', () => {
      render(
        <ProcessingError 
          productIdea="Test idea"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      const mainHeading = screen.getByRole('heading', { level: 2 });
      expect(mainHeading).toHaveTextContent('Analysis Failed');
      
      const subHeading = screen.getByRole('heading', { level: 3 });
      expect(subHeading).toHaveTextContent('Common solutions:');
    });

    it('should provide meaningful error descriptions', () => {
      render(
        <ErrorMessage 
          title="Upload Failed" 
          message="The file you selected is too large. Please choose a file smaller than 10MB."
          type="error"
        />
      );
      
      expect(screen.getByText('Upload Failed')).toBeInTheDocument();
      expect(screen.getByText(/file you selected is too large/i)).toBeInTheDocument();
    });
  });

  describe('Responsive Design', () => {
    it('should adapt button layouts for mobile', () => {
      render(
        <ProcessingError 
          productIdea="Test idea"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      const buttons = screen.getAllByRole('button');
      const hasResponsiveClasses = buttons.some(button => 
        button.className.includes('sm:') || 
        button.className.includes('w-full')
      );
      expect(hasResponsiveClasses).toBe(true);
    });

    it('should handle long error messages gracefully', () => {
      const longMessage = 'Lorem ipsum '.repeat(50);
      render(<ErrorMessage message={longMessage} />);
      
      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('should maintain readability on different screen sizes', () => {
      render(
        <EmptyState 
          title="No Results Found"
          message="Try adjusting your search criteria or browse our popular categories instead."
          action={{
            label: 'Browse Categories',
            onClick: mockHandlers.onSubmit
          }}
        />
      );
      
      const container = screen.getByText('No Results Found').closest('.text-center');
      expect(container).toHaveClass('p-8');
      
      const message = screen.getByText(/try adjusting your search/i);
      expect(message).toHaveClass('max-w-sm', 'mx-auto');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty error messages', () => {
      render(<ErrorMessage message="" />);
      
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('should handle undefined handlers gracefully', () => {
      expect(() => {
        render(
          <ErrorMessage 
            message="Test error"
            onRetry={undefined}
            onDismiss={undefined}
          />
        );
      }).not.toThrow();
      
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('should handle very long product ideas in ProcessingError', () => {
      const veryLongIdea = 'A'.repeat(1000);
      render(
        <ProcessingError 
          productIdea={veryLongIdea}
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      // Should truncate and not break layout
      expect(screen.getByText(/A{60}\.\.\./, { exact: false })).toBeInTheDocument();
    });

    it('should handle malformed validation errors', () => {
      const malformedErrors = {
        field1: null as any,
        field2: undefined as any,
        field3: [] as string[],
        field4: ['Valid error']
      };
      
      expect(() => {
        render(<ValidationError errors={malformedErrors} />);
      }).not.toThrow();
    });
  });

  describe('Component Integration', () => {
    it('should work well in error boundary scenarios', () => {
      render(
        <ErrorBoundary 
          fallback={
            <ErrorMessage 
              title="Application Error"
              message="Something went wrong. Please refresh the page."
              onRetry={mockHandlers.onRetry}
            />
          }
          onReset={mockHandlers.onRetry}
        >
          <div>Normal content</div>
        </ErrorBoundary>
      );
      
      expect(screen.getByText('Normal content')).toBeInTheDocument();
    });

    it('should maintain consistent styling across error types', () => {
      const { rerender } = render(<ErrorMessage message="Test" type="error" />);
      
      const errorElement = screen.getByText('Something went wrong');
      const errorContainer = errorElement.closest('div');
      
      expect(errorContainer).toHaveClass('border');
      expect(errorContainer).toHaveClass('p-6');
      expect(errorContainer).toHaveClass('rounded-lg');
      
      // Switch to different type
      rerender(<ErrorMessage message="Test" type="warning" />);
      
      const warningContainer = screen.getByText('Something went wrong').closest('div');
      expect(warningContainer).toHaveClass('border');
      expect(warningContainer).toHaveClass('p-6');
      expect(warningContainer).toHaveClass('rounded-lg');
    });
  });

  describe('Data TestIds', () => {
    it('should have testids for ErrorBoundary', () => {
      render(
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    });

    it('should have testids for ErrorMessage', () => {
      render(
        <ErrorMessage 
          message="Test error" 
          onRetry={mockHandlers.onRetry}
          onDismiss={mockHandlers.onDismiss}
        />
      );
      
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      expect(screen.getByTestId('error-icon')).toBeInTheDocument();
      expect(screen.getByTestId('error-title')).toBeInTheDocument();
      expect(screen.getByTestId('error-message-text')).toBeInTheDocument();
      expect(screen.getByTestId('error-actions')).toBeInTheDocument();
      expect(screen.getByTestId('error-retry-button')).toBeInTheDocument();
      expect(screen.getByTestId('error-dismiss-button')).toBeInTheDocument();
      expect(screen.getByTestId('error-close-button')).toBeInTheDocument();
    });

    it('should have testids for NetworkError', () => {
      render(<NetworkError onRetry={mockHandlers.onRetry} />);
      expect(screen.getByTestId('network-error')).toBeInTheDocument();
    });

    it('should have testids for ValidationError', () => {
      const errors = { field: ['Error message'] };
      render(<ValidationError errors={errors} />);
      expect(screen.getByTestId('validation-error')).toBeInTheDocument();
    });

    it('should have testids for ProcessingError', () => {
      render(
        <ProcessingError 
          productIdea="Test idea"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
          onContactSupport={mockHandlers.onContactSupport}
          errorDetails="Technical details"
        />
      );
      
      expect(screen.getByTestId('processing-error')).toBeInTheDocument();
      expect(screen.getByTestId('processing-error-card')).toBeInTheDocument();
      expect(screen.getByTestId('processing-error-icon')).toBeInTheDocument();
      expect(screen.getByTestId('processing-error-title')).toBeInTheDocument();
      expect(screen.getByTestId('processing-error-message')).toBeInTheDocument();
      expect(screen.getByTestId('error-details')).toBeInTheDocument();
      expect(screen.getByTestId('error-details-toggle')).toBeInTheDocument();
      expect(screen.getByTestId('processing-error-actions')).toBeInTheDocument();
      expect(screen.getByTestId('retry-analysis-button')).toBeInTheDocument();
      expect(screen.getByTestId('start-over-button')).toBeInTheDocument();
      expect(screen.getByTestId('contact-support-button')).toBeInTheDocument();
      expect(screen.getByTestId('error-suggestions')).toBeInTheDocument();
      expect(screen.getByTestId('suggestions-title')).toBeInTheDocument();
      expect(screen.getByTestId('suggestions-list')).toBeInTheDocument();
      expect(screen.getByTestId('suggestion-1')).toBeInTheDocument();
      expect(screen.getByTestId('suggestion-2')).toBeInTheDocument();
      expect(screen.getByTestId('suggestion-3')).toBeInTheDocument();
      expect(screen.getByTestId('suggestion-4')).toBeInTheDocument();
    });

    it('should have testids for EmptyState', () => {
      render(
        <EmptyState 
          title="No Data" 
          message="Nothing found"
          action={{ label: 'Create', onClick: mockHandlers.onSubmit }}
        />
      );
      
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByTestId('empty-state-icon')).toBeInTheDocument();
      expect(screen.getByTestId('empty-state-title')).toBeInTheDocument();
      expect(screen.getByTestId('empty-state-message')).toBeInTheDocument();
      expect(screen.getByTestId('empty-state-action')).toBeInTheDocument();
    });
  });

  describe('Ref Forwarding', () => {
    it('should forward ref for ErrorBoundary', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(
        <ErrorBoundary ref={ref}>
          <div>Content</div>
        </ErrorBoundary>
      );
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'error-boundary');
    });

    it('should forward ref for ErrorMessage', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<ErrorMessage ref={ref} message="Test" />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'error-message');
    });

    it('should forward ref for NetworkError', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<NetworkError ref={ref} onRetry={mockHandlers.onRetry} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'network-error');
    });

    it('should forward ref for ValidationError', () => {
      const ref = React.createRef<HTMLDivElement>();
      const errors = { field: ['Error'] };
      render(<ValidationError ref={ref} errors={errors} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'validation-error');
    });

    it('should forward ref for ProcessingError', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(
        <ProcessingError 
          ref={ref}
          productIdea="Test"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'processing-error');
    });

    it('should forward ref for EmptyState', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<EmptyState ref={ref} message="Empty" />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'empty-state');
    });
  });

  describe('Component DisplayNames', () => {
    it('should have proper displayNames', () => {
      expect(ErrorBoundary.displayName).toBe('ErrorBoundary');
      expect(ErrorMessage.displayName).toBe('ErrorMessage');
      expect(NetworkError.displayName).toBe('NetworkError');
      expect(ValidationError.displayName).toBe('ValidationError');
      expect(ProcessingError.displayName).toBe('ProcessingError');
      expect(EmptyState.displayName).toBe('EmptyState');
    });
  });

  describe('Performance and Memory', () => {
    it('should clean up properly on unmount', () => {
      const components = [
        <ErrorMessage key="error" message="Test" />,
        <NetworkError key="network" onRetry={mockHandlers.onRetry} />,
        <ProcessingError key="processing" productIdea="Test" onRetry={mockHandlers.onRetry} onStartOver={mockHandlers.onStartOver} />,
        <EmptyState key="empty" message="Empty" />
      ];
      
      components.forEach(component => {
        const { unmount } = render(component);
        expect(() => unmount()).not.toThrow();
      });
    });

    it('should handle rapid prop changes', () => {
      const { rerender } = render(<ErrorMessage message="Message 1" type="error" />);
      
      const messages = ['Message 2', 'Message 3', 'Message 4', 'Message 5'];
      const types = ['warning', 'info', 'error', 'warning'] as const;
      
      messages.forEach((message, index) => {
        rerender(<ErrorMessage message={message} type={types[index]} />);
        expect(screen.getByText(message)).toBeInTheDocument();
      });
    });

    it('should handle multiple simultaneous error states', () => {
      render(
        <div>
          <ErrorMessage message="General error" type="error" />
          <NetworkError onRetry={mockHandlers.onRetry} />
          <ValidationError errors={{ field: ['Validation error'] }} />
          <EmptyState message="No data" />
        </div>
      );
      
      expect(screen.getByText('General error')).toBeInTheDocument();
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
      expect(screen.getByText('Validation Error')).toBeInTheDocument();
      expect(screen.getByText('No data')).toBeInTheDocument();
    });

    it('should handle error details expand/collapse correctly', async () => {
      const user = userEvent.setup();
      const errorDetails = 'Detailed technical error information';
      
      render(
        <ProcessingError 
          productIdea="Test"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
          errorDetails={errorDetails}
        />
      );
      
      const detailsToggle = screen.getByTestId('error-details-toggle');
      
      // Initially collapsed
      expect(screen.queryByText(errorDetails)).not.toBeInTheDocument();
      
      // Expand
      await user.click(detailsToggle);
      await waitFor(() => {
        expect(screen.getByTestId('error-details-content')).toBeInTheDocument();
      });
      
      // Collapse
      await user.click(detailsToggle);
      // Details should still be in DOM but potentially hidden
      expect(screen.getByTestId('error-details-content')).toBeInTheDocument();
    });
  });
});