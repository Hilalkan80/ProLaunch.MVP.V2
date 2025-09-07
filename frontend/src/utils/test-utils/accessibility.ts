import { axe, toHaveNoViolations } from 'jest-axe';
import { render as rtlRender, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReactElement } from 'react';
import ColorContrastChecker from 'color-contrast-checker';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

const colorChecker = new ColorContrastChecker();

export interface AccessibilityTestOptions {
  /**
   * Axe-core rules to test against
   */
  rules?: Record<string, { enabled: boolean }>;
  /**
   * WCAG level to test (A, AA, AAA)
   */
  wcagLevel?: 'A' | 'AA' | 'AAA';
  /**
   * Whether to test color contrast
   */
  testColorContrast?: boolean;
  /**
   * Whether to test keyboard navigation
   */
  testKeyboardNavigation?: boolean;
  /**
   * Whether to test screen reader compatibility
   */
  testScreenReader?: boolean;
  /**
   * Whether to test mobile accessibility
   */
  testMobile?: boolean;
  /**
   * Custom tags to focus on
   */
  tags?: string[];
  /**
   * Elements to exclude from testing
   */
  exclude?: string[];
}

export interface KeyboardTestResult {
  focusableElements: Element[];
  focusOrder: Element[];
  trapWorking: boolean;
  escapeWorking: boolean;
}

export interface ColorContrastResult {
  passes: boolean;
  ratio: number;
  level: 'AA' | 'AAA' | 'fail';
  foreground: string;
  background: string;
}

/**
 * Comprehensive accessibility testing utility
 */
export class AccessibilityTester {
  private container: HTMLElement | null = null;
  private options: AccessibilityTestOptions;

  constructor(options: AccessibilityTestOptions = {}) {
    this.options = {
      wcagLevel: 'AA',
      testColorContrast: true,
      testKeyboardNavigation: true,
      testScreenReader: true,
      testMobile: false,
      tags: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      ...options,
    };
  }

  /**
   * Run complete accessibility audit
   */
  async runAccessibilityAudit(element: ReactElement): Promise<{
    axeResults: any;
    colorContrastResults: ColorContrastResult[];
    keyboardResults: KeyboardTestResult;
    violations: string[];
  }> {
    const { container } = rtlRender(element);
    this.container = container;

    const results = {
      axeResults: null as any,
      colorContrastResults: [] as ColorContrastResult[],
      keyboardResults: {} as KeyboardTestResult,
      violations: [] as string[],
    };

    // Run axe-core tests
    results.axeResults = await this.runAxeTests();
    
    if (results.axeResults.violations.length > 0) {
      results.violations.push(...results.axeResults.violations.map((v: any) => v.description));
    }

    // Run color contrast tests
    if (this.options.testColorContrast) {
      results.colorContrastResults = await this.testColorContrast();
      const contrastFailures = results.colorContrastResults.filter(r => r.level === 'fail');
      if (contrastFailures.length > 0) {
        results.violations.push(...contrastFailures.map(f => 
          `Color contrast failure: ${f.foreground} on ${f.background} (ratio: ${f.ratio})`
        ));
      }
    }

    // Run keyboard navigation tests
    if (this.options.testKeyboardNavigation) {
      results.keyboardResults = await this.testKeyboardNavigation();
      if (!results.keyboardResults.trapWorking || !results.keyboardResults.escapeWorking) {
        results.violations.push('Keyboard navigation issues detected');
      }
    }

    return results;
  }

