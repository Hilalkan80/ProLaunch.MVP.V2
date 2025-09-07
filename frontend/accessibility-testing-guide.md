# Comprehensive Accessibility Testing Guide for M0 Components

This guide provides a complete framework for testing WCAG 2.1 AA compliance and ensuring accessibility for all M0 components in the ProLaunch MVP platform.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Testing Framework](#testing-framework)
4. [Running Tests](#running-tests)
5. [Manual Testing](#manual-testing)
6. [Reporting and Documentation](#reporting-and-documentation)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)
9. [Resources](#resources)

## Overview

Our accessibility testing framework ensures that all M0 components meet or exceed WCAG 2.1 AA standards. The framework includes:

- **Automated Testing**: axe-core integration for comprehensive rule checking
- **Manual Testing**: Structured procedures for human validation
- **Screen Reader Testing**: Compatibility verification with assistive technologies
- **Keyboard Navigation**: Complete keyboard accessibility validation
- **Color Contrast**: Automated contrast ratio checking
- **Mobile Accessibility**: Touch target and responsive design validation
- **Comprehensive Reporting**: Detailed reports with remediation guidance

## Quick Start

### Installation

```bash
# Install accessibility testing dependencies
npm install --save-dev @axe-core/react jest-axe axe-core @testing-library/jest-dom color-contrast-checker

# Verify installation
npm run test:accessibility
```

### Basic Usage

```typescript
import { testAccessibility, AccessibilityTester } from '../../../utils/test-utils/accessibility';
import { ProductIdeaForm } from '../ProductIdeaForm';

// Quick accessibility test
it('should be accessible', async () => {
  await testAccessibility(<ProductIdeaForm onSubmit={mockHandler} />);
});

// Comprehensive accessibility report
it('should generate accessibility report', async () => {
  const tester = new AccessibilityTester();
  const report = await tester.generateReport(<ProductIdeaForm onSubmit={mockHandler} />);
  
  expect(report.summary.level).toBeIn(['AA', 'AAA']);
  expect(report.summary.score).toBeGreaterThanOrEqual(85);
});
```

## Testing Framework

### Core Components

#### 1. AccessibilityTester Class
The main testing utility that provides comprehensive accessibility auditing:

```typescript
const tester = new AccessibilityTester({
  wcagLevel: 'AA',                    // Target WCAG level
  testColorContrast: true,            // Test color contrast ratios
  testKeyboardNavigation: true,       // Test keyboard accessibility
  testScreenReader: true,             // Test screen reader compatibility
  testMobile: true,                   // Test mobile accessibility
  tags: ['wcag2a', 'wcag2aa', 'wcag21aa'], // Specific rule tags
});
```

#### 2. Test Utilities
Helper functions for specific accessibility aspects:

- `testAccessibility()` - Quick WCAG compliance check
- `testKeyboardNavigation()` - Keyboard navigation validation
- `testColorContrast()` - Color contrast ratio checking
- `mockScreenReader()` - Screen reader announcement testing

### Supported Test Types

#### Automated Tests (axe-core)
- **ARIA Attributes**: Valid and required ARIA attributes
- **Color Contrast**: WCAG AA/AAA contrast requirements
- **Form Labels**: Proper form labeling and associations
- **Heading Structure**: Logical heading hierarchy
- **Keyboard Accessibility**: Focus management and navigation
- **Image Alt Text**: Alternative text for images
- **Landmark Regions**: Proper use of semantic landmarks

#### Manual Test Procedures
- **Screen Reader Testing**: NVDA, JAWS, VoiceOver compatibility
- **Keyboard Navigation**: Tab order and keyboard shortcuts
- **Mobile Accessibility**: Touch targets and responsive behavior
- **Cognitive Accessibility**: Clear content and error handling
- **Visual Testing**: High contrast mode and zoom functionality

## Running Tests

### Available Commands

```bash
# Run all accessibility tests
npm run test:accessibility
npm run test:a11y  # Alias

# Run with coverage
npm run test:coverage:accessibility

# Watch mode for development
npm run test:watch:accessibility

# Run all test types including accessibility
npm run test:jest:all
```

### Test Configuration

Tests are configured in `jest.config.js` with a dedicated accessibility project:

```javascript
{
  displayName: 'accessibility',
  testMatch: ['**/*Accessibility.test.{ts,tsx}', '**/*a11y.test.{ts,tsx}'],
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.accessibility.setup.js'],
  testTimeout: 30000, // Accessibility tests may take longer
}
```

### Environment Setup

The accessibility test environment (`jest.accessibility.setup.js`) includes:

- axe-core integration and custom matchers
- Screen reader mock functionality
- Color contrast testing utilities
- Keyboard navigation helpers
- Reduced motion simulation
- Portal and modal testing support

## Manual Testing

### Required Tools

1. **Screen Readers**:
   - NVDA (Windows) - Free download
   - JAWS (Windows) - Commercial license
   - VoiceOver (macOS) - Built into macOS
   - TalkBack (Android) - Built into Android
   - VoiceOver (iOS) - Built into iOS

2. **Browser Extensions**:
   - axe DevTools (Chrome/Firefox)
   - WAVE Web Accessibility Evaluator
   - Lighthouse Accessibility Audit
   - Accessibility Insights for Web

### Testing Procedures

#### Screen Reader Testing
```bash
# NVDA Commands
Insert + Q          # Start/Stop NVDA
Insert + Space      # Browse mode toggle
H / Shift + H       # Navigate headings
B / Shift + B       # Navigate buttons
F / Shift + F       # Navigate form fields

# VoiceOver Commands
Cmd + F5            # Start/Stop VoiceOver
VO + Right Arrow    # Navigate elements
VO + U              # Open rotor
VO + Cmd + U        # Web rotor
```

#### Keyboard Navigation Testing
1. Use only Tab/Shift+Tab to navigate
2. Test Enter/Space on interactive elements
3. Verify focus indicators are visible
4. Check focus doesn't get trapped unexpectedly
5. Test Escape key functionality

#### Color Contrast Testing
1. Use browser DevTools color picker
2. Verify 4.5:1 ratio for normal text
3. Verify 3:1 ratio for large text (18pt+ or 14pt+ bold)
4. Test all interactive states (hover, focus, active)

### Detailed Manual Testing Guide

See [Manual Accessibility Testing Procedures](./src/utils/test-utils/manual-accessibility-procedures.md) for comprehensive testing steps.

## Reporting and Documentation

### Automated Report Generation

```typescript
import { AccessibilityReporter } from '../../../utils/test-utils/accessibility-reporter';

const reporter = new AccessibilityReporter({
  projectName: 'ProLaunch MVP',
  version: '1.0.0',
  tester: 'QA Team',
});

const components = [
  { name: 'ProductIdeaForm', component: <ProductIdeaForm onSubmit={handler} /> },
  { name: 'ProcessingView', component: <ProcessingView {...props} /> },
  { name: 'FeasibilityReport', component: <FeasibilityReport {...props} /> },
];

const report = await reporter.generateReport(components);

// Generate HTML report
const htmlReport = reporter.generateHtmlReport(report);

// Generate JSON for programmatic use
const jsonReport = reporter.generateJsonReport(report);

// Generate CSV for analysis
const csvReport = reporter.generateCsvReport(report);
```

### Report Contents

The generated reports include:

1. **Executive Summary**
   - Overall accessibility score
   - WCAG compliance level
   - Component pass/fail counts
   - Critical issue summary

2. **Component Details**
   - Individual component scores
   - Specific violations and recommendations
   - WCAG criterion mapping

3. **WCAG Compliance Matrix**
   - Detailed WCAG 2.1 criterion status
   - Level A, AA, and AAA compliance
   - Component-specific issues

4. **Remediation Guidance**
   - Prioritized recommendations
   - Code examples and fixes
   - Screen reader impact assessment
   - Keyboard navigation guidance

### Sample Test Results

```
M0 Components - Accessibility Test Results

Overall Score: 92% (WCAG AA)
Components Tested: 5
Passed: 4
Failed: 1
Critical Issues: 2

Component Results:
✅ ProductIdeaForm: 95% (AAA)
✅ ProcessingView: 91% (AA)
✅ FeasibilityReport: 89% (AA)
✅ LoadingStates: 96% (AAA)
❌ ErrorStates: 78% (A) - Needs improvement
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Accessibility Tests

on:
  pull_request:
    paths:
      - 'frontend/src/components/**'
      - 'frontend/src/**/*test*'

jobs:
  accessibility:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Run accessibility tests
        run: cd frontend && npm run test:accessibility
      
      - name: Generate accessibility report
        run: cd frontend && npm run test:coverage:accessibility
      
      - name: Upload accessibility report
        uses: actions/upload-artifact@v3
        with:
          name: accessibility-report
          path: frontend/coverage/
```

### Pre-commit Hooks

```json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged && npm run test:accessibility"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "npm run test:accessibility -- --findRelatedTests"
    ]
  }
}
```

## Component-Specific Testing Guidelines

### ProductIdeaForm

**Key Accessibility Features:**
- Form label association (`htmlFor` attributes)
- Error state announcements (`role="alert"`)
- Character count updates (`aria-live="polite"`)
- Keyboard submission (Enter key)
- Clear focus management

**Common Issues:**
- Missing label associations
- Error messages not announced
- Character counter not accessible
- Suggestion chips keyboard interaction

### ProcessingView

**Key Accessibility Features:**
- Progress bar with proper ARIA attributes
- Loading state announcements
- Step progression indication
- Cancel button accessibility
- Time information clarity

**Common Issues:**
- Progress updates not announced
- Missing progress labels
- Cancel button not keyboard accessible
- Time updates too frequent

### FeasibilityReport

**Key Accessibility Features:**
- Logical heading hierarchy (H1, H2, H3)
- Data table accessibility
- Expandable section controls
- Action button clarity
- Score visualization alternatives

**Common Issues:**
- Missing heading structure
- Complex data without alternatives
- Expandable sections missing ARIA
- Color-only information conveyance

## Troubleshooting

### Common Test Failures

#### 1. "No accessible name" error
```typescript
// ❌ Bad
<button onClick={handleClick}>
  <Icon name="close" />
</button>

// ✅ Good
<button onClick={handleClick} aria-label="Close dialog">
  <Icon name="close" />
</button>
```

#### 2. "Color contrast insufficient" error
```css
/* ❌ Bad - 3.2:1 ratio */
.text-light {
  color: #999999;
  background-color: #ffffff;
}

/* ✅ Good - 4.6:1 ratio */
.text-accessible {
  color: #666666;
  background-color: #ffffff;
}
```

#### 3. "Focus not visible" error
```css
/* ❌ Bad */
button:focus {
  outline: none;
}

/* ✅ Good */
button:focus-visible {
  outline: 2px solid #005fcc;
  outline-offset: 2px;
}
```

### Debug Mode

Enable detailed logging for accessibility tests:

```javascript
// In test file
process.env.ACCESSIBILITY_DEBUG = 'true';
```

### Test Environment Issues

If tests are failing in CI but passing locally:

1. Check Node.js version compatibility
2. Verify jsdom environment setup
3. Check for timing-related issues
4. Validate mock implementations

## WCAG 2.1 Level AA Checklist

### Level A Requirements
- [ ] 1.1.1 Non-text Content
- [ ] 1.3.1 Info and Relationships
- [ ] 1.3.2 Meaningful Sequence
- [ ] 2.1.1 Keyboard
- [ ] 2.1.2 No Keyboard Trap
- [ ] 2.4.1 Bypass Blocks
- [ ] 2.4.2 Page Titled
- [ ] 2.4.3 Focus Order
- [ ] 3.1.1 Language of Page
- [ ] 3.2.1 On Focus
- [ ] 3.2.2 On Input
- [ ] 3.3.1 Error Identification
- [ ] 3.3.2 Labels or Instructions
- [ ] 4.1.1 Parsing
- [ ] 4.1.2 Name, Role, Value

### Level AA Requirements
- [ ] 1.4.3 Contrast (Minimum)
- [ ] 1.4.4 Resize text
- [ ] 2.4.6 Headings and Labels
- [ ] 2.4.7 Focus Visible
- [ ] 3.3.3 Error Suggestion
- [ ] 3.3.4 Error Prevention (Legal, Financial, Data)

## Resources

### Documentation
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [axe-core Rule Documentation](https://dequeuniversity.com/rules/axe/)
- [ARIA Authoring Practices Guide](https://w3c.github.io/aria-practices/)

### Testing Tools
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [WAVE Web Accessibility Evaluator](https://wave.webaim.org/)
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/)

### Screen Readers
- [NVDA Download](https://www.nvaccess.org/download/)
- [JAWS Information](https://www.freedomscientific.com/products/software/jaws/)
- [VoiceOver User Guide](https://support.apple.com/guide/voiceover/welcome/)

### Learning Resources
- [WebAIM Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)
- [Deque University](https://dequeuniversity.com/)
- [A11y Project](https://www.a11yproject.com/)

## Getting Help

### Internal Support
- **QA Team**: Accessibility testing questions
- **Design System Team**: Component accessibility requirements
- **DevOps Team**: CI/CD integration issues

### External Resources
- **axe-core GitHub**: Technical issues with axe-core
- **WCAG Working Group**: Standards interpretation
- **WebAIM Community**: General accessibility questions

---

## Conclusion

This comprehensive accessibility testing framework ensures that all M0 components meet WCAG 2.1 AA standards and provide an excellent experience for users with disabilities. Regular testing, both automated and manual, combined with detailed reporting and remediation guidance, creates a robust accessibility program that scales with the application.

Remember: Accessibility is not a one-time check but an ongoing commitment to inclusive design and development practices.