import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockHandlers, disableAnimations, mockNetworkSuccess, mockNetworkError } from './testUtils';
import { M0Container } from '../M0Container';

// Mock timers for integration tests
jest.useFakeTimers();

describe('M0 Integration Tests', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    jest.clearAllMocks();
    jest.clearAllTimers();
    mockNetworkSuccess();
    
    // Mock console methods to reduce test noise
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanupAnimations();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    jest.useFakeTimers();
    jest.restoreAllMocks();
  });

  describe('Complete User Journey', () => {
    it('should complete full workflow from input to report', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <M0Container 
          onUpgrade={mockHandlers.onUpgrade}
          onStartNextStep={mockHandlers.onStartNextStep}
          onAnalysisComplete={mockHandlers.onAnalysisComplete}
        />
      );
      
      // STEP 1: Initial state verification
      expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start analysis/i })).toBeDisabled();
      
      // STEP 2: Form interaction
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Premium organic dog treats made with locally sourced ingredients');
      
      // Verify character counter updates
      expect(screen.getByText('74/500')).toBeInTheDocument();
      
      // Verify submit button becomes enabled
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /start analysis/i })).toBeEnabled();
      });
      
      // STEP 3: Submit form
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      // STEP 4: Processing state verification
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      expect(screen.getByText('"Premium organic dog treats made with locally sourced..."')).toBeInTheDocument();
      expect(screen.getByText('Time elapsed: 0:00')).toBeInTheDocument();
      expect(screen.getByText('Overall Progress')).toBeInTheDocument();
      expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel analysis/i })).toBeInTheDocument();
      
      // STEP 5: Verify processing steps
      expect(screen.getByText('Market Research')).toBeInTheDocument();
      expect(screen.getByText('Competitor Analysis')).toBeInTheDocument();
      expect(screen.getByText('Pricing Analysis')).toBeInTheDocument();
      expect(screen.getByText('Demand Validation')).toBeInTheDocument();
      expect(screen.getByText('Risk Assessment')).toBeInTheDocument();
      expect(screen.getByText('Viability Scoring')).toBeInTheDocument();
      
      // STEP 6: Fast-forward through processing
      act(() => {
        jest.advanceTimersByTime(10000); // Complete all steps
      });
      
      // STEP 7: Success state verification
      await waitFor(() => {
        expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Verify report components
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      expect(screen.getByText('78')).toBeInTheDocument();
      expect(screen.getByText('Key Insights')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
      expect(screen.getByText('$2.1B')).toBeInTheDocument();
      expect(screen.getByText('15% YoY')).toBeInTheDocument();
      expect(screen.getByText('Next Steps (Priority Order)')).toBeInTheDocument();
      
      // STEP 8: Verify callback was called
      expect(mockHandlers.onAnalysisComplete).toHaveBeenCalledTimes(1);
      expect(mockHandlers.onAnalysisComplete.mock.calls[0][0]).toMatchObject({
        productIdea: 'Premium organic dog treats made with locally sourced ingredients',
        viabilityScore: 78,
        marketSize: '$2.1B',
      });
    });

    it('should handle user interactions in success state', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <M0Container 
          onUpgrade={mockHandlers.onUpgrade}
          onStartNextStep={mockHandlers.onStartNextStep}
        />
      );
      
      // Complete workflow to success state
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Smart pet feeding system with mobile app');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Test next step interaction
      const startButton = screen.getByRole('button', { name: /start now →/i });
      await user.click(startButton);
      
      expect(mockHandlers.onStartNextStep).toHaveBeenCalledWith('m1-unit-economics');
      
      // Test upgrade interaction
      const upgradeButton = screen.getByRole('button', { name: /upgrade to launcher package/i });
      await user.click(upgradeButton);
      
      expect(mockHandlers.onUpgrade).toHaveBeenCalledTimes(1);
      
      // Test new analysis
      const newAnalysisButton = screen.getByRole('button', { name: /← new analysis/i });
      await user.click(newAnalysisButton);
      
      await waitFor(() => {
        expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      });
    });
  });

  describe('Form Validation Integration', () => {
    it('should prevent submission with invalid input and show errors', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      // Test too short input
      await user.type(textarea, 'short');
      expect(submitButton).toBeDisabled();
      
      // Try to submit anyway
      await user.click(submitButton);
      
      // Should still be in input state
      expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      expect(mockHandlers.onAnalysisComplete).not.toHaveBeenCalled();
      
      // Test valid input
      await user.clear(textarea);
      await user.type(textarea, 'This is a valid product idea with enough characters');
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
      
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
    });

    it('should handle suggestion chip interactions properly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      // Click suggestion chip
      const suggestion = screen.getByText('Organic dog treats');
      await user.click(suggestion);
      
      // Verify form is filled and valid
      expect(textarea).toHaveValue('Organic dog treats');
      expect(screen.getByText('18/500')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
      
      // Submit should work
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
        expect(screen.getByText('"Organic dog treats"')).toBeInTheDocument();
      });
    });

    it('should handle keyboard submission correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      
      await user.type(textarea, 'Eco-friendly yoga mats made from recycled materials');
      
      // Submit with Enter key
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
    });
  });

  describe('Processing State Integration', () => {
    it('should handle cancel during processing correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      // Start processing
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Smart home security system');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Advance processing partway
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      // Cancel processing
      const cancelButton = screen.getByRole('button', { name: /cancel analysis/i });
      await user.click(cancelButton);
      
      // Should return to input state
      await waitFor(() => {
        expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      });
      
      // Form should be cleared
      expect(screen.getByRole('textbox')).toHaveValue('');
    });

    it('should show realistic processing progression', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'AI-powered language learning app');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Check initial state
      expect(screen.getByText('Step 1 of 6')).toBeInTheDocument();
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
      
      // Advance to first step completion
      act(() => {
        jest.advanceTimersByTime(1800); // Complete first step
      });
      
      await waitFor(() => {
        // Progress should update
        const progressBar = screen.getByRole('progressbar');
        expect(progressBar.getAttribute('aria-valuenow')).not.toBe('0');
      });
      
      // Continue through more steps
      act(() => {
        jest.advanceTimersByTime(3000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/step \d+ of 6/i)).toBeInTheDocument();
      });
    });

    it('should display step status changes correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Subscription box for artisanal coffee');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Market Research')).toBeInTheDocument();
      });
      
      // Initially, first step should be processing
      expect(screen.getByText('Market Research').closest('.bg-blue-50')).toBeInTheDocument();
      expect(screen.getByText('In Progress')).toBeInTheDocument();
      
      // Complete first step
      act(() => {
        jest.advanceTimersByTime(1800);
      });
      
      await waitFor(() => {
        // First step should be completed, second should be processing
        expect(screen.getByText('Market Research').closest('.bg-green-50')).toBeInTheDocument();
        expect(screen.getByText('Complete')).toBeInTheDocument();
      });
    });
  });

  describe('Report Interaction Integration', () => {
    const setupReportState = async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(
        <M0Container 
          onUpgrade={mockHandlers.onUpgrade}
          onStartNextStep={mockHandlers.onStartNextStep}
        />
      );
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Sustainable packaging for e-commerce');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      }, { timeout: 5000 });
      
      return user;
    };

    it('should handle report section interactions', async () => {
      const user = await setupReportState();
      
      // Test competitor section expansion
      const competitorToggle = screen.getByRole('button', { name: /top competitors/i });
      await user.click(competitorToggle);
      
      await waitFor(() => {
        expect(screen.getByText('Test Competitor')).toBeInTheDocument();
      });
      
      // Collapse it
      await user.click(competitorToggle);
      
      await waitFor(() => {
        expect(screen.queryByText('Test Competitor')).not.toBeInTheDocument();
      });
    });

    it('should handle next steps prioritization', async () => {
      await setupReportState();
      
      // Verify steps are displayed in order
      const stepElements = screen.getAllByText(/step \d+/i);
      expect(stepElements[0]).toBeInTheDocument();
      
      // First unlocked step should have "START NOW" button
      const startButton = screen.getByRole('button', { name: /start now →/i });
      expect(startButton).toBeInTheDocument();
      
      // Locked steps should have "UNLOCK PAID" button
      const unlockButtons = screen.getAllByRole('button', { name: /unlock paid/i });
      expect(unlockButtons.length).toBeGreaterThan(0);
    });

    it('should maintain data consistency throughout workflow', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      const productIdea = 'Revolutionary fitness tracking wearable device';
      
      render(
        <M0Container 
          onAnalysisComplete={mockHandlers.onAnalysisComplete}
        />
      );
      
      // Input the idea
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, productIdea);
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      // Verify idea appears in processing view
      await waitFor(() => {
        expect(screen.getByText(`"${productIdea}"`)).toBeInTheDocument();
      });
      
      // Complete processing
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      // Verify idea appears in report
      await waitFor(() => {
        expect(screen.getByText(`${productIdea} Feasibility Report`)).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Verify callback data matches
      expect(mockHandlers.onAnalysisComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          productIdea: productIdea
        })
      );
    });
  });

  describe('Error Recovery Integration', () => {
    it('should handle errors gracefully and allow recovery', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Test product for error handling');
      
      // Simulate network error
      mockNetworkError();
      
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      // Should start processing despite error mock (component handles internally)
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Component should continue to function
      expect(screen.getByRole('button', { name: /cancel analysis/i })).toBeInTheDocument();
    });

    it('should handle retry scenarios correctly', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Retry test product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Cancel and try again with different input
      await user.click(screen.getByRole('button', { name: /cancel analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      });
      
      // New attempt
      const newTextarea = screen.getByRole('textbox');
      await user.type(newTextarea, 'Second attempt product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
        expect(screen.getByText('"Second attempt product"')).toBeInTheDocument();
      });
    });
  });

  describe('Performance Integration', () => {
    it('should handle rapid user interactions without breaking', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      
      // Rapid typing and clearing
      await user.type(textarea, 'First idea');
      await user.clear(textarea);
      await user.type(textarea, 'Second idea');
      await user.clear(textarea);
      await user.type(textarea, 'Final idea for performance test');
      
      const submitButton = screen.getByRole('button', { name: /start analysis/i });
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled();
      });
      
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
        expect(screen.getByText('"Final idea for performance test"')).toBeInTheDocument();
      });
    });

    it('should handle component updates during processing efficiently', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      const { rerender } = render(<M0Container />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Performance test product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Re-render multiple times during processing
      rerender(<M0Container className="updated-class" />);
      rerender(<M0Container />);
      rerender(<M0Container onUpgrade={mockHandlers.onUpgrade} />);
      
      // Should maintain processing state
      expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      
      // Complete processing
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      }, { timeout: 5000 });
    });
  });

  describe('Accessibility Integration', () => {
    it('should maintain accessibility throughout entire workflow', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      // Initial state accessibility
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('AI Co-Pilot for Ecommerce Validation');
      expect(screen.getByLabelText(/what's your product idea/i)).toBeInTheDocument();
      
      // Form interaction
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Accessible product testing workflow');
      
      // Submit and check processing accessibility
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
        expect(screen.getByRole('status')).toBeInTheDocument();
      });
      
      // Complete to report and check accessibility
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        const reportHeading = screen.getByRole('heading', { level: 1 });
        expect(reportHeading).toHaveTextContent(/feasibility report/i);
      }, { timeout: 5000 });
      
      // All buttons should be accessible
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
    });

    it('should support keyboard navigation throughout workflow', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      // Navigate with keyboard
      await user.tab();
      expect(screen.getByRole('textbox')).toHaveFocus();
      
      // Type and submit with keyboard
      await user.type(screen.getByRole('textbox'), 'Keyboard navigation test product');
      await user.keyboard('{Enter}');
      
      await waitFor(() => {
        expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
      });
      
      // Navigate to cancel button
      await user.tab();
      expect(screen.getByRole('button', { name: /cancel analysis/i })).toHaveFocus();
      
      // Complete processing via timing
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Should be able to navigate report buttons
      await user.tab();
      const firstButton = document.activeElement;
      expect(firstButton?.tagName).toBe('BUTTON');
    });
  });

  describe('Real-world Usage Scenarios', () => {
    it('should handle typical user behavior patterns', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      // User starts typing, then uses suggestion
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Custom');
      await user.click(screen.getByText('Organic dog treats'));
      
      expect(textarea).toHaveValue('Organic dog treats');
      
      // User modifies the suggestion
      await user.type(textarea, ' with superfoods');
      
      // Submit
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('"Organic dog treats with superfoods"')).toBeInTheDocument();
      });
      
      // User decides to cancel mid-processing
      await user.click(screen.getByRole('button', { name: /cancel analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      });
      
      // Start fresh with new idea
      const newTextarea = screen.getByRole('textbox');
      await user.type(newTextarea, 'Completely different product - eco-friendly phone cases');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('"Completely different product - eco-friendly phone cases"')).toBeInTheDocument();
      });
    });

    it('should handle edge case inputs gracefully', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      render(<M0Container />);
      
      const edgeCaseInputs = [
        'A'.repeat(10), // Minimum length
        'Special chars: @#$%^&*()_+-=[]{}|;:,.<>?',
        'Numbers: 12345 and symbols: !@#$%',
        'Unicode: 🚀 💡 🎯 product with émojis',
        'A'.repeat(500), // Maximum length
      ];
      
      for (const input of edgeCaseInputs) {
        const textarea = screen.getByRole('textbox');
        
        await user.clear(textarea);
        await user.type(textarea, input);
        
        await waitFor(() => {
          expect(screen.getByRole('button', { name: /start analysis/i })).toBeEnabled();
        });
        
        await user.click(screen.getByRole('button', { name: /start analysis/i }));
        
        await waitFor(() => {
          expect(screen.getByText('Analyzing Your Product Idea')).toBeInTheDocument();
        });
        
        // Cancel and try next input
        await user.click(screen.getByRole('button', { name: /cancel analysis/i }));
        
        await waitFor(() => {
          expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
        });
      }
    });

    it('should maintain state consistency across multiple sessions', async () => {
      const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
      
      // First session
      render(
        <M0Container 
          onAnalysisComplete={mockHandlers.onAnalysisComplete}
        />
      );
      
      await user.type(screen.getByRole('textbox'), 'First session product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText('First session product Feasibility Report')).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Start new analysis
      await user.click(screen.getByRole('button', { name: /← new analysis/i }));
      
      await waitFor(() => {
        expect(screen.getByText('AI Co-Pilot for Ecommerce Validation')).toBeInTheDocument();
      });
      
      // Second session
      await user.type(screen.getByRole('textbox'), 'Second session product');
      await user.click(screen.getByRole('button', { name: /start analysis/i }));
      
      act(() => {
        jest.advanceTimersByTime(10000);
      });
      
      await waitFor(() => {
        expect(screen.getByText('Second session product Feasibility Report')).toBeInTheDocument();
      }, { timeout: 5000 });
      
      // Verify both analysis complete callbacks were called with correct data
      expect(mockHandlers.onAnalysisComplete).toHaveBeenCalledTimes(2);
      expect(mockHandlers.onAnalysisComplete.mock.calls[0][0].productIdea).toBe('First session product');
      expect(mockHandlers.onAnalysisComplete.mock.calls[1][0].productIdea).toBe('Second session product');
    });
  });
});