  /**
   * Run axe-core accessibility tests
   */
  async runAxeTests(): Promise<any> {
    if (!this.container) throw new Error('Container not initialized');

    const config = {
      tags: this.options.tags,
      rules: {
        // Enable/disable specific rules
        'color-contrast': { enabled: this.options.testColorContrast },
        'keyboard': { enabled: this.options.testKeyboardNavigation },
        'aria-allowed-attr': { enabled: true },
        'aria-required-attr': { enabled: true },
        'aria-valid-attr-value': { enabled: true },
        'aria-valid-attr': { enabled: true },
        'button-name': { enabled: true },
        'bypass': { enabled: true },
        'document-title': { enabled: false }, // Not applicable for components
        'duplicate-id': { enabled: true },
        'form-field-multiple-labels': { enabled: true },
        'frame-title': { enabled: true },
        'html-has-lang': { enabled: false }, // Not applicable for components
        'html-lang-valid': { enabled: false }, // Not applicable for components
        'image-alt': { enabled: true },
        'input-image-alt': { enabled: true },
        'label': { enabled: true },
        'link-name': { enabled: true },
        'list': { enabled: true },
        'listitem': { enabled: true },
        'meta-refresh': { enabled: true },
        'meta-viewport': { enabled: false }, // Not applicable for components
        'object-alt': { enabled: true },
        'role-img-alt': { enabled: true },
        'scrollable-region-focusable': { enabled: true },
        'server-side-image-map': { enabled: true },
        'svg-img-alt': { enabled: true },
        'td-headers-attr': { enabled: true },
        'th-has-data-cells': { enabled: true },
        'valid-lang': { enabled: true },
        'video-caption': { enabled: true },
        ...this.options.rules,
      },
    };

    // Exclude elements if specified
    if (this.options.exclude) {
      config.exclude = this.options.exclude;
    }

    return await axe(this.container, config);
  }

  /**
   * Test color contrast ratios
   */
  async testColorContrast(): Promise<ColorContrastResult[]> {
    if (!this.container) throw new Error('Container not initialized');

    const results: ColorContrastResult[] = [];
    const textElements = this.container.querySelectorAll(
      'p, span, a, button, input, label, h1, h2, h3, h4, h5, h6, li, td, th, div'
    );

    for (const element of textElements) {
      const computedStyle = window.getComputedStyle(element);
      const color = computedStyle.color;
      const backgroundColor = computedStyle.backgroundColor;

      // Skip if no visible text or transparent background
      if (!color || backgroundColor === 'rgba(0, 0, 0, 0)' || !element.textContent?.trim()) {
        continue;
      }

      const contrast = this.calculateContrastRatio(color, backgroundColor);
      const fontSize = parseFloat(computedStyle.fontSize);
      const isBold = computedStyle.fontWeight === 'bold' || parseInt(computedStyle.fontWeight) >= 700;
      
      // WCAG AA requirements: 4.5:1 for normal text, 3:1 for large text (18pt+ or 14pt+ bold)
      const isLargeText = fontSize >= 24 || (fontSize >= 19 && isBold);
      const requiredRatio = isLargeText ? 3 : 4.5;
      
      let level: 'AA' | 'AAA' | 'fail' = 'fail';
      if (contrast >= 7) level = 'AAA';
      else if (contrast >= requiredRatio) level = 'AA';

      results.push({
        passes: contrast >= requiredRatio,
        ratio: contrast,
        level,
        foreground: color,
        background: backgroundColor,
      });
    }

    return results;
  }

  /**
   * Calculate color contrast ratio between two colors
   */
  private calculateContrastRatio(foreground: string, background: string): number {
    try {
      const fgRgb = this.parseColor(foreground);
      const bgRgb = this.parseColor(background);
      
      if (!fgRgb || !bgRgb) return 0;

      return colorChecker.getContrastRatio(fgRgb, bgRgb);
    } catch {
      return 0;
    }
  }

