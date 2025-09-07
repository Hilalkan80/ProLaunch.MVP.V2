import React from 'react';
import { testAccessibility, AccessibilityTester, screen } from '../../../utils/test-utils/accessibility';
import { Button } from '../Button';

describe('Button Accessibility Tests', () => {
  it('should pass basic accessibility tests', async () => {
    await testAccessibility(<Button>Click me</Button>);
  });

  it('should have proper accessible name', () => {
    const { container } = render(<Button>Save Changes</Button>);
    
    const button = screen.getByRole('button', { name: /save changes/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAccessibleName('Save Changes');
  });

  it('should handle disabled state accessibly', () => {
    const { container } = render(<Button disabled>Disabled Button</Button>);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
  });

  it('should handle loading state accessibly', () => {
    const { container } = render(<Button isLoading>Loading Button</Button>);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    
    // Should have loading indicator
    const spinner = container.querySelector('svg');
    expect(spinner).toBeInTheDocument();
  });

  it('should generate comprehensive accessibility report', async () => {
    const tester = new AccessibilityTester({
      wcagLevel: 'AA',
      testColorContrast: true,
      testKeyboardNavigation: true,
    });

    const report = await tester.generateReport(<Button>Test Button</Button>);
    
    expect(report.summary.level).toBeIn(['AA', 'AAA']);
    expect(report.summary.score).toBeGreaterThanOrEqual(85);
    expect(report.recommendations).toHaveLength(0);
  });
});

// Mock render function for simple testing
function render(component: React.ReactElement) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  
  // Simple React render mock
  const ReactDOM = require('react-dom');
  ReactDOM.render(component, container);
  
  return { container };
}

// Custom matcher
expect.extend({
  toBeIn(received: any, expectedArray: any[]) {
    const pass = expectedArray.includes(received);
    if (pass) {
      return {
        message: () => `expected ${received} not to be in [${expectedArray.join(', ')}]`,
        pass: true,
      };
    } else {
      return {
        message: () => `expected ${received} to be in [${expectedArray.join(', ')}]`,
        pass: false,
      };
    }
  },
});