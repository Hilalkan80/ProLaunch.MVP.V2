import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FeasibilityReportData } from '../FeasibilityReport';

/**
 * Custom render function that includes all necessary providers
 */
const AllProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return (
    <ChakraProvider>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ChakraProvider>
  );
};

const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllProviders, ...options });

export * from '@testing-library/react';
export { customRender as render };

/**
 * Mock data factories for M0 components
 */
export const createMockProcessingStep = (overrides = {}) => ({
  id: 'test-step',
  label: 'Test Step',
  description: 'Test step description',
  status: 'pending' as const,
  duration: 10,
  ...overrides,
});

export const createMockProcessingSteps = (count = 3) => {
  return Array.from({ length: count }, (_, index) => 
    createMockProcessingStep({
      id: `step-${index + 1}`,
      label: `Step ${index + 1}`,
      description: `Description for step ${index + 1}`,
    })
  );
};

export const createMockCompetitorData = (overrides = {}) => ({
  name: 'Test Competitor',
  priceRange: '$10-15/lb',
  rating: 4.2,
  reviewCount: 500,
  marketPosition: 'premium' as const,
  ...overrides,
});

export const createMockMarketInsight = (overrides = {}) => ({
  type: 'positive' as const,
  text: 'Strong market demand with growing trends',
  ...overrides,
});

export const createMockNextStep = (overrides = {}) => ({
  id: 'test-step',
  title: 'Test Next Step',
  description: 'Test next step description',
  isUnlocked: true,
  order: 1,
  estimatedTime: '15 minutes',
  ...overrides,
});

export const createMockFeasibilityReport = (overrides: Partial<FeasibilityReportData> = {}): FeasibilityReportData => ({
  productIdea: 'Organic dog treats',
  viabilityScore: 78,
  marketSize: '$2.1B',
  growthRate: '15% YoY',
  competitionLevel: 'moderate',
  insights: [
    createMockMarketInsight(),
    createMockMarketInsight({ type: 'warning', text: 'High competition in premium segment' }),
  ],
  competitors: [
    createMockCompetitorData(),
    createMockCompetitorData({ name: 'Another Competitor', rating: 4.5 }),
  ],
  recommendedPriceRange: '$18-24/lb',
  nextSteps: [
    createMockNextStep(),
    createMockNextStep({ id: 'step-2', title: 'Second Step', isUnlocked: false, order: 2 }),
  ],
  generatedAt: new Date('2023-01-01T00:00:00Z'),
  ...overrides,
});

/**
 * Mock form data
 */
export const createMockProductIdeaFormData = (overrides = {}) => ({
  productIdea: 'Test product idea that meets minimum length requirements',
  ...overrides,
});

/**
 * Helper functions for testing
 */
export const waitForElement = (callback: () => any, timeout = 1000) => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const checkElement = () => {
      try {
        const element = callback();
        if (element) {
          resolve(element);
        } else if (Date.now() - startTime > timeout) {
          reject(new Error('Element not found within timeout'));
        } else {
          setTimeout(checkElement, 10);
        }
      } catch (error) {
        if (Date.now() - startTime > timeout) {
          reject(error);
        } else {
          setTimeout(checkElement, 10);
        }
      }
    };
    checkElement();
  });
};

/**
 * Mock event handlers
 */
export const createMockHandlers = () => ({
  onSubmit: jest.fn(),
  onCancel: jest.fn(),
  onRetry: jest.fn(),
  onStartOver: jest.fn(),
  onStartNextStep: jest.fn(),
  onUpgrade: jest.fn(),
  onShare: jest.fn(),
  onExport: jest.fn(),
  onNewAnalysis: jest.fn(),
  onAnalysisComplete: jest.fn(),
  onContactSupport: jest.fn(),
  onDismiss: jest.fn(),
});

/**
 * Accessibility testing helpers
 */
export const axeMatchers = {
  toHaveNoViolations: expect.toHaveNoViolations,
};

/**
 * Animation testing helper - disables CSS animations for consistent testing
 */
export const disableAnimations = () => {
  const style = document.createElement('style');
  style.innerHTML = `
    *,
    *::before,
    *::after {
      animation-duration: 0s !important;
      animation-delay: 0s !important;
      transition-duration: 0s !important;
      transition-delay: 0s !important;
    }
  `;
  document.head.appendChild(style);
  return () => document.head.removeChild(style);
};

/**
 * Viewport testing helpers
 */
export const setViewport = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  });
  
  window.dispatchEvent(new Event('resize'));
};

/**
 * Mock ResizeObserver for testing responsive components
 */
export class MockResizeObserver {
  private callbacks: ResizeObserverCallback[] = [];
  
  constructor(callback: ResizeObserverCallback) {
    this.callbacks.push(callback);
  }
  
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  
  // Helper to trigger resize callbacks in tests
  triggerResize(entries: ResizeObserverEntry[] = []) {
    this.callbacks.forEach(callback => callback(entries, this));
  }
}

/**
 * Form validation helpers
 */
export const getFormValidationErrors = (container: HTMLElement) => {
  return Array.from(container.querySelectorAll('[role="alert"]')).map(
    el => el.textContent
  );
};

export const fillForm = async (getByLabelText: any, data: Record<string, string>) => {
  for (const [label, value] of Object.entries(data)) {
    const field = getByLabelText(new RegExp(label, 'i'));
    if (field) {
      await userEvent.clear(field);
      await userEvent.type(field, value);
    }
  }
};

/**
 * Network simulation helpers
 */
export const mockNetworkError = () => {
  global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
};

export const mockNetworkSuccess = (data: any = {}) => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
};

export const mockNetworkDelay = (delay: number, data: any = {}) => {
  global.fetch = jest.fn().mockImplementation(
    () => new Promise(resolve => 
      setTimeout(() => resolve({
        ok: true,
        json: () => Promise.resolve(data),
        text: () => Promise.resolve(JSON.stringify(data)),
      }), delay)
    )
  );
};