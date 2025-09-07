/**
 * Jest setup file specifically for integration tests
 * Configures additional integration testing utilities and global settings
 */

// Import base setup
require('./jest.setup.js');

// Set default timeout for integration tests
jest.setTimeout(15000);

// Integration test specific globals
global.integrationTestTimeout = 15000;

// Mock API endpoints for integration testing
global.mockApiEndpoints = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 5000,
};

// Setup mock server utilities
global.integrationTestUtils = {
  setupMockServer: () => {
    // Placeholder for mock server setup
    return {
      listen: jest.fn(),
      close: jest.fn(),
      resetHandlers: jest.fn(),
    };
  },
  
  expectApiCall: (mockServer, endpoint, method = 'GET') => {
    // Helper to verify API calls were made during integration tests
    expect(mockServer).toHaveBeenCalledWith(
      expect.objectContaining({
        url: expect.stringContaining(endpoint),
        method: method.toUpperCase(),
      })
    );
  },

  expectValidResponse: (response) => {
    // Helper to verify API response structure
    expect(response).toBeDefined();
    expect(response.status).toBeGreaterThanOrEqual(200);
    expect(response.status).toBeLessThan(400);
  },

  expectErrorResponse: (response, expectedStatus = 400) => {
    // Helper to verify error response structure
    expect(response).toBeDefined();
    expect(response.status).toBeGreaterThanOrEqual(expectedStatus);
    if (response.data && response.data.error) {
      expect(response.data.error).toBeDefined();
    }
  }
};

// Setup for component integration testing
global.componentTestUtils = {
  expectComponentRenders: (component) => {
    expect(component).toBeInTheDocument();
  },
  
  expectUserInteraction: (element, interaction) => {
    expect(element).toBeVisible();
    expect(element).not.toBeDisabled();
  },

  expectFormSubmission: (form, submitButton) => {
    expect(form).toBeInTheDocument();
    expect(submitButton).toBeInTheDocument();
    expect(submitButton).not.toBeDisabled();
  }
};

// Console logging for integration test debugging
const originalConsoleLog = console.log;
console.log = jest.fn((...args) => {
  if (process.env.JEST_DEBUG === 'true') {
    originalConsoleLog('🔧 INTEGRATION TEST LOG:', ...args);
  }
});