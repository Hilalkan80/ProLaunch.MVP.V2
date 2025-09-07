import { AccessibilityTester, ColorContrastResult, KeyboardTestResult } from './accessibility';
import { ReactElement } from 'react';

export interface AccessibilityReportConfig {
  projectName?: string;
  version?: string;
  testDate?: Date;
  tester?: string;
  environment?: string;
  components?: ComponentTestResult[];
}

export interface ComponentTestResult {
  name: string;
  component: ReactElement;
  results: {
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
  };
}

export interface AccessibilityReport {
  metadata: {
    projectName: string;
    version: string;
    testDate: string;
    tester: string;
    environment: string;
    totalComponents: number;
  };
  summary: {
    overallScore: number;
    overallLevel: 'A' | 'AA' | 'AAA' | 'FAIL';
    componentsPass: number;
    componentsFail: number;
    criticalIssues: number;
    totalIssues: number;
  };
  components: ComponentTestResult[];
  wcagCompliance: {
    level: 'A' | 'AA' | 'AAA';
    passedCriteria: WcagCriterion[];
    failedCriteria: WcagCriterion[];
    notApplicable: WcagCriterion[];
  };
  recommendations: {
    critical: string[];
    high: string[];
    medium: string[];
    low: string[];
  };
  detailedFindings: Finding[];
}

export interface WcagCriterion {
  number: string;
  title: string;
  level: 'A' | 'AA' | 'AAA';
  status: 'pass' | 'fail' | 'not-applicable';
  components: string[];
}

export interface Finding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  wcagCriterion: string;
  component: string;
  description: string;
  impact: string;
  recommendation: string;
  codeExample?: string;
  screenReaderImpact?: string;
  keyboardImpact?: string;
}

/**
 * Comprehensive accessibility report generator
 */
export class AccessibilityReporter {
  private config: AccessibilityReportConfig;
  private tester: AccessibilityTester;

  constructor(config: AccessibilityReportConfig = {}) {
    this.config = {
      projectName: 'ProLaunch MVP',
      version: '1.0.0',
      testDate: new Date(),
      tester: 'Automated Testing',
      environment: 'Test',
      ...config,
    };
    
    this.tester = new AccessibilityTester({
      wcagLevel: 'AA',
      testColorContrast: true,
      testKeyboardNavigation: true,
      testScreenReader: true,
      testMobile: true,
    });
  }

  /**
   * Generate comprehensive accessibility report for multiple components
   */
  async generateReport(components: { name: string; component: ReactElement }[]): Promise<AccessibilityReport> {
    const componentResults: ComponentTestResult[] = [];
    
    // Test each component
    for (const { name, component } of components) {
      try {
        const results = await this.tester.generateReport(component);
        componentResults.push({
          name,
          component,
          results,
        });
      } catch (error) {
        console.error(`Error testing component ${name}:`, error);
        // Add failed result
        componentResults.push({
          name,
          component,
          results: {
            summary: {
              score: 0,
              level: 'FAIL',
              totalTests: 1,
              passed: 0,
              failed: 1,
            },
            details: {
              axe: { violations: [{ description: `Testing failed: ${error}` }], passes: [] },
              colorContrast: [],
              keyboard: { focusableElements: [], focusOrder: [], trapWorking: false, escapeWorking: false },
              aria: { hasProperRoles: false, hasProperLabels: false, hasProperStates: false, issues: [`Testing error: ${error}`] },
            },
            recommendations: [`Fix testing error for ${name}: ${error}`],
          },
        });
      }
    }

    // Calculate overall statistics
    const totalComponents = componentResults.length;
    const componentsPass = componentResults.filter(c => c.results.summary.level !== 'FAIL').length;
    const componentsFail = totalComponents - componentsPass;
    
    const overallScore = Math.round(
      componentResults.reduce((sum, c) => sum + c.results.summary.score, 0) / totalComponents
    );
    
    let overallLevel: 'A' | 'AA' | 'AAA' | 'FAIL' = 'FAIL';
    if (overallScore >= 95) overallLevel = 'AAA';
    else if (overallScore >= 85) overallLevel = 'AA';
    else if (overallScore >= 70) overallLevel = 'A';

    // Count issues
    const allRecommendations = componentResults.flatMap(c => c.results.recommendations);
    const criticalIssues = allRecommendations.filter(r => 
      r.includes('critical') || r.includes('fails') || r.includes('violation')
    ).length;

    // Generate WCAG compliance report
    const wcagCompliance = this.generateWcagCompliance(componentResults);

    // Categorize recommendations
    const recommendations = this.categorizeRecommendations(allRecommendations);

    // Generate detailed findings
    const detailedFindings = this.generateDetailedFindings(componentResults);

    return {
      metadata: {
        projectName: this.config.projectName!,
        version: this.config.version!,
        testDate: this.config.testDate!.toISOString(),
        tester: this.config.tester!,
        environment: this.config.environment!,
        totalComponents,
      },
      summary: {
        overallScore,
        overallLevel,
        componentsPass,
        componentsFail,
        criticalIssues,
        totalIssues: allRecommendations.length,
      },
      components: componentResults,
      wcagCompliance,
      recommendations,
      detailedFindings,
    };
  }