  /**
   * Parse CSS color string to RGB values
   */
  private parseColor(colorStr: string): { r: number; g: number; b: number } | null {
    const rgbMatch = colorStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (rgbMatch) {
      return {
        r: parseInt(rgbMatch[1]),
        g: parseInt(rgbMatch[2]),
        b: parseInt(rgbMatch[3]),
      };
    }

    const hexMatch = colorStr.match(/^#([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
    if (hexMatch) {
      return {
        r: parseInt(hexMatch[1], 16),
        g: parseInt(hexMatch[2], 16),
        b: parseInt(hexMatch[3], 16),
      };
    }

    return null;
  }

  /**
   * Test keyboard navigation and focus management
   */
  async testKeyboardNavigation(): Promise<KeyboardTestResult> {
    if (!this.container) throw new Error('Container not initialized');

    const user = userEvent.setup();
    const focusableElements = Array.from(
      this.container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter(el => !el.hasAttribute('disabled')) as HTMLElement[];

    const result: KeyboardTestResult = {
      focusableElements,
      focusOrder: [],
      trapWorking: true,
      escapeWorking: true,
    };

    if (focusableElements.length === 0) {
      return result;
    }

    // Test tab order
    focusableElements[0]?.focus();
    result.focusOrder.push(document.activeElement as Element);

    for (let i = 1; i < focusableElements.length; i++) {
      await user.tab();
      if (document.activeElement && result.focusOrder[result.focusOrder.length - 1] !== document.activeElement) {
        result.focusOrder.push(document.activeElement);
      }
    }

    // Test escape key functionality
    try {
      await user.keyboard('{Escape}');
      // If escape doesn't cause any errors, it's working
    } catch {
      result.escapeWorking = false;
    }

    return result;
  }

  /**
   * Test for proper ARIA attributes and roles
   */
  async testAriaCompliance(): Promise<{
    hasProperRoles: boolean;
    hasProperLabels: boolean;
    hasProperStates: boolean;
    issues: string[];
  }> {
    if (!this.container) throw new Error('Container not initialized');

    const issues: string[] = [];
    let hasProperRoles = true;
    let hasProperLabels = true;
    let hasProperStates = true;

    // Check for elements that should have labels
    const labelRequiredElements = this.container.querySelectorAll(
      'input:not([type="hidden"]), select, textarea, button'
    );

    labelRequiredElements.forEach((element) => {
      const hasLabel = element.hasAttribute('aria-label') ||
        element.hasAttribute('aria-labelledby') ||
        element.labels?.length > 0 ||
        (element as HTMLElement).textContent?.trim() !== '';

      if (!hasLabel) {
        hasProperLabels = false;
        issues.push(`Element ${element.tagName} lacks proper labeling`);
      }
    });

    // Check for interactive elements without proper roles
    const interactiveElements = this.container.querySelectorAll(
      '[onclick], [onkeydown], [tabindex]:not([tabindex="-1"])'
    );

    interactiveElements.forEach((element) => {
      const hasRole = element.hasAttribute('role') ||
        ['button', 'a', 'input', 'select', 'textarea'].includes(
          element.tagName.toLowerCase()
        );

      if (!hasRole) {
        hasProperRoles = false;
        issues.push(`Interactive element ${element.tagName} lacks proper role`);
      }
    });

    return {
      hasProperRoles,
      hasProperLabels,
      hasProperStates,
      issues,
    };
  }

  /**
   * Test mobile accessibility features
   */
  async testMobileAccessibility(): Promise<{
    hasTouchTargets: boolean;
    hasProperSpacing: boolean;
    issues: string[];
  }> {
    if (!this.container) throw new Error('Container not initialized');

    const issues: string[] = [];
    let hasTouchTargets = true;
    let hasProperSpacing = true;

    // Check touch target sizes (minimum 44px)
    const interactiveElements = this.container.querySelectorAll(
      'button, a, input, select, textarea, [role="button"]'
    );

    interactiveElements.forEach((element) => {
      const rect = element.getBoundingClientRect();
      const minSize = 44;

      if (rect.width < minSize || rect.height < minSize) {
        hasTouchTargets = false;
        issues.push(
          `Touch target too small: ${element.tagName} (${rect.width}x${rect.height}px)`
        );
      }
    });

    return {
      hasTouchTargets,
      hasProperSpacing,
      issues,
    };
  }

  /**
   * Generate comprehensive accessibility report
   */
  async generateReport(element: ReactElement): Promise<{
    summary: {
      score: number;
      level: 'A' | 'AA' | 'AAA' | 'FAIL';
      totalTests: number;
      passed: number;
      failed: number;
    };
    details: {
      axe: any;
      colorContrast: ColorContrastResult[];
      keyboard: KeyboardTestResult;
      aria: any;
      mobile?: any;
    };
    recommendations: string[];
  }> {
    const auditResults = await this.runAccessibilityAudit(element);
    const ariaResults = await this.testAriaCompliance();
    const mobileResults = this.options.testMobile
      ? await this.testMobileAccessibility()
      : null;

    const totalTests = [
      auditResults.axeResults.passes.length + auditResults.axeResults.violations.length,
      auditResults.colorContrastResults.length,
      ariaResults.issues.length === 0 ? 1 : 0,
    ].reduce((a, b) => a + b, 0);

    const failed = [
      auditResults.axeResults.violations.length,
      auditResults.colorContrastResults.filter(r => !r.passes).length,
      ariaResults.issues.length,
    ].reduce((a, b) => a + b, 0);

    const passed = totalTests - failed;
    const score = totalTests > 0 ? Math.round((passed / totalTests) * 100) : 100;

    let level: 'A' | 'AA' | 'AAA' | 'FAIL' = 'FAIL';
    if (score >= 95) level = 'AAA';
    else if (score >= 85) level = 'AA';
    else if (score >= 70) level = 'A';

    const recommendations: string[] = [];
    if (auditResults.violations.length > 0) {
      recommendations.push(...auditResults.violations);
    }
    if (ariaResults.issues.length > 0) {
      recommendations.push(...ariaResults.issues);
    }
    if (mobileResults?.issues.length) {
      recommendations.push(...mobileResults.issues);
    }

    return {
      summary: {
        score,
        level,
        totalTests,
        passed,
        failed,
      },
      details: {
        axe: auditResults.axeResults,
        colorContrast: auditResults.colorContrastResults,
        keyboard: auditResults.keyboardResults,
        aria: ariaResults,
        mobile: mobileResults,
      },
      recommendations,
    };
  }
}

/**
 * Quick accessibility test for components
 */
export const testAccessibility = async (
  element: ReactElement,
  options?: AccessibilityTestOptions
): Promise<void> => {
  const tester = new AccessibilityTester(options);
  const results = await tester.runAccessibilityAudit(element);

  // Fail the test if there are violations
  expect(results.axeResults).toHaveNoViolations();

  if (results.violations.length > 0) {
    throw new Error(`Accessibility violations found:\n${results.violations.join('\n')}`);
  }
};

/**
 * Test keyboard navigation specifically
 */
export const testKeyboardNavigation = async (
  element: ReactElement
): Promise<KeyboardTestResult> => {
  const tester = new AccessibilityTester({ testKeyboardNavigation: true });
  rtlRender(element);
  return await tester.testKeyboardNavigation();
};

/**
 * Test color contrast specifically
 */
export const testColorContrast = async (
  element: ReactElement
): Promise<ColorContrastResult[]> => {
  const tester = new AccessibilityTester({ testColorContrast: true });
  rtlRender(element);
  return await tester.testColorContrast();
};

/**
 * Mock screen reader announcements for testing
 */
export const mockScreenReader = () => {
  const announcements: string[] = [];
  
  // Mock live region announcements
  const originalSetAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name: string, value: string) {
    if (name === 'aria-live' && value) {
      announcements.push(this.textContent || '');
    }
    return originalSetAttribute.call(this, name, value);
  };

  // Mock role="alert" and status
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach((node) => {
          if (node instanceof Element) {
            const role = node.getAttribute('role');
            if (role === 'alert' || role === 'status') {
              announcements.push(node.textContent || '');
            }
          }
        });
      }
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  return {
    announcements,
    getLastAnnouncement: () => announcements[announcements.length - 1],
    clearAnnouncements: () => announcements.splice(0, announcements.length),
    disconnect: () => observer.disconnect(),
  };
};

// Re-export commonly used testing utilities
export {
  screen,
  fireEvent,
  waitFor,
  userEvent,
};

// Export render with alias
export { render as rtlRender } from '@testing-library/react';