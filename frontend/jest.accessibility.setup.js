import 'jest-axe/extend-expect';
import '@testing-library/jest-dom';
import { configure } from '@testing-library/react';

// Configure Testing Library for better accessibility testing
configure({
  testIdAttribute: 'data-testid',
  // Use semantic selectors by default
  getElementError: (message, container) => {
    const error = new Error(
      [
        message,
        '',
        'Tip: Consider using semantic HTML elements and ARIA attributes',
        'instead of data-testid when possible for better accessibility.',
      ].join('\n')
    );
    error.name = 'TestingLibraryElementError';
    error.stack = null;
    return error;
  },
});

// Mock IntersectionObserver for tests that use animations
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  unobserve: jest.fn(),
}));

// Mock ResizeObserver for responsive components
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  unobserve: jest.fn(),
}));

// Mock matchMedia for responsive design testing
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.getComputedStyle for color contrast testing
const originalGetComputedStyle = window.getComputedStyle;
window.getComputedStyle = jest.fn().mockImplementation((element, pseudoElement) => {
  const styles = originalGetComputedStyle(element, pseudoElement);
  return {
    ...styles,
    // Provide default styles for testing
    color: styles.color || 'rgb(0, 0, 0)',
    backgroundColor: styles.backgroundColor || 'rgb(255, 255, 255)',
    fontSize: styles.fontSize || '16px',
    lineHeight: styles.lineHeight || '1.5',
  };
});

// Enhanced console warnings for accessibility issues
const originalWarn = console.warn;
console.warn = (...args) => {
  // Convert accessibility warnings to test failures in CI
  if (process.env.CI && args.some(arg => 
    typeof arg === 'string' && 
    (arg.includes('aria-') || arg.includes('role') || arg.includes('accessibility'))
  )) {
    throw new Error(`Accessibility warning: ${args.join(' ')}`);
  }
  originalWarn(...args);
};

// Mock audio context for components that might use sound
global.AudioContext = jest.fn(() => ({
  createGain: jest.fn(() => ({ gain: { value: 1 } })),
  createOscillator: jest.fn(() => ({
    connect: jest.fn(),
    start: jest.fn(),
    stop: jest.fn(),
  })),
  destination: {},
}));

// Global test utilities for accessibility testing
global.testUtils = {
  // Helper to check if element is properly labeled
  isProperlyLabeled: (element) => {
    return element.hasAttribute('aria-label') || 
           element.hasAttribute('aria-labelledby') || 
           element.labels?.length > 0;
  },
  
  // Helper to check if element has focus management
  hasFocusManagement: (element) => {
    return element.tabIndex >= 0 || 
           ['button', 'a', 'input', 'select', 'textarea'].includes(element.tagName.toLowerCase()) ||
           element.hasAttribute('role');
  },
  
  // Helper to simulate reduced motion preference
  simulateReducedMotion: (enabled = true) => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation((query) => {
        if (query === '(prefers-reduced-motion: reduce)') {
          return {
            matches: enabled,
            media: query,
            onchange: null,
            addListener: jest.fn(),
            removeListener: jest.fn(),
            addEventListener: jest.fn(),
            removeEventListener: jest.fn(),
            dispatchEvent: jest.fn(),
          };
        }
        return {
          matches: false,
          media: query,
          onchange: null,
          addListener: jest.fn(),
          removeListener: jest.fn(),
          addEventListener: jest.fn(),
          removeEventListener: jest.fn(),
          dispatchEvent: jest.fn(),
        };
      }),
    });
  },
};

// Set up error boundaries for accessibility testing
global.accessibilityTestSetup = {
  // Mock for components that use portal rendering
  mockPortal: () => {
    const portalRoot = document.createElement('div');
    portalRoot.setAttribute('id', 'portal-root');
    document.body.appendChild(portalRoot);
    return portalRoot;
  },
  
  // Clean up portal after tests
  cleanupPortal: () => {
    const portalRoot = document.getElementById('portal-root');
    if (portalRoot) {
      document.body.removeChild(portalRoot);
    }
  },
};