# M0 Components Integration Tests

This directory contains comprehensive integration tests for the M0 (Feasibility Analysis) components, providing thorough coverage of end-to-end user flows, component interactions, API integration, and error scenarios.

## Test Structure

### Test Files

- **`m0-integration.spec.ts`** - Playwright end-to-end tests
- **`m0-component-integration.test.tsx`** - Jest component integration tests
- **`m0-performance.test.tsx`** - Performance and stress testing
- **`m0-accessibility.test.tsx`** - Accessibility compliance tests
- **`m0-share-export.test.tsx`** - Share and export functionality tests

### Utility Files

- **`mock-api-helper.ts`** - API mocking utilities for Playwright
- **`TestWrapper.tsx`** - React testing utilities and providers

## Test Coverage Areas

### 1. End-to-End User Flows
- ✅ Complete feasibility analysis flow from input to results
- ✅ Suggestion chip workflow
- ✅ Error recovery and retry mechanisms
- ✅ Network error handling with auto-retry
- ✅ State transitions between input → processing → success/error

### 2. Component Interactions
- ✅ Form validation (length, required fields, character limits)
- ✅ Clear button functionality
- ✅ Character counter real-time updates
- ✅ Keyboard shortcuts (Enter to submit, Shift+Enter for newline)
- ✅ Processing step visualization and progress indicators
- ✅ Cancel analysis functionality

### 3. State Management
- ✅ Data persistence during processing
- ✅ Error state transitions and recovery
- ✅ Start over functionality
- ✅ Component unmount cleanup
- ✅ Memory leak prevention

### 4. API Integration
- ✅ Successful API responses with proper data mapping
- ✅ API timeout handling
- ✅ Invalid response format handling
- ✅ Server error responses (500, 404, etc.)
- ✅ Rate limiting scenarios
- ✅ Network connectivity issues

### 5. Loading States
- ✅ Form loading states during submission
- ✅ Processing step indicators
- ✅ Skeleton loading for report data
- ✅ Button and input disabled states
- ✅ Progress bar animations

### 6. Error Scenarios
- ✅ Network connectivity failures
- ✅ Server error responses
- ✅ Invalid JSON responses
- ✅ Missing required data handling
- ✅ Processing timeout scenarios

### 7. Share Functionality
- ✅ Share URL generation with encoded data
- ✅ Copy to clipboard functionality
- ✅ Social media sharing (Twitter, LinkedIn)
- ✅ Email sharing with formatted content
- ✅ Share modal accessibility
- ✅ Clipboard API fallback support

### 8. Export Features
- ✅ PDF export generation
- ✅ JSON export with complete data structure
- ✅ Filename sanitization
- ✅ Download link creation
- ✅ Export error handling

### 9. Performance Testing
- ✅ Component mount performance
- ✅ Form interaction responsiveness
- ✅ State transition timing
- ✅ Animation performance
- ✅ Memory usage monitoring
- ✅ Network performance under load

### 10. Accessibility
- ✅ Keyboard navigation support
- ✅ Screen reader compatibility
- ✅ Focus management
- ✅ ARIA labels and descriptions
- ✅ Color contrast compliance
- ✅ Touch target sizes (mobile)
- ✅ Reduced motion preferences

### 11. Edge Cases
- ✅ Special characters and emoji handling
- ✅ Maximum length input testing
- ✅ Rapid form interactions
- ✅ Browser back/forward navigation
- ✅ Window resize during processing
- ✅ Concurrent request handling

## Running the Tests

### Prerequisites
```bash
# Install dependencies
npm install

# Ensure test environment is set up
npm run build
```

### Individual Test Suites

```bash
# Run all integration tests
npm run test:integration

# Run specific test files
npm test m0-component-integration.test.tsx
npm test m0-performance.test.tsx
npm test m0-accessibility.test.tsx
npm test m0-share-export.test.tsx

# Run Playwright end-to-end tests
npm run test:e2e tests/e2e/m0-integration.spec.ts

# Run with coverage
npm run test:coverage:integration

# Run in watch mode for development
npm run test:watch:integration
```

