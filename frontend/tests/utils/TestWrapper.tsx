import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, extendTheme } from '@chakra-ui/react';

// Create a minimal theme for testing
const testTheme = extendTheme({
  styles: {
    global: {
      body: {
        bg: 'white',
      },
    },
  },
});

// Create a test query client with disabled retries and caching for predictable tests
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

interface TestWrapperProps {
  children: React.ReactNode;
  queryClient?: QueryClient;
}

export const TestWrapper: React.FC<TestWrapperProps> = ({ 
  children, 
  queryClient = createTestQueryClient() 
}) => {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={testTheme}>
        {children}
      </ChakraProvider>
    </QueryClientProvider>
  );
};

// Custom render function with providers
import { render, RenderOptions } from '@testing-library/react';

interface CustomRenderOptions extends RenderOptions {
  queryClient?: QueryClient;
}

export const renderWithProviders = (
  ui: React.ReactElement,
  options: CustomRenderOptions = {}
) => {
  const { queryClient, ...renderOptions } = options;

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <TestWrapper queryClient={queryClient}>{children}</TestWrapper>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Mock implementations for testing
export const createMockAnalysisData = (overrides = {}) => ({
  productIdea: 'Test Product Idea',
  viabilityScore: 75,
  marketSize: '$2.1B',
  growthRate: '15% YoY',
  competitionLevel: 'moderate',
  insights: [
    {
      type: 'positive',
      text: 'Strong market demand identified'
    },
    {
      type: 'warning', 
      text: 'Competitive landscape requires differentiation'
    }
  ],
  competitors: [
    {
      name: 'Competitor A',
      priceRange: '$15-18/unit',
      rating: 4.2,
      reviewCount: 850,
      marketPosition: 'premium'
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
    }
  ],
  generatedAt: new Date(),
  ...overrides
});

// Test utilities for common operations
export const fillProductIdeaForm = async (
  user: any, 
  productIdea: string = 'Test product idea for automated testing'
) => {
  const textarea = document.querySelector('[data-testid="product-idea-textarea"]') as HTMLTextAreaElement;
  if (textarea) {
    await user.clear(textarea);
    await user.type(textarea, productIdea);
  }
  return textarea;
};

export const submitForm = async (user: any) => {
  const submitButton = document.querySelector('[data-testid="submit-button"]') as HTMLButtonElement;
  if (submitButton && !submitButton.disabled) {
    await user.click(submitButton);
  }
  return submitButton;
};

export const waitForProcessingToComplete = async (timeout = 10000) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const successState = document.querySelector('[data-testid="success-state"]');
    if (successState) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  throw new Error('Processing did not complete within timeout');
};

// Mock timer utilities for testing time-dependent components
export const mockTimers = () => {
  jest.useFakeTimers();
  return {
    advanceTime: (ms: number) => jest.advanceTimersByTime(ms),
    runAllTimers: () => jest.runAllTimers(),
    cleanup: () => jest.useRealTimers()
  };
};

// Network simulation utilities
export const simulateSlowNetwork = (delay: number = 2000) => {
  const originalFetch = global.fetch;
  
  global.fetch = jest.fn((...args) => 
    new Promise(resolve => 
      setTimeout(() => resolve(originalFetch(...args)), delay)
    )
  );
  
  return () => {
    global.fetch = originalFetch;
  };
};

export const simulateNetworkError = () => {
  const originalFetch = global.fetch;
  
  global.fetch = jest.fn(() => 
    Promise.reject(new Error('Network error'))
  );
  
  return () => {
    global.fetch = originalFetch;
  };
};

// Local storage mock utilities
export const mockLocalStorage = () => {
  const store: Record<string, string> = {};
  
  const mockStorage = {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
  };
  
  Object.defineProperty(window, 'localStorage', {
    value: mockStorage,
    writable: true,
  });
  
  return mockStorage;
};

// Clipboard API mock
export const mockClipboard = () => {
  const clipboardData: { [key: string]: string } = {};
  
  const mockClipboard = {
    writeText: jest.fn((text: string) => {
      clipboardData.text = text;
      return Promise.resolve();
    }),
    readText: jest.fn(() => Promise.resolve(clipboardData.text || '')),
  };
  
  Object.defineProperty(navigator, 'clipboard', {
    value: mockClipboard,
    writable: true,
  });
  
  return mockClipboard;
};

// Window API mocks for testing share functionality
export const mockWindowAPIs = () => {
  const originalWindow = { ...window };
  
  // Mock window.open
  Object.defineProperty(window, 'open', {
    value: jest.fn(),
    writable: true,
  });
  
  // Mock URL methods
  Object.defineProperty(window, 'URL', {
    value: {
      createObjectURL: jest.fn(() => 'blob:mock-url'),
      revokeObjectURL: jest.fn(),
    },
    writable: true,
  });
  
  return {
    cleanup: () => {
      Object.assign(window, originalWindow);
    }
  };
};

// Intersection Observer mock for animation testing
export const mockIntersectionObserver = () => {
  const mockIntersectionObserver = jest.fn();
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null,
  });
  
  Object.defineProperty(window, 'IntersectionObserver', {
    value: mockIntersectionObserver,
    writable: true,
  });
  
  Object.defineProperty(global, 'IntersectionObserver', {
    value: mockIntersectionObserver,
    writable: true,
  });
  
  return mockIntersectionObserver;
};

// WebSocket mock for real-time features
export const mockWebSocket = () => {
  const mockWebSocket = jest.fn(() => ({
    send: jest.fn(),
    close: jest.fn(),
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    readyState: WebSocket.OPEN,
  }));
  
  Object.defineProperty(global, 'WebSocket', {
    value: mockWebSocket,
    writable: true,
  });
  
  return mockWebSocket;
};

// Performance measurement utilities
export const measurePerformance = (testName: string, fn: () => Promise<void> | void) => {
  return async () => {
    const start = performance.now();
    await fn();
    const end = performance.now();
    const duration = end - start;
    
    console.log(`Performance test "${testName}": ${duration.toFixed(2)}ms`);
    
    return duration;
  };
};

// Accessibility testing utilities
export const checkAccessibility = async (container: HTMLElement) => {
  // Basic accessibility checks
  const issues: string[] = [];
  
  // Check for missing alt attributes on images
  const images = container.querySelectorAll('img');
  images.forEach((img, index) => {
    if (!img.getAttribute('alt')) {
      issues.push(`Image at index ${index} is missing alt attribute`);
    }
  });
  
  // Check for proper heading hierarchy
  const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
  let previousLevel = 0;
  headings.forEach((heading) => {
    const currentLevel = parseInt(heading.tagName[1]);
    if (currentLevel > previousLevel + 1) {
      issues.push(`Heading level jump from h${previousLevel} to h${currentLevel}`);
    }
    previousLevel = currentLevel;
  });
  
  // Check for form labels
  const inputs = container.querySelectorAll('input, textarea, select');
  inputs.forEach((input, index) => {
    const id = input.getAttribute('id');
    if (id) {
      const label = container.querySelector(`label[for="${id}"]`);
      if (!label) {
        issues.push(`Input at index ${index} is missing associated label`);
      }
    }
  });
  
  return issues;
};

// Export all utilities
export {
  createTestQueryClient,
  testTheme
};