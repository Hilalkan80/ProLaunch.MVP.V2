import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { M0Container } from '../../src/components/m0/M0Container';
import { TestWrapper, measurePerformance, mockTimers, simulateSlowNetwork } from '../utils/TestWrapper';

// Performance benchmarks (in milliseconds)
const PERFORMANCE_BENCHMARKS = {
  COMPONENT_MOUNT: 1000,
  FORM_INTERACTION: 100,
  STATE_TRANSITION: 500,
  ANIMATION_DURATION: 2000,
  API_RESPONSE_TIMEOUT: 30000,
  MEMORY_LEAK_THRESHOLD: 1000000 // bytes
};

describe('M0 Performance Tests', () => {
  let mockFetch: jest.Mock;
  let performanceObserver: PerformanceObserver;
  let performanceEntries: PerformanceEntry[] = [];

  beforeEach(() => {
    jest.clearAllMocks();
    performanceEntries = [];
    
    // Setup performance observer
    if ('PerformanceObserver' in window) {
      performanceObserver = new PerformanceObserver((list) => {
        performanceEntries.push(...list.getEntries());
      });
      performanceObserver.observe({ entryTypes: ['measure', 'navigation', 'paint'] });
    }

    // Mock fetch with reasonable response time
    mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        data: {
          productIdea: 'Performance Test Product',
          viabilityScore: 75,
          marketSize: '$2.1B',
          growthRate: '15% YoY'
        }
      })
    });
    global.fetch = mockFetch;
  });

  afterEach(() => {
    if (performanceObserver) {
      performanceObserver.disconnect();
    }
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  describe('Component Mount Performance', () => {
    test('mounts within acceptable time', async () => {
      const duration = await measurePerformance('M0Container Mount', async () => {
        render(
          <TestWrapper>
            <M0Container />
          </TestWrapper>
        );
        await waitFor(() => {
          expect(screen.getByTestId('m0-container')).toBeInTheDocument();
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.COMPONENT_MOUNT);
    });

    test('renders all components efficiently on initial load', async () => {
      const startTime = performance.now();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Wait for all components to be rendered
      await waitFor(() => {
        expect(screen.getByTestId('input-state')).toBeInTheDocument();
        expect(screen.getByTestId('product-idea-form')).toBeInTheDocument();
        expect(screen.getByTestId('hero-section')).toBeInTheDocument();
        expect(screen.getByTestId('social-proof')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      expect(renderTime).toBeLessThan(PERFORMANCE_BENCHMARKS.COMPONENT_MOUNT);
    });

    test('handles multiple rapid mounts efficiently', async () => {
      const mountTimes: number[] = [];

      for (let i = 0; i < 5; i++) {
        const duration = await measurePerformance(`Mount ${i}`, async () => {
          const { unmount } = render(
            <TestWrapper>
              <M0Container />
            </TestWrapper>
          );
          
          await waitFor(() => {
            expect(screen.getByTestId('m0-container')).toBeInTheDocument();
          });
          
          unmount();
        });
        
        mountTimes.push(duration);
      }

      const averageTime = mountTimes.reduce((a, b) => a + b, 0) / mountTimes.length;
      expect(averageTime).toBeLessThan(PERFORMANCE_BENCHMARKS.COMPONENT_MOUNT);

      // Ensure performance doesn't degrade with repeated mounts
      const lastMount = mountTimes[mountTimes.length - 1];
      const firstMount = mountTimes[0];
      expect(lastMount).toBeLessThan(firstMount * 1.5); // No more than 50% slower
    });
  });

  describe('Form Interaction Performance', () => {
    test('textarea input response time', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      const testText = 'Performance testing input for measuring response times';

      const duration = await measurePerformance('Textarea Input', async () => {
        await user.type(textarea, testText);
      });

      // Should be responsive (less than 100ms per character)
      const averagePerChar = duration / testText.length;
      expect(averagePerChar).toBeLessThan(PERFORMANCE_BENCHMARKS.FORM_INTERACTION);
    });

    test('character counter updates efficiently', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      const counter = screen.getByTestId('character-counter');

      const duration = await measurePerformance('Character Counter Updates', async () => {
        const longText = 'A'.repeat(200);
        await user.type(textarea, longText);
        
        await waitFor(() => {
          expect(counter).toHaveTextContent('200/500');
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.FORM_INTERACTION * 2);
    });

    test('form validation performance under load', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      const validationStartTime = performance.now();

      // Test multiple validation scenarios rapidly
      const validationTests = [
        '',                    // Empty
        'short',              // Too short  
        'A'.repeat(501),      // Too long
        'Valid input text'    // Valid
      ];

      for (const testInput of validationTests) {
        await user.clear(textarea);
        await user.type(textarea, testInput);
        
        // Wait for validation to complete
        await waitFor(() => {
          const submitButton = screen.getByTestId('submit-button');
          // Button state should reflect validation result
          if (testInput === 'Valid input text') {
            expect(submitButton).toBeEnabled();
          } else {
            expect(submitButton).toBeDisabled();
          }
        });
      }

      const validationEndTime = performance.now();
      const totalValidationTime = validationEndTime - validationStartTime;

      expect(totalValidationTime).toBeLessThan(PERFORMANCE_BENCHMARKS.FORM_INTERACTION * 10);
    });
  });

  describe('State Transition Performance', () => {
    test('input to processing state transition', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'State transition test');

      const duration = await measurePerformance('State Transition to Processing', async () => {
        await user.click(screen.getByTestId('submit-button'));
        
        await waitFor(() => {
          expect(screen.getByTestId('processing-state')).toBeInTheDocument();
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.STATE_TRANSITION);
    });

    test('processing to success state transition', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Success transition test');
      await user.click(screen.getByTestId('submit-button'));

      // Wait for processing state
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      const transitionStart = performance.now();
      
      // Wait for success state
      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 30000 });

      const transitionEnd = performance.now();
      const processingDuration = transitionEnd - transitionStart;

      // Processing should complete within reasonable time
      expect(processingDuration).toBeLessThan(PERFORMANCE_BENCHMARKS.API_RESPONSE_TIMEOUT);
    });

    test('error recovery performance', async () => {
      const user = userEvent.setup();
      
      // Mock initial error
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Error recovery test');
      await user.click(screen.getByTestId('submit-button'));

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByTestId('error-state')).toBeInTheDocument();
      });

      // Reset mock to success
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { productIdea: 'Recovery test' }
        })
      });

      const duration = await measurePerformance('Error Recovery', async () => {
        await user.click(screen.getByTestId('retry-button'));
        
        await waitFor(() => {
          expect(screen.getByTestId('processing-state')).toBeInTheDocument();
        });
      });

      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.STATE_TRANSITION);
    });
  });

  describe('Animation Performance', () => {
    test('fade-in animations complete within expected time', async () => {
      const { mockTimer } = mockTimers();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const fadeInElement = screen.getByTestId('input-state');
      expect(fadeInElement).toBeInTheDocument();

      // Check that animations don't block the main thread
      const startTime = performance.now();
      
      // Fast-forward through animation
      mockTimer.advanceTime(1000);
      
      const endTime = performance.now();
      const executionTime = endTime - startTime;

      expect(executionTime).toBeLessThan(100); // Should be very fast when mocked

      mockTimer.cleanup();
    });

    test('processing step animations perform well', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Animation performance test');
      await user.click(screen.getByTestId('submit-button'));

      const animationStart = performance.now();
      
      await waitFor(() => {
        expect(screen.getByTestId('processing-view')).toBeInTheDocument();
        expect(screen.getByTestId('current-step-highlight')).toBeInTheDocument();
      });

      const animationEnd = performance.now();
      const animationDuration = animationEnd - animationStart;

      expect(animationDuration).toBeLessThan(PERFORMANCE_BENCHMARKS.ANIMATION_DURATION);
    });
  });

  describe('Network Performance', () => {
    test('handles slow network gracefully', async () => {
      const user = userEvent.setup();
      const cleanupSlowNetwork = simulateSlowNetwork(5000); // 5 second delay

      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Slow network test');
      
      const requestStart = performance.now();
      await user.click(screen.getByTestId('submit-button'));

      // Should show loading state immediately
      expect(screen.getByTestId('submit-button')).toHaveTextContent('Analyzing...');

      // Wait for processing state (should appear quickly despite slow network)
      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      const stateChangeTime = performance.now() - requestStart;
      expect(stateChangeTime).toBeLessThan(PERFORMANCE_BENCHMARKS.STATE_TRANSITION);

      cleanupSlowNetwork();
    });

    test('concurrent request handling', async () => {
      const user = userEvent.setup();
      let requestCount = 0;
      
      mockFetch.mockImplementation(() => {
        requestCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: { productIdea: `Request ${requestCount}` }
          })
        });
      });

      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Simulate rapid form submissions (edge case)
      await user.type(screen.getByTestId('product-idea-textarea'), 'Concurrent request test');
      
      // Multiple rapid clicks should be handled gracefully
      const submitButton = screen.getByTestId('submit-button');
      await user.click(submitButton);
      await user.click(submitButton); // Second click should be ignored

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Should only have made one request despite multiple clicks
      expect(requestCount).toBe(1);
    });
  });

  describe('Memory Performance', () => {
    test('component cleanup prevents memory leaks', async () => {
      const user = userEvent.setup();
      const initialMemory = performance.memory?.usedJSHeapSize || 0;

      // Mount and unmount multiple times
      for (let i = 0; i < 10; i++) {
        const { unmount } = render(
          <TestWrapper>
            <M0Container />
          </TestWrapper>
        );

        await user.type(screen.getByTestId('product-idea-textarea'), `Memory test ${i}`);
        unmount();
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

      const finalMemory = performance.memory?.usedJSHeapSize || 0;
      const memoryIncrease = finalMemory - initialMemory;

      // Memory increase should be reasonable (less than 1MB for 10 mounts)
      expect(memoryIncrease).toBeLessThan(PERFORMANCE_BENCHMARKS.MEMORY_LEAK_THRESHOLD);
    });

    test('event listener cleanup', async () => {
      let listenerCount = 0;
      const originalAddEventListener = window.addEventListener;
      const originalRemoveEventListener = window.removeEventListener;

      window.addEventListener = jest.fn((...args) => {
        listenerCount++;
        return originalAddEventListener.apply(window, args);
      });

      window.removeEventListener = jest.fn((...args) => {
        listenerCount--;
        return originalRemoveEventListener.apply(window, args);
      });

      const { unmount } = render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      unmount();

      // Event listeners should be cleaned up
      expect(listenerCount).toBeLessThanOrEqual(0);

      // Restore original functions
      window.addEventListener = originalAddEventListener;
      window.removeEventListener = originalRemoveEventListener;
    });
  });

  describe('Stress Testing', () => {
    test('handles large input efficiently', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const largeInput = 'A'.repeat(500); // Maximum allowed length
      const textarea = screen.getByTestId('product-idea-textarea');

      const duration = await measurePerformance('Large Input Handling', async () => {
        await user.type(textarea, largeInput);
      });

      // Should handle large input efficiently
      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.FORM_INTERACTION * 5);
    });

    test('rapid state changes performance', async () => {
      const user = userEvent.setup();
      const { mockTimer } = mockTimers();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const textarea = screen.getByTestId('product-idea-textarea');
      const clearButton = screen.getByTestId('clear-button');

      const duration = await measurePerformance('Rapid State Changes', async () => {
        // Rapid form interactions
        for (let i = 0; i < 20; i++) {
          await user.type(textarea, `Test ${i}`);
          mockTimer.advanceTime(50);
          await user.click(clearButton);
          mockTimer.advanceTime(50);
        }
      });

      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.FORM_INTERACTION * 20);

      mockTimer.cleanup();
    });

    test('component performance under DOM stress', async () => {
      const user = userEvent.setup();
      
      // Add many sibling components to stress the DOM
      const StressTest = () => (
        <TestWrapper>
          <div>
            {Array.from({ length: 100 }, (_, i) => (
              <div key={i}>Sibling component {i}</div>
            ))}
            <M0Container />
          </div>
        </TestWrapper>
      );

      const duration = await measurePerformance('DOM Stress Test', async () => {
        render(<StressTest />);
        
        await waitFor(() => {
          expect(screen.getByTestId('m0-container')).toBeInTheDocument();
        });

        await user.type(screen.getByTestId('product-idea-textarea'), 'DOM stress test');
      });

      // Should still perform reasonably well under DOM stress
      expect(duration).toBeLessThan(PERFORMANCE_BENCHMARKS.COMPONENT_MOUNT * 2);
    });
  });

  describe('Performance Monitoring', () => {
    test('tracks performance metrics', async () => {
      if (!('PerformanceObserver' in window)) {
        console.warn('PerformanceObserver not available, skipping performance metrics test');
        return;
      }

      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Performance monitoring test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('processing-state')).toBeInTheDocument();
      });

      // Check that we collected some performance entries
      expect(performanceEntries.length).toBeGreaterThan(0);
    });

    test('performance regression detection', async () => {
      const benchmarkResults: number[] = [];
      
      // Run the same test multiple times to detect regressions
      for (let i = 0; i < 3; i++) {
        const duration = await measurePerformance(`Regression Test ${i}`, async () => {
          const { unmount } = render(
            <TestWrapper>
              <M0Container />
            </TestWrapper>
          );
          
          await waitFor(() => {
            expect(screen.getByTestId('m0-container')).toBeInTheDocument();
          });
          
          unmount();
        });
        
        benchmarkResults.push(duration);
      }

      const averageTime = benchmarkResults.reduce((a, b) => a + b, 0) / benchmarkResults.length;
      const maxTime = Math.max(...benchmarkResults);
      const minTime = Math.min(...benchmarkResults);
      
      // Results should be consistent (max time should not be more than 2x min time)
      expect(maxTime).toBeLessThan(minTime * 2);
      
      // Average time should be within acceptable limits
      expect(averageTime).toBeLessThan(PERFORMANCE_BENCHMARKS.COMPONENT_MOUNT);
    });
  });
});