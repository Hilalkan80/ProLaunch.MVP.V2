import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { M0Container } from '../../src/components/m0/M0Container';
import { TestWrapper } from '../utils/TestWrapper';

// Mock API calls
const mockAnalysisComplete = jest.fn();
const mockUpgrade = jest.fn();
const mockStartNextStep = jest.fn();

// Mock fetch for API calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('M0 Component Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        data: {
          productIdea: 'Test Product',
          viabilityScore: 75,
          marketSize: '$1.5B',
          growthRate: '12% YoY'
        }
      })
    });
  });

  const renderM0Container = (props = {}) => {
    return render(
      <TestWrapper>
        <M0Container
          onAnalysisComplete={mockAnalysisComplete}
          onUpgrade={mockUpgrade}
          onStartNextStep={mockStartNextStep}
          {...props}
        />
      </TestWrapper>
    );
  };

  describe('End-to-End User Flows', () => {
    test('completes full analysis flow from input to results', async () => {
      const user = userEvent.setup();
      renderM0Container();

      // Initial state verification
      expect(screen.getByTestId('input-state')).toBeInTheDocument();
      expect(screen.getByTestId('hero-title')).toHaveTextContent('AI Co-Pilot for Ecommerce Validation');

      // Fill in product idea
      const textarea = screen.getByTestId('product-idea-textarea');
      await user.type(textarea, 'Innovative eco-friendly water bottles with built-in filtration system');

      // Verify form validation
      expect(screen.getByTestId('submit-button')).toBeEnabled();
      expect(screen.getByTestId('character-counter')).toHaveTextContent('/500');

      // Submit form
      await user.click(screen.getByTestId('submit-button'));

      // Verify processing state
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      expect(screen.getByTestId('processing-title')).toHaveTextContent('Analyzing Your Product Idea');
      expect(screen.getByTestId('product-idea-display')).toHaveTextContent('Innovative eco-friendly water bottles');

      // Wait for success state (mocked processing completes quickly)
      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Verify success state components
      expect(screen.getByTestId('feasibility-report')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score')).toBeInTheDocument();
      
      // Verify callback was called
      expect(mockAnalysisComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          productIdea: expect.stringContaining('Innovative eco-friendly water bottles')
        })
      );
    });

    test('handles suggestion chip workflow', async () => {
      const user = userEvent.setup();
      renderM0Container();

      // Click on a suggestion chip
      const organicTreatsChip = screen.getByTestId('suggestion-chip-organic-dog-treats');
      await user.click(organicTreatsChip);

      // Verify textarea is populated
      const textarea = screen.getByTestId('product-idea-textarea');
      expect(textarea).toHaveValue('Organic dog treats');

      // Submit should now be enabled
      expect(screen.getByTestId('submit-button')).toBeEnabled();

      // Submit and verify processing starts
      await user.click(screen.getByTestId('submit-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });

    test('handles start over functionality', async () => {
      const user = userEvent.setup();
      renderM0Container();

      // Complete a full flow first
      const textarea = screen.getByTestId('product-idea-textarea');
      await user.type(textarea, 'Test product for start over functionality');
      await user.click(screen.getByTestId('submit-button'));

      // Wait for success state
      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Click start over
      const startOverButton = screen.getByTestId('new-analysis-button');
      await user.click(startOverButton);

      // Should return to initial state
      await waitFor(() => {
        expect(screen.getByTestId('input-state')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('product-idea-textarea')).toHaveValue('');
    });
  });

  describe('Component Interactions', () => {
    test('form validation works correctly', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const textarea = screen.getByTestId('product-idea-textarea');
      const submitButton = screen.getByTestId('submit-button');

      // Test empty state
      expect(submitButton).toBeDisabled();

      // Test too short input
      await user.type(textarea, 'short');
      await waitFor(() => {
        expect(screen.getByTestId('product-idea-error')).toHaveTextContent('at least 10 characters');
      });
      expect(submitButton).toBeDisabled();

      // Test valid input
      await user.clear(textarea);
      await user.type(textarea, 'This is a valid product idea description that meets the minimum requirements');
      
      await waitFor(() => {
        expect(screen.queryByTestId('product-idea-error')).not.toBeInTheDocument();
      });
      expect(submitButton).toBeEnabled();

      // Test maximum length
      const longText = 'a'.repeat(501);
      await user.clear(textarea);
      await user.type(textarea, longText);
      
      await waitFor(() => {
        expect(screen.getByTestId('product-idea-error')).toHaveTextContent('under 500 characters');
      });
      expect(submitButton).toBeDisabled();
    });

    test('clear button functionality', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const textarea = screen.getByTestId('product-idea-textarea');
      const clearButton = screen.getByTestId('clear-button');

      // Initially disabled
      expect(clearButton).toBeDisabled();

      // Type something
      await user.type(textarea, 'Some text to clear');
      expect(clearButton).toBeEnabled();

      // Click clear
      await user.click(clearButton);
      expect(textarea).toHaveValue('');
      expect(clearButton).toBeDisabled();
    });

    test('character counter updates correctly', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const textarea = screen.getByTestId('product-idea-textarea');
      const counter = screen.getByTestId('character-counter');

      expect(counter).toHaveTextContent('0/500');

      const testText = 'Testing character counter functionality';
      await user.type(textarea, testText);

      await waitFor(() => {
        expect(counter).toHaveTextContent(`${testText.length}/500`);
      });
    });

    test('keyboard shortcuts work correctly', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const textarea = screen.getByTestId('product-idea-textarea');
      
      // Fill with valid input
      await user.type(textarea, 'Valid product idea for testing keyboard shortcuts and submission');

      // Press Enter to submit
      await user.type(textarea, '{Enter}');
      
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });

    test('processing steps display correctly', async () => {
      const user = userEvent.setup();
      renderM0Container();

      // Start processing
      const textarea = screen.getByTestId('product-idea-textarea');
      await user.type(textarea, 'Test product for processing step verification');
      await user.click(screen.getByTestId('submit-button'));

      // Wait for processing view
      await waitFor(() => {
        expect(screen.getByTestId('processing-view')).toBeInTheDocument();
      });

      // Verify processing components
      expect(screen.getByTestId('processing-header')).toBeInTheDocument();
      expect(screen.getByTestId('overall-progress')).toBeInTheDocument();
      expect(screen.getByTestId('current-step-highlight')).toBeInTheDocument();
      expect(screen.getByTestId('steps-list')).toBeInTheDocument();

      // Verify individual steps
      const expectedSteps = [
        'market-research',
        'competitor-analysis', 
        'pricing-analysis',
        'demand-validation',
        'risk-assessment',
        'viability-scoring'
      ];

      expectedSteps.forEach(stepId => {
        expect(screen.getByTestId(`processing-step-${stepId}`)).toBeInTheDocument();
      });
    });
  });

  describe('State Management', () => {
    test('maintains state during processing', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const productIdea = 'State management test product with longer description';
      
      // Submit form
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      // Verify state is maintained during processing
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Product idea should still be displayed
      const displayElement = screen.getByTestId('product-idea-display');
      expect(displayElement).toHaveTextContent(productIdea.substring(0, 60));
    });

    test('handles error state transitions', async () => {
      const user = userEvent.setup();
      
      // Mock API error
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Error test product');
      await user.click(screen.getByTestId('submit-button'));

      // Should show error state
      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
      }, { timeout: 5000 });

      // Test retry functionality
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { productIdea: 'Retry test' }
        })
      });

      const retryButton = screen.getByTestId('retry-button');
      await user.click(retryButton);

      // Should go back to processing
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });
  });

  describe('API Integration', () => {
    test('handles successful API responses', async () => {
      const user = userEvent.setup();
      const mockData = {
        productIdea: 'API success test',
        viabilityScore: 85,
        marketSize: '$3.2B',
        growthRate: '18% YoY',
        insights: [
          { type: 'positive', text: 'Strong market potential' },
          { type: 'warning', text: 'High competition expected' }
        ]
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockData
        })
      });

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), mockData.productIdea);
      await user.click(screen.getByTestId('submit-button'));

      // Wait for success state
      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Verify mock data is displayed
      expect(screen.getByTestId('viability-score')).toHaveTextContent('85');
    });

    test('handles API error responses', async () => {
      const user = userEvent.setup();
      
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.resolve({
          success: false,
          error: 'Internal server error'
        })
      });

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Server error test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
      }, { timeout: 5000 });
    });

    test('handles network timeout', async () => {
      const user = userEvent.setup();
      
      // Mock timeout
      mockFetch.mockImplementationOnce(() => 
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout')), 100)
        )
      );

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Timeout test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('network-error-state')).toBeInTheDocument();
      }, { timeout: 5000 });
    });
  });

  describe('Loading States', () => {
    test('shows loading states during form submission', async () => {
      const user = userEvent.setup();
      
      // Mock delayed response
      let resolvePromise: (value: any) => void;
      const delayedPromise = new Promise(resolve => {
        resolvePromise = resolve;
      });

      mockFetch.mockReturnValueOnce(delayedPromise);

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Loading state test');
      await user.click(screen.getByTestId('submit-button'));

      // Verify loading state
      expect(screen.getByTestId('submit-button')).toHaveTextContent('Analyzing...');
      expect(screen.getByTestId('submit-button')).toBeDisabled();
      expect(screen.getByTestId('product-idea-textarea')).toBeDisabled();

      // Resolve the promise
      resolvePromise!({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { productIdea: 'Test' }
        })
      });

      // Wait for processing state
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });

    test('shows processing indicators', async () => {
      const user = userEvent.setup();
      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Processing indicators test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Verify processing indicators
      expect(screen.getByTestId('processing-loader')).toBeInTheDocument();
      expect(screen.getByTestId('overall-progress')).toBeInTheDocument();
      expect(screen.getByTestId('time-elapsed')).toBeInTheDocument();
    });
  });

  describe('Error Scenarios', () => {
    test('handles invalid JSON responses', async () => {
      const user = userEvent.setup();
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON'))
      });

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Invalid JSON test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
      });
    });

    test('handles missing required data', async () => {
      const user = userEvent.setup();
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: {} // Missing required fields
        })
      });

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Missing data test');
      await user.click(screen.getByTestId('submit-button'));

      // Should handle gracefully and show success state with default values
      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    test('handles special characters in input', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const specialText = '🚀 Émojis & special chars! @#$%^&*()_+{}|:"<>?[]\\;\',./';
      await user.type(screen.getByTestId('product-idea-textarea'), specialText);

      expect(screen.getByTestId('submit-button')).toBeEnabled();
      
      await user.click(screen.getByTestId('submit-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });
    });

    test('handles maximum length input', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const maxLengthText = 'A'.repeat(500);
      await user.type(screen.getByTestId('product-idea-textarea'), maxLengthText);

      expect(screen.getByTestId('character-counter')).toHaveTextContent('500/500');
      expect(screen.getByTestId('submit-button')).toBeEnabled();
    });

    test('handles rapid form interactions', async () => {
      const user = userEvent.setup();
      renderM0Container();

      const textarea = screen.getByTestId('product-idea-textarea');
      const clearButton = screen.getByTestId('clear-button');

      // Rapid typing and clearing
      for (let i = 0; i < 3; i++) {
        await user.type(textarea, `Test input ${i}`);
        await user.click(clearButton);
      }

      // Final input should work normally
      await user.type(textarea, 'Final test input after rapid interactions');
      expect(screen.getByTestId('submit-button')).toBeEnabled();
    });
  });

  describe('Callback Functions', () => {
    test('calls onAnalysisComplete with correct data', async () => {
      const user = userEvent.setup();
      const testData = {
        productIdea: 'Callback test product',
        viabilityScore: 90,
        marketSize: '$5B'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: testData
        })
      });

      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), testData.productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockAnalysisComplete).toHaveBeenCalledWith(
          expect.objectContaining(testData)
        );
      }, { timeout: 10000 });
    });

    test('calls onUpgrade when upgrade is triggered', async () => {
      const user = userEvent.setup();
      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Upgrade test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Find and click upgrade button if present
      const upgradeButton = screen.queryByTestId('upgrade-button');
      if (upgradeButton) {
        await user.click(upgradeButton);
        expect(mockUpgrade).toHaveBeenCalled();
      }
    });

    test('calls onStartNextStep when next step is initiated', async () => {
      const user = userEvent.setup();
      renderM0Container();

      await user.type(screen.getByTestId('product-idea-textarea'), 'Next step test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Find and click next step button if present
      const nextStepButton = screen.queryByTestId('next-step-button');
      if (nextStepButton) {
        await user.click(nextStepButton);
        expect(mockStartNextStep).toHaveBeenCalledWith(expect.any(String));
      }
    });
  });
});