/**
 * Jest setup file specifically for security tests
 * Configures additional security-focused testing utilities and global settings
 */

// Import base setup
require('./jest.setup.js');

// Security test specific globals
global.securityTestTimeout = 10000;

// Set default timeout for security tests
jest.setTimeout(10000);

// Mock potentially dangerous browser APIs for security testing
Object.defineProperty(window, 'eval', {
  value: jest.fn(() => {
    throw new Error('eval() usage detected in security test - this should be prevented');
  }),
  writable: true,
});

Object.defineProperty(window, 'Function', {
  value: jest.fn(() => {
    throw new Error('Function constructor usage detected in security test - this should be prevented');
  }),
  writable: true,
});

// Mock localStorage with security validations
const mockLocalStorage = {
  getItem: jest.fn((key) => {
    // Simulate security validation
    if (typeof key !== 'string') {
      throw new Error('LocalStorage key must be a string');
    }
    return null;
  }),
  setItem: jest.fn((key, value) => {
    if (typeof key !== 'string') {
      throw new Error('LocalStorage key must be a string');
    }
    if (typeof value !== 'string') {
      throw new Error('LocalStorage value must be a string');
    }
  }),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true,
});

// Mock sessionStorage with similar security validations
Object.defineProperty(window, 'sessionStorage', {
  value: { ...mockLocalStorage },
  writable: true,
});

// Security test utilities
global.securityTestUtils = {
  expectNoXSSVulnerability: (component, userInput) => {
    // Helper to test for XSS vulnerabilities
    expect(component.innerHTML).not.toContain('<script>');
    expect(component.innerHTML).not.toContain('javascript:');
    expect(component.innerHTML).not.toContain('onerror=');
    expect(component.innerHTML).not.toContain('onload=');
  },
  
  expectSafeHTMLOutput: (htmlString) => {
    // Helper to verify HTML output is safe
    expect(htmlString).not.toMatch(/<script[\s\S]*?>[\s\S]*?<\/script>/gi);
    expect(htmlString).not.toMatch(/javascript:/gi);
    expect(htmlString).not.toMatch(/on\w+\s*=/gi);
  },
  
  expectCSRFProtection: (requestConfig) => {
    // Helper to verify CSRF protection is in place
    expect(requestConfig.headers).toBeDefined();
    expect(
      requestConfig.headers['X-CSRF-Token'] || 
      requestConfig.headers['csrf-token'] ||
      requestConfig.data?.csrfToken
    ).toBeDefined();
  },

  expectSecureHeaders: (response) => {
    // Helper to verify security headers
    expect(response.headers).toBeDefined();
    if (response.headers['Content-Security-Policy']) {
      expect(response.headers['Content-Security-Policy']).toBeTruthy();
    }
    if (response.headers['X-Frame-Options']) {
      expect(response.headers['X-Frame-Options']).toBeTruthy();
    }
  }
};

// Console warnings for potential security issues during tests
const originalConsoleWarn = console.warn;
console.warn = jest.fn((...args) => {
  const message = args.join(' ');
  if (message.includes('eval') || message.includes('innerHTML') || message.includes('dangerouslySetInnerHTML')) {
    // Log security-related warnings for review
    originalConsoleWarn('🔒 SECURITY WARNING in test:', ...args);
  }
  originalConsoleWarn(...args);
});