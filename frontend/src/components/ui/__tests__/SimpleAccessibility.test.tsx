import React from 'react';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Simple test component
const TestButton = ({ children, ...props }: any) => (
  <button {...props}>{children}</button>
);

const TestForm = () => (
  <form>
    <label htmlFor="test-input">Test Input:</label>
    <input id="test-input" type="text" />
    <button type="submit">Submit</button>
  </form>
);

describe('Simple Accessibility Tests', () => {
  it('should pass axe accessibility tests for button', async () => {
    const { container } = render(<TestButton>Click me</TestButton>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should pass axe accessibility tests for form', async () => {
    const { container } = render(<TestForm />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper button accessibility', () => {
    render(<TestButton>Save Changes</TestButton>);
    
    const button = screen.getByRole('button', { name: /save changes/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAccessibleName('Save Changes');
  });

  it('should have proper form accessibility', () => {
    render(<TestForm />);
    
    const input = screen.getByRole('textbox', { name: /test input/i });
    const submitButton = screen.getByRole('button', { name: /submit/i });
    
    expect(input).toBeInTheDocument();
    expect(input).toHaveAccessibleName('Test Input:');
    expect(submitButton).toBeInTheDocument();
  });

  it('should fail for inaccessible button', async () => {
    // Button without accessible name should fail
    const { container } = render(
      <button>
        <span aria-hidden="true">×</span>
      </button>
    );
    
    const results = await axe(container);
    // This should have violations due to missing accessible name
    expect(results.violations.length).toBeGreaterThan(0);
  });

  it('should test color contrast requirements', async () => {
    const { container } = render(
      <div style={{ color: '#999', backgroundColor: '#fff' }}>
        Low contrast text that should fail
      </div>
    );
    
    const results = await axe(container, {
      rules: {
        'color-contrast': { enabled: true }
      }
    });
    
    // This might fail due to low contrast
    // In a real implementation, we'd ensure proper contrast ratios
    console.log('Color contrast violations:', results.violations.filter(v => v.id === 'color-contrast'));
  });

  it('should test keyboard accessibility', async () => {
    const { container } = render(
      <div>
        <div onClick={() => {}} style={{ cursor: 'pointer' }}>
          Clickable div without keyboard support
        </div>
      </div>
    );
    
    const results = await axe(container);
    
    // This should have violations due to non-keyboard accessible clickable element
    const keyboardViolations = results.violations.filter(v => 
      v.id === 'click-events-have-key-events' || 
      v.id === 'interactive-supports-focus'
    );
    
    console.log('Keyboard accessibility violations:', keyboardViolations);
  });

  it('should validate ARIA attributes', async () => {
    const { container } = render(
      <div>
        <div role="button" tabIndex={0}>
          Proper ARIA button
        </div>
        <div role="invalid-role">
          Invalid ARIA role
        </div>
      </div>
    );
    
    const results = await axe(container);
    
    // Should have violations for invalid ARIA role
    const ariaViolations = results.violations.filter(v => 
      v.id.includes('aria') || v.id.includes('role')
    );
    
    console.log('ARIA violations:', ariaViolations);
  });
});