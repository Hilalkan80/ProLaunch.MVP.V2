import { Page, Route } from '@playwright/test';

interface MockFeasibilityData {
  productIdea: string;
  viabilityScore: number;
  marketSize: string;
  growthRate: string;
  competitionLevel?: string;
  insights?: Array<{
    type: 'positive' | 'warning' | 'negative';
    text: string;
  }>;
  competitors?: Array<{
    name: string;
    priceRange: string;
    rating: number;
    reviewCount: number;
    marketPosition: string;
  }>;
  recommendedPriceRange?: string;
  nextSteps?: Array<{
    id: string;
    title: string;
    description: string;
    isUnlocked: boolean;
    order: number;
    estimatedTime?: string;
  }>;
}

export class MockApiHelper {
  private page: Page;
  private routes: Route[] = [];

  constructor(page: Page) {
    this.page = page;
  }

  async setupMocks(): Promise<void> {
    // Mock successful API responses by default
    await this.mockSuccessfulAnalysis();
  }

  async mockSuccessfulAnalysis(customData?: Partial<MockFeasibilityData>): Promise<void> {
    const defaultData: MockFeasibilityData = {
      productIdea: 'Test Product Idea',
      viabilityScore: 78,
      marketSize: '$2.1B',
      growthRate: '15% YoY',
      competitionLevel: 'moderate',
      insights: [
        {
          type: 'positive',
          text: 'Strong market demand with consistent growth'
        },
        {
          type: 'positive',
          text: 'Manageable competition with clear differentiation opportunities'
        },
        {
          type: 'warning',
          text: 'Premium positioning required for profitability'
        }
      ],
      competitors: [
        {
          name: 'Competitor A',
          priceRange: '$15-18/unit',
          rating: 4.2,
          reviewCount: 850,
          marketPosition: 'premium'
        },
        {
          name: 'Competitor B',
          priceRange: '$12-15/unit',
          rating: 4.4,
          reviewCount: 1200,
          marketPosition: 'mid-market'
        }
      ],
      recommendedPriceRange: '$18-24/unit',
      nextSteps: [
        {
          id: 'm1-unit-economics',
          title: 'Analyze Unit Economics (M1)',
          description: 'Deep dive into costs and profit margins',
          isUnlocked: true,
          order: 1,
          estimatedTime: '15 minutes'
        },
        {
          id: 'm2-market-research',
          title: 'Deep Market Research (M2)',
          description: 'Comprehensive competitor and demand analysis',
          isUnlocked: false,
          order: 2
        }
      ]
    };

    const mockData = { ...defaultData, ...customData };

    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: mockData,
          generatedAt: new Date().toISOString()
        })
      });
    });
  }

  async mockProcessingSteps(): Promise<void> {
    await this.page.route('**/api/v1/m0/analyze', async (route) => {
      this.routes.push(route);
      
      // Simulate step-by-step processing
      const steps = [
        { id: 'market-research', duration: 3000 },
        { id: 'competitor-analysis', duration: 4000 },
        { id: 'pricing-analysis', duration: 2000 },
        { id: 'demand-validation', duration: 3000 },
        { id: 'risk-assessment', duration: 2000 },
        { id: 'viability-scoring', duration: 1000 }
      ];

      let completedSteps = 0;
      const processSteps = async () => {
        for (const step of steps) {
          await new Promise(resolve => setTimeout(resolve, step.duration));
          completedSteps++;
          
          // Send progress update (in real app, this might be WebSocket)
          if (completedSteps === steps.length) {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                success: true,
                data: await this.getDefaultMockData(),
                progress: 100
              })
            });
            return;
          }
        }
      };

      processSteps();
    });
  }

  async simulateNetworkError(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      await route.abort('failed');
    });
  }

  async simulateTimeout(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      // Don't fulfill the route, causing a timeout
      await new Promise(resolve => setTimeout(resolve, 30000));
      await route.fulfill({
        status: 408,
        body: 'Request Timeout'
      });
    });
  }

  async simulateProcessingError(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'Processing failed',
          message: 'Unable to analyze product idea due to service error'
        })
      });
    });
  }

  async mockServerError(statusCode: number = 500): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await route.fulfill({
        status: statusCode,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Server error',
          message: 'Internal server error occurred'
        })
      });
    });
  }

  async mockRateLimitError(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        headers: {
          'Retry-After': '60'
        },
        body: JSON.stringify({
          error: 'Too many requests',
          message: 'Rate limit exceeded. Please try again later.'
        })
      });
    });
  }

  async mockInvalidResponse(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{"invalid": "json"' // Invalid JSON
      });
    });
  }

  async mockSlowResponse(delay: number = 5000): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: await this.getDefaultMockData()
        })
      });
    });
  }

  async mockPartialData(): Promise<void> {
    await this.page.route('**/api/v1/m0/**', async (route) => {
      this.routes.push(route);
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            productIdea: 'Partial Data Test',
            viabilityScore: 65,
            marketSize: '$1.2B'
            // Missing other expected fields
          }
        })
      });
    });
  }

  async resetMocks(): Promise<void> {
    // Clear all existing routes
    for (const route of this.routes) {
      try {
        await route.continue();
      } catch {
        // Route might already be handled
      }
    }
    this.routes = [];
    
    // Set up default successful mocks again
    await this.setupMocks();
  }

  private async getDefaultMockData(): Promise<MockFeasibilityData> {
    return {
      productIdea: 'Default Test Product',
      viabilityScore: 78,
      marketSize: '$2.1B',
      growthRate: '15% YoY',
      competitionLevel: 'moderate',
      insights: [
        {
          type: 'positive',
          text: 'Strong market opportunity identified'
        },
        {
          type: 'warning',
          text: 'Competitive landscape requires differentiation'
        }
      ],
      competitors: [
        {
          name: 'Market Leader',
          priceRange: '$20-25/unit',
          rating: 4.3,
          reviewCount: 2500,
          marketPosition: 'premium'
        }
      ],
      recommendedPriceRange: '$22-28/unit',
      nextSteps: [
        {
          id: 'm1-economics',
          title: 'Unit Economics Analysis',
          description: 'Detailed cost and margin analysis',
          isUnlocked: true,
          order: 1,
          estimatedTime: '15 minutes'
        }
      ]
    };
  }

  // Utility methods for test assertions
  async waitForApiCall(timeout: number = 10000): Promise<boolean> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      if (this.routes.length > 0) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return false;
  }

  getApiCallCount(): number {
    return this.routes.length;
  }

  async mockWebSocketConnection(): Promise<void> {
    // Mock WebSocket for real-time updates if needed
    await this.page.addInitScript(() => {
      // Mock WebSocket for processing updates
      class MockWebSocket {
        onopen: ((event: Event) => void) | null = null;
        onmessage: ((event: MessageEvent) => void) | null = null;
        onclose: ((event: CloseEvent) => void) | null = null;
        onerror: ((event: Event) => void) | null = null;
        
        constructor(url: string) {
          setTimeout(() => {
            if (this.onopen) {
              this.onopen(new Event('open'));
            }
            
            // Simulate processing updates
            const updates = [
              { step: 'market-research', status: 'processing', progress: 16 },
              { step: 'market-research', status: 'completed', progress: 16 },
              { step: 'competitor-analysis', status: 'processing', progress: 33 },
              { step: 'competitor-analysis', status: 'completed', progress: 33 },
              // ... more updates
            ];
            
            updates.forEach((update, index) => {
              setTimeout(() => {
                if (this.onmessage) {
                  this.onmessage(new MessageEvent('message', { 
                    data: JSON.stringify(update) 
                  }));
                }
              }, index * 2000);
            });
          }, 100);
        }
        
        send() {}
        close() {}
      }
      
      (window as any).WebSocket = MockWebSocket;
    });
  }
}