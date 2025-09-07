import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockHandlers, disableAnimations } from './testUtils';
import { ProductIdeaForm } from '../ProductIdeaForm';

describe('ProductIdeaForm', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanupAnimations();
  });

  describe('Rendering', () => {
    it('should render with default props', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      expect(screen.getByRole('form')).toBeInTheDocument();
      expect(screen.getByLabelText(/what's your product idea/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
    });

    it('should render with custom placeholder', () => {
      const customPlaceholder = 'Tell me your amazing idea...';
      render(
        <ProductIdeaForm 
          onSubmit={mockHandlers.onSubmit} 
          placeholder={customPlaceholder} 
        />
      );
      
      expect(screen.getByPlaceholderText(customPlaceholder)).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      const customClass = 'custom-form-class';
      render(
        <ProductIdeaForm 
          onSubmit={mockHandlers.onSubmit} 
          className={customClass} 
        />
      );
      
      expect(screen.getByRole('form')).toHaveClass(customClass);
    });

    it('should display character counter', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      expect(screen.getByText('0/500')).toBeInTheDocument();
    });

    it('should display suggestion chips', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      expect(screen.getByText('Organic dog treats')).toBeInTheDocument();
      expect(screen.getByText('Smart home gadget')).toBeInTheDocument();
      expect(screen.getByText('Eco-friendly packaging')).toBeInTheDocument();
    });

    it('should show keyboard hint', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      expect(screen.getByText(/press enter to submit/i)).toBeInTheDocument();
    });
  });

  describe('User Interactions', () => {
    it('should update character counter when typing', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello world');
      
      expect(screen.getByText('11/500')).toBeInTheDocument();
    });

    it('should fill textarea when suggestion chip is clicked', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const suggestion = screen.getByText('Organic dog treats');
      await user.click(suggestion);
      
      const textarea = screen.getByRole('textbox');
      expect(textarea).toHaveValue('Organic dog treats');
      expect(screen.getByText('18/500')).toBeInTheDocument();
    });

    it('should clear form when Clear button is clicked', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Some product idea');
      
      const clearButton = screen.getByRole('button', { name: /clear/i });
      await user.click(clearButton);
      
      expect(textarea).toHaveValue('');
      expect(screen.getByText('0/500')).toBeInTheDocument();
    });

    it('should disable Clear button when textarea is empty', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const clearButton = screen.getByRole('button', { name: /clear/i });
      expect(clearButton).toBeDisabled();
    });

    it('should enable Clear button when textarea has content', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Content');
      
      const clearButton = screen.getByRole('button', { name: /clear/i });
      expect(clearButton).toBeEnabled();
    });
  });

  describe('Form Validation', () => {
    it('should show validation error for input too short', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      await user.type(textarea, 'Short');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/please provide at least 10 characters/i)).toBeInTheDocument();
      });
      
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });

    it('should show validation error for input too long', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      const longText = 'A'.repeat(501);
      await user.type(textarea, longText);
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText(/please keep your description under 500 characters/i)).toBeInTheDocument();
      });
      
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });

    it('should disable submit button when input is invalid', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      expect(submitButton).toBeDisabled();
      
      await user.type(textarea, 'Short');
      expect(submitButton).toBeDisabled();
    });

    it('should enable submit button when input is valid', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      await user.type(textarea, 'This is a valid product idea with enough characters');
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
    });

    it('should submit form with valid input', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      const validIdea = 'This is a valid product idea with enough characters to pass validation';
      await user.type(textarea, validIdea);
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockHandlers.onSubmit).toHaveBeenCalledWith({
          productIdea: validIdea
        });
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should submit form on Enter key press when valid', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const validIdea = 'This is a valid product idea with enough characters';
      
      await user.type(textarea, validIdea);
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(mockHandlers.onSubmit).toHaveBeenCalledWith({
          productIdea: validIdea
        });
      });
    });

    it('should not submit form on Enter key press when invalid', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      await user.type(textarea, 'Short');
      await user.keyboard('{Enter}');
      
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });

    it('should allow new line on Shift+Enter', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      await user.type(textarea, 'First line');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Second line');
      
      expect(textarea).toHaveValue('First line\nSecond line');
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('should disable form when loading', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /analyzing/i });
      const clearButton = screen.getByRole('button', { name: /clear/i });
      
      expect(textarea).toBeDisabled();
      expect(submitButton).toBeDisabled();
      expect(clearButton).toBeDisabled();
      
      // Check suggestion chips are also disabled
      const suggestion = screen.getByText('Organic dog treats');
      expect(suggestion).toBeDisabled();
    });

    it('should show loading text on submit button when loading', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      expect(screen.getByRole('button', { name: /analyzing/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /start analysis/i })).not.toBeInTheDocument();
    });

    it('should not submit when loading', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      const submitButton = screen.getByRole('button', { name: /analyzing/i });
      await user.click(submitButton);
      
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and roles', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const form = screen.getByRole('form');
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      expect(form).toBeInTheDocument();
      expect(textarea).toHaveAccessibleName(/what's your product idea/i);
      expect(submitButton).toBeInTheDocument();
    });

    it('should show validation errors with role="alert"', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      await user.type(textarea, 'Short');
      await user.click(submitButton);
      
      await waitFor(() => {
        const errorMessage = screen.getByRole('alert');
        expect(errorMessage).toBeInTheDocument();
        expect(errorMessage).toHaveTextContent(/please provide at least 10 characters/i);
      });
    });

    it('should support keyboard navigation through all interactive elements', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Tab through all focusable elements
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      // Skip suggestion chips and go to buttons
      await user.tab({ shift: true });
      await user.tab();
      
      // Should be able to reach all buttons
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(1);
    });

    it('should have proper focus management', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.click(textarea);
      
      expect(textarea).toHaveFocus();
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid typing and validation changes', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      // Rapid typing simulation
      await user.type(textarea, 'A');
      await user.type(textarea, 'B');
      await user.type(textarea, 'C');
      
      expect(screen.getByText('3/500')).toBeInTheDocument();
    });

    it('should handle form reset while typing', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Some content');
      
      const clearButton = screen.getByRole('button', { name: /clear/i });
      await user.click(clearButton);
      
      expect(textarea).toHaveValue('');
      expect(screen.getByText('0/500')).toBeInTheDocument();
    });

    it('should handle exact boundary lengths', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      // Test minimum valid length (10 characters)
      await user.clear(textarea);
      await user.type(textarea, '1234567890'); // exactly 10 chars
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
      
      // Test maximum valid length (500 characters)
      const maxValidText = 'A'.repeat(500);
      await user.clear(textarea);
      await user.type(textarea, maxValidText);
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
    });

    it('should handle special characters and unicode', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const specialText = 'Product with émojis 🚀 and special chars: @#$%^&*()';
      
      await user.type(textarea, specialText);
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(mockHandlers.onSubmit).toHaveBeenCalledWith({
          productIdea: specialText
        });
      });
    });

    it('should handle paste operations correctly', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      const pastedText = 'This is a pasted product idea that meets requirements';
      
      await user.click(textarea);
      await user.paste(pastedText);
      
      expect(textarea).toHaveValue(pastedText);
      expect(screen.getByText(`${pastedText.length}/500`)).toBeInTheDocument();
    });

    it('should handle backspace and delete operations', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test content');
      
      // Delete some characters
      await user.keyboard('{Backspace}{Backspace}');
      
      expect(textarea).toHaveValue('Test conte');
      expect(screen.getByText('9/500')).toBeInTheDocument();
    });

    it('should handle suggestion chip clicks while form has content', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Previous content');
      
      const suggestion = screen.getByText('Organic dog treats');
      await user.click(suggestion);
      
      // Should replace existing content
      expect(textarea).toHaveValue('Organic dog treats');
      expect(screen.getByText('18/500')).toBeInTheDocument();
    });

    it('should prevent form submission during loading via Enter key', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      const textarea = screen.getByRole('textbox');
      await user.keyboard('{Enter}');
      
      expect(mockHandlers.onSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Component Lifecycle', () => {
    it('should maintain state during re-renders', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Persistent content here');
      
      expect(textarea).toHaveValue('Persistent content here');
      
      // Re-render with same props
      rerender(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Content should be preserved
      expect(screen.getByRole('textbox')).toHaveValue('Persistent content here');
    });

    it('should clean up properly on unmount', () => {
      const { unmount } = render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Should not throw error on unmount
      expect(() => unmount()).not.toThrow();
    });

    it('should update when placeholder prop changes', () => {
      const { rerender } = render(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} placeholder="Original placeholder" />
      );
      
      expect(screen.getByPlaceholderText('Original placeholder')).toBeInTheDocument();
      
      rerender(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} placeholder="Updated placeholder" />
      );
      
      expect(screen.getByPlaceholderText('Updated placeholder')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Original placeholder')).not.toBeInTheDocument();
    });

    it('should update when loading state changes', async () => {
      const { rerender } = render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      expect(screen.getByRole('button', { name: /start analysis/i })).toBeEnabled();
      
      rerender(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      expect(screen.getByRole('button', { name: /analyzing/i })).toBeDisabled();
      
      rerender(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={false} />);
      
      expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
    });
  });

  describe('Performance and Error Handling', () => {
    it('should handle rapid suggestion chip clicks', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const suggestion1 = screen.getByText('Organic dog treats');
      const suggestion2 = screen.getByText('Smart home gadget');
      const textarea = screen.getByRole('textbox');
      
      // Rapid clicks
      await user.click(suggestion1);
      await user.click(suggestion2);
      
      expect(textarea).toHaveValue('Smart home gadget');
    });

    it('should handle onSubmit prop changes', async () => {
      const user = userEvent.setup();
      const firstHandler = jest.fn();
      const secondHandler = jest.fn();
      
      const { rerender } = render(<ProductIdeaForm onSubmit={firstHandler} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Valid product idea here');
      
      // Change handler
      rerender(<ProductIdeaForm onSubmit={secondHandler} />);
      
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(secondHandler).toHaveBeenCalled();
        expect(firstHandler).not.toHaveBeenCalled();
      });
    });

    it('should handle form validation during rapid state changes', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      // Type invalid content
      await user.type(textarea, 'Short');
      
      // Change to loading state
      rerender(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} isLoading={true} />);
      
      // Should still show character counter
      expect(screen.getByText('5/500')).toBeInTheDocument();
    });

    it('should maintain character count consistency', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByRole('textbox');
      
      // Type and delete characters in various patterns
      await user.type(textarea, 'Hello');
      expect(screen.getByText('5/500')).toBeInTheDocument();
      
      await user.keyboard('{selectall}{backspace}');
      expect(screen.getByText('0/500')).toBeInTheDocument();
      
      await user.type(textarea, 'New content here');
      expect(screen.getByText('16/500')).toBeInTheDocument();
    });
  });

  describe('Data Testids', () => {
    it('should have all required data-testid attributes', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      // Main form elements
      expect(screen.getByTestId('product-idea-form')).toBeInTheDocument();
      expect(screen.getByTestId('product-idea-label')).toBeInTheDocument();
      expect(screen.getByTestId('product-idea-textarea')).toBeInTheDocument();
      expect(screen.getByTestId('character-counter')).toBeInTheDocument();
      expect(screen.getByTestId('suggestion-chips')).toBeInTheDocument();
      expect(screen.getByTestId('suggestions-label')).toBeInTheDocument();
      expect(screen.getByTestId('form-instructions')).toBeInTheDocument();
      expect(screen.getByTestId('form-actions')).toBeInTheDocument();
      expect(screen.getByTestId('clear-button')).toBeInTheDocument();
      expect(screen.getByTestId('submit-button')).toBeInTheDocument();
    });

    it('should have data-testid for all suggestion chips', () => {
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const expectedSuggestions = [
        'organic-dog-treats',
        'smart-home-gadget',
        'eco-friendly-packaging',
        'online-fitness-app',
        'sustainable-fashion'
      ];
      
      expectedSuggestions.forEach(suggestion => {
        expect(screen.getByTestId(`suggestion-chip-${suggestion}`)).toBeInTheDocument();
      });
    });

    it('should show validation error with correct testid', async () => {
      const user = userEvent.setup();
      render(<ProductIdeaForm onSubmit={mockHandlers.onSubmit} />);
      
      const textarea = screen.getByTestId('product-idea-textarea');
      const submitButton = screen.getByTestId('submit-button');
      
      await user.type(textarea, 'Short');
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByTestId('product-idea-error')).toBeInTheDocument();
      });
    });
  });

  describe('Ref Forwarding', () => {
    it('should forward ref to form element', () => {
      const ref = React.createRef<HTMLFormElement>();
      render(<ProductIdeaForm ref={ref} onSubmit={mockHandlers.onSubmit} />);
      
      expect(ref.current).toBeInstanceOf(HTMLFormElement);
      expect(ref.current?.tagName).toBe('FORM');
    });

    it('should have proper displayName', () => {
      expect(ProductIdeaForm.displayName).toBe('ProductIdeaForm');
    });
  });
});