### Performance Benchmarks

The performance tests include the following benchmarks:

- **Component Mount**: < 1000ms
- **Form Interaction**: < 100ms per character
- **State Transition**: < 500ms
- **Animation Duration**: < 2000ms
- **API Response Timeout**: < 30000ms
- **Memory Leak Threshold**: < 1MB for 10 mounts

### Accessibility Standards

Tests verify compliance with:
- WCAG 2.1 Level AA guidelines
- Keyboard navigation requirements
- Screen reader compatibility
- Focus management standards
- Mobile accessibility guidelines

## Test Data and Mocking

### Mock API Responses

The `MockApiHelper` class provides various API response scenarios:

```typescript
// Successful analysis
await mockApi.mockSuccessfulAnalysis({
  productIdea: 'Test Product',
  viabilityScore: 85,
  marketSize: '$3.2B'
});

// Network errors
await mockApi.simulateNetworkError();

// Processing errors
await mockApi.simulateProcessingError();

// Slow responses
await mockApi.mockSlowResponse(5000);
```

### Test Utilities

The `TestWrapper` provides testing utilities:

```typescript
import { TestWrapper, fillProductIdeaForm, submitForm } from '../utils/TestWrapper';

// Fill and submit form
await fillProductIdeaForm(user, 'My test product idea');
await submitForm(user);

// Wait for processing to complete
await waitForProcessingToComplete();
```

## Writing New Tests

### Best Practices

1. **Use descriptive test names** that clearly indicate what is being tested
2. **Follow the AAA pattern** (Arrange, Act, Assert)
3. **Clean up after tests** to prevent side effects
4. **Use appropriate timeouts** for async operations
5. **Mock external dependencies** appropriately
6. **Test both success and failure scenarios**

### Example Test Structure

```typescript
describe('Feature Description', () => {
  beforeEach(() => {
    // Setup common test conditions
  });

  afterEach(() => {
    // Cleanup after each test
  });

  test('should handle specific scenario', async () => {
    // Arrange
    const user = userEvent.setup();
    render(<TestComponent />);

    // Act
    await user.type(screen.getByTestId('input'), 'test input');
    await user.click(screen.getByTestId('submit'));

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId('result')).toHaveTextContent('expected result');
    });
  });
});
```

## Debugging Tests

### Debug Mode

Enable debug logging:
```bash
JEST_DEBUG=true npm run test:integration
```

### Common Issues

1. **Timeouts**: Increase timeout for slow operations
2. **Flaky tests**: Add proper waits and cleanup
3. **Mock issues**: Verify mocks are properly set up and reset
4. **Memory leaks**: Check component cleanup in afterEach

### Test Reports

Test reports are generated in:
- `coverage/html-report/` - HTML coverage report
- `playwright-report/` - Playwright test results
- `test-results/` - JSON test results

## Continuous Integration

These tests are configured to run in CI with:
- Multiple browser testing (Chrome, Firefox, Safari)
- Mobile viewport testing
- Performance regression detection
- Accessibility compliance checking
- Coverage threshold enforcement (70% minimum, 85% for auth components)

## Contributing

When adding new features to M0 components:

1. Add corresponding integration tests
2. Update mock data if API changes
3. Add performance tests for new interactions
4. Verify accessibility compliance
5. Update this documentation

## Maintenance

### Regular Tasks

- Review and update test data monthly
- Check for deprecated testing utilities
- Update performance benchmarks as needed
- Verify accessibility standards compliance
- Update browser support matrix

### Known Limitations

- PDF generation testing requires additional setup
- WebSocket testing is mocked and may not reflect real behavior
- Some browser-specific features may not be testable in JSDOM

For questions or issues with these tests, please refer to the main project documentation or create an issue in the project repository.