  /**
   * Generate WCAG 2.1 compliance report
   */
  private generateWcagCompliance(componentResults: ComponentTestResult[]): AccessibilityReport['wcagCompliance'] {
    // WCAG 2.1 Level AA criteria
    const wcagCriteria: WcagCriterion[] = [
      { number: '1.1.1', title: 'Non-text Content', level: 'A', status: 'pass', components: [] },
      { number: '1.3.1', title: 'Info and Relationships', level: 'A', status: 'pass', components: [] },
      { number: '1.3.2', title: 'Meaningful Sequence', level: 'A', status: 'pass', components: [] },
      { number: '1.4.3', title: 'Contrast (Minimum)', level: 'AA', status: 'pass', components: [] },
      { number: '1.4.4', title: 'Resize text', level: 'AA', status: 'pass', components: [] },
      { number: '2.1.1', title: 'Keyboard', level: 'A', status: 'pass', components: [] },
      { number: '2.1.2', title: 'No Keyboard Trap', level: 'A', status: 'pass', components: [] },
      { number: '2.4.1', title: 'Bypass Blocks', level: 'A', status: 'not-applicable', components: [] },
      { number: '2.4.2', title: 'Page Titled', level: 'A', status: 'not-applicable', components: [] },
      { number: '2.4.3', title: 'Focus Order', level: 'A', status: 'pass', components: [] },
      { number: '2.4.6', title: 'Headings and Labels', level: 'AA', status: 'pass', components: [] },
      { number: '2.4.7', title: 'Focus Visible', level: 'AA', status: 'pass', components: [] },
      { number: '3.1.1', title: 'Language of Page', level: 'A', status: 'not-applicable', components: [] },
      { number: '3.2.1', title: 'On Focus', level: 'A', status: 'pass', components: [] },
      { number: '3.2.2', title: 'On Input', level: 'A', status: 'pass', components: [] },
      { number: '3.3.1', title: 'Error Identification', level: 'A', status: 'pass', components: [] },
      { number: '3.3.2', title: 'Labels or Instructions', level: 'A', status: 'pass', components: [] },
      { number: '4.1.1', title: 'Parsing', level: 'A', status: 'pass', components: [] },
      { number: '4.1.2', title: 'Name, Role, Value', level: 'A', status: 'pass', components: [] },
    ];

    // Analyze component results against WCAG criteria
    componentResults.forEach(component => {
      const { axe, colorContrast, keyboard, aria } = component.results.details;

      // Check for violations that map to WCAG criteria
      axe.violations?.forEach((violation: any) => {
        const criterionMap = this.mapViolationToWcag(violation.id);
        criterionMap.forEach(criterionNumber => {
          const criterion = wcagCriteria.find(c => c.number === criterionNumber);
          if (criterion) {
            criterion.status = 'fail';
            criterion.components.push(component.name);
          }
        });
      });

      // Check color contrast issues
      const contrastFailures = colorContrast.filter(c => !c.passes);
      if (contrastFailures.length > 0) {
        const contrastCriterion = wcagCriteria.find(c => c.number === '1.4.3');
        if (contrastCriterion) {
          contrastCriterion.status = 'fail';
          if (!contrastCriterion.components.includes(component.name)) {
            contrastCriterion.components.push(component.name);
          }
        }
      }

      // Check keyboard navigation issues
      if (!keyboard.trapWorking || !keyboard.escapeWorking) {
        const keyboardCriteria = wcagCriteria.filter(c => c.number.startsWith('2.1.'));
        keyboardCriteria.forEach(criterion => {
          criterion.status = 'fail';
          if (!criterion.components.includes(component.name)) {
            criterion.components.push(component.name);
          }
        });
      }

      // Check ARIA issues
      if (aria.issues?.length > 0) {
        const ariaCriteria = wcagCriteria.filter(c => 
          c.number === '4.1.2' || c.number === '1.3.1'
        );
        ariaCriteria.forEach(criterion => {
          criterion.status = 'fail';
          if (!criterion.components.includes(component.name)) {
            criterion.components.push(component.name);
          }
        });
      }
    });

    const passedCriteria = wcagCriteria.filter(c => c.status === 'pass');
    const failedCriteria = wcagCriteria.filter(c => c.status === 'fail');
    const notApplicable = wcagCriteria.filter(c => c.status === 'not-applicable');

    // Determine overall compliance level
    let level: 'A' | 'AA' | 'AAA' = 'AAA';
    if (failedCriteria.some(c => c.level === 'A')) level = 'A';
    else if (failedCriteria.some(c => c.level === 'AA')) level = 'AA';

    return {
      level,
      passedCriteria,
      failedCriteria,
      notApplicable,
    };
  }

