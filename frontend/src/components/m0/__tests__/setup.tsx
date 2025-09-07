import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Configure testing library
configure({ 
  testIdAttribute: 'data-testid',
  asyncUtilTimeout: 5000,
});

// Create user event instance for better typing
export const user = userEvent.setup();

// Global test setup for M0 components
beforeEach(() => {
  // Clear all mocks before each test
  jest.clearAllMocks();
  
  // Reset DOM
  document.body.innerHTML = '';
  
  // Reset localStorage mock
  if (window.localStorage.store) {
    window.localStorage.store = {};
  }
  
  // Reset URL
  window.history.replaceState({}, '', '/');
});

afterEach(() => {
  // Clean up any remaining timers
  jest.useRealTimers();
});

// Mock console methods to avoid noise in tests (but allow explicit calls)
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: any[]) => {
    // Only suppress React warnings and other known harmless messages
    const message = args[0];
    if (
      typeof message === 'string' &&
      (message.includes('Warning:') || 
       message.includes('Not implemented: HTMLCanvasElement.prototype.getContext'))
    ) {
      return;
    }
    originalError(...args);
  };
  
  console.warn = (...args: any[]) => {
    const message = args[0];
    if (
      typeof message === 'string' &&
      message.includes('Warning:')
    ) {
      return;
    }
    originalWarn(...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Extended Jest matchers for M0 testing
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidProductIdea(): R;
      toBeWithinScoreRange(min: number, max: number): R;
    }
  }
}

// Custom matchers
expect.extend({
  toBeValidProductIdea(received: string) {
    const pass = received.length >= 10 && received.length <= 500;
    return {
      message: () => `expected "${received}" to be a valid product idea (10-500 characters)`,
      pass,
    };
  },
  
  toBeWithinScoreRange(received: number, min: number, max: number) {
    const pass = received >= min && received <= max;
    return {
      message: () => `expected ${received} to be within range ${min}-${max}`,
      pass,
    };
  },
});

export default undefined;