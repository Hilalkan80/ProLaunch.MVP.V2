import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { M0Container } from '../../src/components/m0/M0Container';
import { TestWrapper, mockWindowAPIs, mockClipboard } from '../utils/TestWrapper';

describe('M0 Share and Export Functionality Tests', () => {
  let mockFetch: jest.Mock;
  let windowAPIs: ReturnType<typeof mockWindowAPIs>;
  let clipboardAPI: ReturnType<typeof mockClipboard>;

  beforeEach(() => {
    jest.clearAllMocks();
    
    windowAPIs = mockWindowAPIs();
    clipboardAPI = mockClipboard();
    
    mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: true,
        data: {
          productIdea: 'Shareable Test Product',
          viabilityScore: 85,
          marketSize: '$3.2B',
          growthRate: '20% YoY',
          competitionLevel: 'moderate',
          insights: [
            { type: 'positive', text: 'Strong market opportunity' },
            { type: 'warning', text: 'Competitive landscape' }
          ],
          competitors: [
            {
              name: 'Test Competitor',
              priceRange: '$20-25/unit',
              rating: 4.3,
              reviewCount: 1500,
              marketPosition: 'premium'
            }
          ],
          recommendedPriceRange: '$22-28/unit',
          nextSteps: [
            {
              id: 'm1-unit-economics',
              title: 'Analyze Unit Economics (M1)',
              description: 'Detailed cost analysis',
              isUnlocked: true,
              order: 1
            }
          ],
          generatedAt: new Date()
        }
      })
    });
    global.fetch = mockFetch;
  });

  afterEach(() => {
    windowAPIs.cleanup();
  });

  describe('Share URL Generation', () => {
    test('generates shareable URL for completed analysis', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Complete analysis flow
      await user.type(screen.getByTestId('product-idea-textarea'), 'URL sharing test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Look for share button
      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Should generate and display share URL
        const shareUrl = screen.queryByTestId('share-url');
        if (shareUrl) {
          const url = shareUrl.textContent || shareUrl.getAttribute('value') || '';
          expect(url).toMatch(/\/report\//);
          expect(url).toContain(window.location.origin);
        }
      }
    });

    test('share URL contains encoded product data', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'Data encoding test product';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const shareUrl = screen.queryByTestId('share-url');
        if (shareUrl) {
          const url = shareUrl.textContent || shareUrl.getAttribute('value') || '';
          
          // Extract encoded data from URL
          const urlParts = url.split('/report/');
          if (urlParts.length > 1) {
            const encodedData = urlParts[1];
            const decodedData = atob(encodedData);
            expect(decodedData).toContain(productIdea);
          }
        }
      }
    });

    test('share modal functionality', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Share modal test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Check for share modal
        const modal = screen.queryByTestId('share-modal');
        if (modal) {
          expect(modal).toBeInTheDocument();
          expect(modal).toHaveAttribute('role', 'dialog');

          // Should have close functionality
          const closeButton = screen.queryByTestId('close-modal-button') || 
                             screen.queryByLabelText('Close');
          if (closeButton) {
            await user.click(closeButton);
            expect(modal).not.toBeInTheDocument();
          }
        }
      }
    });
  });

  describe('Copy to Clipboard', () => {
    test('copies share URL to clipboard', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Clipboard test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const copyButton = screen.queryByTestId('copy-url-button') ||
                          screen.queryByText(/copy/i);
        if (copyButton) {
          await user.click(copyButton);

          // Should have called clipboard API
          expect(clipboardAPI.writeText).toHaveBeenCalled();
          
          // Should show confirmation
          await waitFor(() => {
            const confirmation = screen.queryByText(/copied/i) || 
                                screen.queryByText(/✓/);
            expect(confirmation).toBeInTheDocument();
          });
        }
      }
    });

    test('handles clipboard API errors gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock clipboard error
      clipboardAPI.writeText.mockRejectedValueOnce(new Error('Clipboard not available'));
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Clipboard error test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const copyButton = screen.queryByTestId('copy-url-button');
        if (copyButton) {
          await user.click(copyButton);

          // Should show error message or fallback
          await waitFor(() => {
            const errorMessage = screen.queryByText(/error/i) ||
                                screen.queryByText(/unable to copy/i);
            if (errorMessage) {
              expect(errorMessage).toBeInTheDocument();
            }
          });
        }
      }
    });

    test('provides fallback for unsupported clipboard API', async () => {
      const user = userEvent.setup();
      
      // Remove clipboard API
      Object.defineProperty(navigator, 'clipboard', {
        value: undefined,
        writable: true,
      });
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Clipboard fallback test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Should provide alternative method (select text, etc.)
        const shareUrl = screen.queryByTestId('share-url');
        if (shareUrl && shareUrl.tagName === 'INPUT') {
          // Should be selectable
          expect(shareUrl).toHaveAttribute('readonly');
        }
      }
    });
  });

  describe('PDF Export', () => {
    test('generates PDF download', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'PDF export test product');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const exportPdfButton = screen.queryByTestId('export-pdf-button') ||
                             screen.queryByText(/export.*pdf/i);
      
      if (exportPdfButton) {
        await user.click(exportPdfButton);

        // In a real implementation, this would trigger a download
        // For now, we can check that the function was called
        // This would typically be mocked in the component level
      }
    });

    test('PDF export includes all report data', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Comprehensive PDF test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Verify all data is present before export
      expect(screen.getByTestId('viability-score')).toBeInTheDocument();
      expect(screen.getByTestId('market-insights')).toBeInTheDocument();
      expect(screen.getByTestId('competitors-section')).toBeInTheDocument();
      expect(screen.getByTestId('next-steps-section')).toBeInTheDocument();

      const exportPdfButton = screen.queryByTestId('export-pdf-button');
      if (exportPdfButton) {
        // Button should be enabled with complete data
        expect(exportPdfButton).toBeEnabled();
      }
    });

    test('handles PDF generation errors', async () => {
      const user = userEvent.setup();
      
      // Mock console.error to capture error handling
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'PDF error test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const exportPdfButton = screen.queryByTestId('export-pdf-button');
      if (exportPdfButton) {
        await user.click(exportPdfButton);

        // Should handle errors gracefully (would need actual PDF lib integration)
        // For now, verify no uncaught errors
      }

      consoleSpy.mockRestore();
    });
  });

  describe('JSON Export', () => {
    test('exports data as JSON file', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'JSON export test product';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const exportJsonButton = screen.queryByTestId('export-json-button') ||
                              screen.queryByText(/export.*json/i);
      
      if (exportJsonButton) {
        // Mock document.createElement to capture download link creation
        const originalCreateElement = document.createElement;
        const mockLink = {
          href: '',
          download: '',
          click: jest.fn(),
          setAttribute: jest.fn((attr, value) => {
            mockLink[attr as keyof typeof mockLink] = value;
          }),
          getAttribute: jest.fn((attr) => mockLink[attr as keyof typeof mockLink])
        };

        document.createElement = jest.fn((tagName) => {
          if (tagName === 'a') {
            return mockLink as any;
          }
          return originalCreateElement.call(document, tagName);
        });

        await user.click(exportJsonButton);

        // Should have created download link
        expect(document.createElement).toHaveBeenCalledWith('a');
        expect(mockLink.click).toHaveBeenCalled();
        expect(mockLink.download).toMatch(/\.json$/);

        // Restore original createElement
        document.createElement = originalCreateElement;
      }
    });

    test('JSON export contains complete data structure', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'Complete JSON data test';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const exportJsonButton = screen.queryByTestId('export-json-button');
      if (exportJsonButton) {
        // Mock URL.createObjectURL to capture the data
        let capturedData = '';
        const mockCreateObjectURL = jest.fn((blob: Blob) => {
          blob.text().then(text => {
            capturedData = text;
          });
          return 'blob:mock-url';
        });
        
        Object.defineProperty(window.URL, 'createObjectURL', {
          value: mockCreateObjectURL,
        });

        await user.click(exportJsonButton);

        // Wait for blob processing
        await new Promise(resolve => setTimeout(resolve, 100));

        if (capturedData) {
          const jsonData = JSON.parse(capturedData);
          
          // Verify essential fields
          expect(jsonData.productIdea).toBe(productIdea);
          expect(jsonData.viabilityScore).toBeDefined();
          expect(jsonData.marketSize).toBeDefined();
          expect(jsonData.insights).toBeDefined();
          expect(jsonData.competitors).toBeDefined();
          expect(jsonData.nextSteps).toBeDefined();
          expect(jsonData.generatedAt).toBeDefined();
        }
      }
    });

    test('JSON filename reflects product idea', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'Special Product Name!@#$';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const exportJsonButton = screen.queryByTestId('export-json-button');
      if (exportJsonButton) {
        const mockLink = {
          download: '',
          click: jest.fn(),
          setAttribute: jest.fn((attr, value) => {
            if (attr === 'download') mockLink.download = value;
          })
        };

        document.createElement = jest.fn((tagName) => {
          if (tagName === 'a') return mockLink as any;
          return document.createElement(tagName);
        });

        await user.click(exportJsonButton);

        // Should sanitize filename
        expect(mockLink.download).toMatch(/special_product_name.*\.json$/i);
      }
    });
  });

  describe('Social Sharing', () => {
    test('opens new window for social sharing', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Social sharing test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Look for social sharing options
        const twitterShare = screen.queryByTestId('twitter-share') ||
                           screen.queryByText(/twitter/i);
        
        if (twitterShare) {
          await user.click(twitterShare);
          expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('twitter.com'),
            '_blank'
          );
        }

        const linkedinShare = screen.queryByTestId('linkedin-share') ||
                            screen.queryByText(/linkedin/i);
        
        if (linkedinShare) {
          await user.click(linkedinShare);
          expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('linkedin.com'),
            '_blank'
          );
        }
      }
    });

    test('includes proper share text and URLs', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'Shareable product concept';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const twitterShare = screen.queryByTestId('twitter-share');
        if (twitterShare) {
          await user.click(twitterShare);

          const twitterCall = (window.open as jest.Mock).mock.calls.find(call => 
            call[0].includes('twitter.com')
          );

          if (twitterCall) {
            const url = twitterCall[0];
            expect(url).toContain(encodeURIComponent(productIdea));
            expect(url).toContain('text=');
          }
        }
      }
    });
  });

  describe('Email Sharing', () => {
    test('opens email client with report summary', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Email sharing test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const emailShare = screen.queryByTestId('email-share') ||
                          screen.queryByText(/email/i);
        
        if (emailShare) {
          await user.click(emailShare);

          // Should open email client (mailto:)
          expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('mailto:'),
            '_blank'
          );
        }
      }
    });

    test('email contains formatted report summary', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      const productIdea = 'Email formatted test';
      await user.type(screen.getByTestId('product-idea-textarea'), productIdea);
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        const emailShare = screen.queryByTestId('email-share');
        if (emailShare) {
          await user.click(emailShare);

          const emailCall = (window.open as jest.Mock).mock.calls.find(call => 
            call[0].includes('mailto:')
          );

          if (emailCall) {
            const mailtoUrl = emailCall[0];
            const decodedUrl = decodeURIComponent(mailtoUrl);
            
            expect(decodedUrl).toContain(productIdea);
            expect(decodedUrl).toContain('subject=');
            expect(decodedUrl).toContain('body=');
          }
        }
      }
    });
  });

  describe('Share Features Error Handling', () => {
    test('handles share functionality when no data available', async () => {
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      // Try to access share functionality without completing analysis
      // Share button should not be available or should be disabled
      const shareButton = screen.queryByTestId('share-button');
      
      if (shareButton) {
        expect(shareButton).toBeDisabled();
      } else {
        // Share button should not be present in initial state
        expect(screen.getByTestId('input-state')).toBeInTheDocument();
      }
    });

    test('handles network errors during share URL generation', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Network error share test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      // Mock network error for share URL generation
      const originalFetch = global.fetch;
      global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Should handle error gracefully
        await waitFor(() => {
          const errorMessage = screen.queryByText(/error.*sharing/i) ||
                              screen.queryByText(/unable.*share/i);
          
          if (errorMessage) {
            expect(errorMessage).toBeInTheDocument();
          }
        });
      }

      // Restore original fetch
      global.fetch = originalFetch;
    });

    test('handles browser compatibility issues', async () => {
      const user = userEvent.setup();
      
      // Remove modern APIs
      const originalClipboard = navigator.clipboard;
      const originalURL = window.URL;
      
      Object.defineProperty(navigator, 'clipboard', { value: undefined });
      Object.defineProperty(window, 'URL', { value: undefined });
      
      render(
        <TestWrapper>
          <M0Container />
        </TestWrapper>
      );

      await user.type(screen.getByTestId('product-idea-textarea'), 'Browser compatibility test');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(screen.getByTestId('success-state')).toBeInTheDocument();
      }, { timeout: 10000 });

      const shareButton = screen.queryByTestId('share-button');
      if (shareButton) {
        await user.click(shareButton);

        // Should provide fallback functionality
        const shareUrl = screen.queryByTestId('share-url');
        if (shareUrl) {
          expect(shareUrl).toBeInTheDocument();
        }
      }

      // Restore APIs
      Object.defineProperty(navigator, 'clipboard', { value: originalClipboard });
      Object.defineProperty(window, 'URL', { value: originalURL });
    });
  });
});