  /**
   * Map axe rule violations to WCAG criteria
   */
  private mapViolationToWcag(ruleId: string): string[] {
    const mapping: Record<string, string[]> = {
      'color-contrast': ['1.4.3'],
      'keyboard': ['2.1.1'],
      'focus-order-semantics': ['2.4.3'],
      'aria-allowed-attr': ['4.1.2'],
      'aria-required-attr': ['4.1.2'],
      'aria-valid-attr-value': ['4.1.2'],
      'aria-valid-attr': ['4.1.2'],
      'button-name': ['4.1.2'],
      'duplicate-id': ['4.1.1'],
      'form-field-multiple-labels': ['3.3.2'],
      'image-alt': ['1.1.1'],
      'input-image-alt': ['1.1.1'],
      'label': ['3.3.2'],
      'link-name': ['4.1.2'],
      'list': ['1.3.1'],
      'listitem': ['1.3.1'],
      'role-img-alt': ['1.1.1'],
      'svg-img-alt': ['1.1.1'],
    };

    return mapping[ruleId] || [];
  }

  /**
   * Categorize recommendations by severity
   */
  private categorizeRecommendations(recommendations: string[]): AccessibilityReport['recommendations'] {
    const result = {
      critical: [] as string[],
      high: [] as string[],
      medium: [] as string[],
      low: [] as string[],
    };

    recommendations.forEach(rec => {
      const lower = rec.toLowerCase();
      if (lower.includes('critical') || lower.includes('fails') || lower.includes('violation')) {
        result.critical.push(rec);
      } else if (lower.includes('error') || lower.includes('missing') || lower.includes('invalid')) {
        result.high.push(rec);
      } else if (lower.includes('improve') || lower.includes('enhance') || lower.includes('consider')) {
        result.medium.push(rec);
      } else {
        result.low.push(rec);
      }
    });

    return result;
  }

  /**
   * Generate detailed findings with remediation guidance
   */
  private generateDetailedFindings(componentResults: ComponentTestResult[]): Finding[] {
    const findings: Finding[] = [];
    let findingId = 1;

    componentResults.forEach(component => {
      const { axe, colorContrast, keyboard, aria } = component.results.details;

      // Process axe violations
      axe.violations?.forEach((violation: any) => {
        findings.push({
          id: `A11Y-${findingId++}`,
          severity: this.getSeverityFromViolation(violation),
          wcagCriterion: this.mapViolationToWcag(violation.id).join(', '),
          component: component.name,
          description: violation.description,
          impact: violation.impact || 'Unknown',
          recommendation: violation.help || 'Review accessibility requirements',
          codeExample: violation.nodes?.[0]?.html || '',
          screenReaderImpact: this.getScreenReaderImpact(violation.id),
          keyboardImpact: this.getKeyboardImpact(violation.id),
        });
      });

      // Process color contrast issues
      colorContrast.filter(c => !c.passes).forEach(contrast => {
        findings.push({
          id: `A11Y-${findingId++}`,
          severity: 'high',
          wcagCriterion: '1.4.3',
          component: component.name,
          description: `Insufficient color contrast: ${contrast.ratio.toFixed(2)}:1`,
          impact: 'Users with low vision may not be able to read the text',
          recommendation: `Increase contrast to at least 4.5:1 for normal text or 3:1 for large text`,
          screenReaderImpact: 'None - screen readers don\'t rely on visual contrast',
          keyboardImpact: 'None - keyboard users may still be affected by low vision',
        });
      });

      // Process keyboard navigation issues
      if (!keyboard.trapWorking || !keyboard.escapeWorking) {
        findings.push({
          id: `A11Y-${findingId++}`,
          severity: 'critical',
          wcagCriterion: '2.1.1, 2.1.2',
          component: component.name,
          description: 'Keyboard navigation issues detected',
          impact: 'Keyboard-only users cannot navigate effectively',
          recommendation: 'Ensure all interactive elements are keyboard accessible and focus management works properly',
          keyboardImpact: 'Critical - affects primary interaction method',
          screenReaderImpact: 'High - screen reader users also rely on keyboard navigation',
        });
      }

      // Process ARIA issues
      aria.issues?.forEach((issue: string) => {
        findings.push({
          id: `A11Y-${findingId++}`,
          severity: 'high',
          wcagCriterion: '4.1.2',
          component: component.name,
          description: issue,
          impact: 'Screen readers may not announce content correctly',
          recommendation: 'Review ARIA implementation and ensure proper labeling',
          screenReaderImpact: 'High - directly affects screen reader functionality',
          keyboardImpact: 'Medium - may affect navigation context',
        });
      });
    });

    return findings;
  }

  /**
   * Determine severity from axe violation
   */
  private getSeverityFromViolation(violation: any): 'critical' | 'high' | 'medium' | 'low' {
    const impact = violation.impact?.toLowerCase() || '';
    
    if (impact === 'critical') return 'critical';
    if (impact === 'serious') return 'high';
    if (impact === 'moderate') return 'medium';
    return 'low';
  }

  /**
   * Get screen reader impact description
   */
  private getScreenReaderImpact(ruleId: string): string {
    const impacts: Record<string, string> = {
      'aria-allowed-attr': 'Invalid ARIA attributes may confuse screen readers',
      'aria-required-attr': 'Missing ARIA attributes may not provide necessary context',
      'button-name': 'Buttons without names cannot be identified by screen readers',
      'form-field-multiple-labels': 'Multiple labels may cause confusion',
      'image-alt': 'Images without alt text cannot be described to users',
      'label': 'Form fields without labels cannot be identified',
      'link-name': 'Links without names cannot be identified or navigated to',
    };

    return impacts[ruleId] || 'May affect screen reader functionality';
  }

  /**
   * Get keyboard impact description
   */
  private getKeyboardImpact(ruleId: string): string {
    const impacts: Record<string, string> = {
      'focus-order-semantics': 'Incorrect focus order makes navigation difficult',
      'keyboard': 'Elements not keyboard accessible cannot be reached',
      'button-name': 'Buttons without names are difficult to identify when focused',
    };

    return impacts[ruleId] || 'May affect keyboard navigation';
  }

  /**
   * Generate HTML report
   */
  generateHtmlReport(report: AccessibilityReport): string {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Accessibility Test Report - ${report.metadata.projectName}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            text-align: center;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }
        .level-AAA { color: #28a745; }
        .level-AA { color: #17a2b8; }
        .level-A { color: #ffc107; }
        .level-FAIL { color: #dc3545; }
        .section {
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .section-header {
            background: #f8f9fa;
            padding: 15px 20px;
            font-weight: 600;
            border-bottom: 1px solid #dee2e6;
        }
        .section-content {
            padding: 20px;
        }
        .component-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .component-card {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 15px;
        }
        .score-circle {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            float: right;
            margin-left: 15px;
        }
        .finding {
            border: 1px solid #dee2e6;
            border-radius: 6px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        .finding-header {
            padding: 10px 15px;
            font-weight: 600;
            display: flex;
            justify-content: between;
            align-items: center;
        }
        .severity-critical { background: #f8d7da; color: #721c24; }
        .severity-high { background: #fff3cd; color: #856404; }
        .severity-medium { background: #cce7ff; color: #004085; }
        .severity-low { background: #e2f4e5; color: #155724; }
        .finding-body {
            padding: 15px;
            background: #f8f9fa;
        }
        .wcag-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
        }
        .wcag-item {
            padding: 10px;
            border-radius: 4px;
            font-size: 0.9em;
        }
        .wcag-pass { background: #d4edda; color: #155724; }
        .wcag-fail { background: #f8d7da; color: #721c24; }
        .wcag-na { background: #e2e3e5; color: #495057; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        .progress-bar {
            background: #e9ecef;
            border-radius: 4px;
            height: 20px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Accessibility Test Report</h1>
        <p><strong>${report.metadata.projectName}</strong> v${report.metadata.version}</p>
        <p>Generated on ${new Date(report.metadata.testDate).toLocaleDateString()} by ${report.metadata.tester}</p>
    </div>

    <div class="summary-grid">
        <div class="metric-card">
            <div class="metric-value level-${report.summary.overallLevel}">${report.summary.overallScore}%</div>
            <div>Overall Score</div>
            <div><strong>WCAG ${report.summary.overallLevel}</strong></div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${report.summary.componentsPass}</div>
            <div>Components Pass</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${report.summary.componentsFail}</div>
            <div>Components Fail</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${report.summary.criticalIssues}</div>
            <div>Critical Issues</div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">Component Results</div>
        <div class="section-content">
            <div class="component-grid">
                ${report.components.map(component => `
                    <div class="component-card">
                        <div class="score-circle level-${component.results.summary.level}" style="background-color: ${this.getScoreColor(component.results.summary.score)}">
                            ${component.results.summary.score}%
                        </div>
                        <h4>${component.name}</h4>
                        <p><strong>Level:</strong> WCAG ${component.results.summary.level}</p>
                        <p><strong>Tests:</strong> ${component.results.summary.passed}/${component.results.summary.totalTests} passed</p>
                        <div class="progress-bar">
                            <div class="progress-fill level-${component.results.summary.level}" style="width: ${component.results.summary.score}%; background-color: ${this.getScoreColor(component.results.summary.score)};"></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">WCAG 2.1 Compliance</div>
        <div class="section-content">
            <p><strong>Overall Level:</strong> WCAG ${report.wcagCompliance.level}</p>
            <div class="wcag-grid">
                ${report.wcagCompliance.passedCriteria.concat(report.wcagCompliance.failedCriteria, report.wcagCompliance.notApplicable)
                  .map(criterion => `
                    <div class="wcag-item wcag-${criterion.status === 'pass' ? 'pass' : criterion.status === 'fail' ? 'fail' : 'na'}">
                        <strong>${criterion.number}</strong> ${criterion.title}
                        <br><small>Level ${criterion.level} - ${criterion.status.replace('-', ' ')}</small>
                    </div>
                  `).join('')}
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">Detailed Findings</div>
        <div class="section-content">
            ${report.detailedFindings.map(finding => `
                <div class="finding">
                    <div class="finding-header severity-${finding.severity}">
                        <span><strong>${finding.id}</strong> - ${finding.description}</span>
                        <span>${finding.severity.toUpperCase()}</span>
                    </div>
                    <div class="finding-body">
                        <p><strong>Component:</strong> ${finding.component}</p>
                        <p><strong>WCAG Criterion:</strong> ${finding.wcagCriterion}</p>
                        <p><strong>Impact:</strong> ${finding.impact}</p>
                        <p><strong>Recommendation:</strong> ${finding.recommendation}</p>
                        ${finding.screenReaderImpact ? `<p><strong>Screen Reader Impact:</strong> ${finding.screenReaderImpact}</p>` : ''}
                        ${finding.keyboardImpact ? `<p><strong>Keyboard Impact:</strong> ${finding.keyboardImpact}</p>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    </div>

    <div class="section">
        <div class="section-header">Recommendations Summary</div>
        <div class="section-content">
            <h4 style="color: #dc3545;">Critical (${report.recommendations.critical.length})</h4>
            <ul>
                ${report.recommendations.critical.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
            
            <h4 style="color: #ffc107;">High Priority (${report.recommendations.high.length})</h4>
            <ul>
                ${report.recommendations.high.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
            
            <h4 style="color: #17a2b8;">Medium Priority (${report.recommendations.medium.length})</h4>
            <ul>
                ${report.recommendations.medium.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
            
            <h4 style="color: #28a745;">Low Priority (${report.recommendations.low.length})</h4>
            <ul>
                ${report.recommendations.low.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        </div>
    </div>
</body>
</html>`;
  }

  /**
   * Generate JSON report for programmatic use
   */
  generateJsonReport(report: AccessibilityReport): string {
    return JSON.stringify(report, null, 2);
  }

  /**
   * Generate CSV report for analysis
   */
  generateCsvReport(report: AccessibilityReport): string {
    const headers = ['Component', 'Score', 'Level', 'Tests Passed', 'Tests Failed', 'Issues'];
    const rows = report.components.map(component => [
      component.name,
      component.results.summary.score.toString(),
      component.results.summary.level,
      component.results.summary.passed.toString(),
      component.results.summary.failed.toString(),
      component.results.recommendations.length.toString(),
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
  }

  /**
   * Get color for score visualization
   */
  private getScoreColor(score: number): string {
    if (score >= 95) return '#28a745'; // Green (AAA)
    if (score >= 85) return '#17a2b8'; // Blue (AA)
    if (score >= 70) return '#ffc107'; // Yellow (A)
    return '#dc3545'; // Red (FAIL)
  }

  /**
   * Save report to file system (for Node.js environments)
   */
  async saveReport(report: AccessibilityReport, format: 'html' | 'json' | 'csv' = 'html', filename?: string): Promise<string> {
    const fs = await import('fs').catch(() => null);
    if (!fs) {
      throw new Error('File system not available in this environment');
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const defaultFilename = `accessibility-report-${timestamp}`;
    const fullFilename = filename || defaultFilename;

    let content: string;
    let extension: string;

    switch (format) {
      case 'html':
        content = this.generateHtmlReport(report);
        extension = 'html';
        break;
      case 'json':
        content = this.generateJsonReport(report);
        extension = 'json';
        break;
      case 'csv':
        content = this.generateCsvReport(report);
        extension = 'csv';
        break;
    }

    const filepath = `${fullFilename}.${extension}`;
    await fs.promises.writeFile(filepath, content, 'utf8');
    
    return filepath;
  }
}