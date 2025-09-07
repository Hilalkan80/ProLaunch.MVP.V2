import React from 'react';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render, createMockFeasibilityReport, createMockHandlers, disableAnimations } from './testUtils';
import { FeasibilityReport } from '../FeasibilityReport';

describe('FeasibilityReport', () => {
  const mockHandlers = createMockHandlers();
  let cleanupAnimations: () => void;

  const defaultProps = {
    data: createMockFeasibilityReport(),
    onStartNextStep: mockHandlers.onStartNextStep,
    onUpgrade: mockHandlers.onUpgrade,
  };

  beforeEach(() => {
    cleanupAnimations = disableAnimations();
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanupAnimations();
  });

  describe('Rendering', () => {
    it('should render with default props', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByText(/feasibility report/i)).toBeInTheDocument();
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      expect(screen.getByText('Key Insights')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
      expect(screen.getByText('Next Steps (Priority Order)')).toBeInTheDocument();
    });

    it('should display product idea in title', () => {
      const customData = createMockFeasibilityReport({
        productIdea: 'Smart Pet Feeders'
      });
      
      render(
        <FeasibilityReport 
          {...defaultProps} 
          data={customData}
        />
      );
      
      expect(screen.getByText('Smart Pet Feeders Feasibility Report')).toBeInTheDocument();
    });

    it('should display generated timestamp', () => {
      const testDate = new Date('2023-12-25T10:30:00Z');
      const customData = createMockFeasibilityReport({
        generatedAt: testDate
      });
      
      render(
        <FeasibilityReport 
          {...defaultProps} 
          data={customData}
        />
      );
      
      expect(screen.getByText(/12\/25\/2023/)).toBeInTheDocument();
      expect(screen.getByText(/10:30:00/)).toBeInTheDocument();
    });

    it('should render with custom className', () => {
      const customClass = 'custom-report-class';
      render(
        <FeasibilityReport 
          {...defaultProps} 
          className={customClass}
        />
      );
      
      const container = screen.getByText(/feasibility report/i).closest('.custom-report-class');
      expect(container).toBeInTheDocument();
    });
  });

  describe('Navigation Actions', () => {
    it('should render New Analysis button and call handler', async () => {
      const user = userEvent.setup();
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onNewAnalysis={mockHandlers.onNewAnalysis}
        />
      );
      
      const newAnalysisButton = screen.getByRole('button', { name: /← new analysis/i });
      await user.click(newAnalysisButton);
      
      expect(mockHandlers.onNewAnalysis).toHaveBeenCalledTimes(1);
    });

    it('should render Share button when onShare is provided', async () => {
      const user = userEvent.setup();
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
        />
      );
      
      const shareButton = screen.getByRole('button', { name: /share/i });
      await user.click(shareButton);
      
      expect(mockHandlers.onShare).toHaveBeenCalledTimes(1);
    });

    it('should render Export button when onExport is provided', async () => {
      const user = userEvent.setup();
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onExport={mockHandlers.onExport}
        />
      );
      
      const exportButton = screen.getByRole('button', { name: /export/i });
      await user.click(exportButton);
      
      expect(mockHandlers.onExport).toHaveBeenCalledTimes(1);
    });

    it('should not render Share/Export buttons when handlers are not provided', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.queryByRole('button', { name: /share/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /export/i })).not.toBeInTheDocument();
    });
  });

  describe('Viability Score Display', () => {
    it('should display viability score with correct color for high score', () => {
      const data = createMockFeasibilityReport({ viabilityScore: 85 });
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('85')).toHaveClass('text-green-600');
      expect(screen.getByText('VIABLE CONCEPT')).toHaveClass('bg-green-600');
    });

    it('should display viability score with correct color for moderate score', () => {
      const data = createMockFeasibilityReport({ viabilityScore: 60 });
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('60')).toHaveClass('text-yellow-600');
      expect(screen.getByText('MODERATE POTENTIAL')).toHaveClass('bg-yellow-500');
    });

    it('should display viability score with correct color for low score', () => {
      const data = createMockFeasibilityReport({ viabilityScore: 30 });
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('30')).toHaveClass('text-red-600');
      expect(screen.getByText('HIGH RISK')).toHaveClass('bg-red-600');
    });

    it('should render circular progress indicator', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      // Check for SVG elements that form the progress circle
      const svgElement = screen.getByText('78').closest('div')?.querySelector('svg');
      expect(svgElement).toBeInTheDocument();
    });
  });

  describe('Market Insights', () => {
    it('should display all insights with correct icons', () => {
      const data = createMockFeasibilityReport({
        insights: [
          { type: 'positive', text: 'Strong market growth' },
          { type: 'warning', text: 'High competition' },
          { type: 'neutral', text: 'Market analysis' },
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('Strong market growth')).toBeInTheDocument();
      expect(screen.getByText('High competition')).toBeInTheDocument();
      expect(screen.getByText('Market analysis')).toBeInTheDocument();
    });

    it('should display correct icons for different insight types', () => {
      const data = createMockFeasibilityReport({
        insights: [
          { type: 'positive', text: 'Positive insight' },
          { type: 'warning', text: 'Warning insight' },
          { type: 'neutral', text: 'Neutral insight' },
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      const insightsSection = screen.getByText('Key Insights').closest('div');
      const icons = insightsSection?.querySelectorAll('svg');
      expect(icons).toHaveLength(3); // One icon per insight
    });
  });

  describe('Market Analysis', () => {
    it('should display market size, growth rate, and competition level', () => {
      const data = createMockFeasibilityReport({
        marketSize: '$5.2B',
        growthRate: '12% YoY',
        competitionLevel: 'high'
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('$5.2B')).toBeInTheDocument();
      expect(screen.getByText('12% YoY')).toBeInTheDocument();
      expect(screen.getByText('high')).toHaveClass('text-red-600');
    });

    it('should apply correct color classes for competition levels', () => {
      const testCases = [
        { level: 'low', colorClass: 'text-green-600' },
        { level: 'moderate', colorClass: 'text-yellow-600' },
        { level: 'high', colorClass: 'text-red-600' },
      ];
      
      testCases.forEach(({ level, colorClass }) => {
        const data = createMockFeasibilityReport({
          competitionLevel: level as any
        });
        
        const { rerender } = render(<FeasibilityReport {...defaultProps} data={data} />);
        expect(screen.getByText(level)).toHaveClass(colorClass);
      });
    });

    it('should display competitor count', () => {
      const data = createMockFeasibilityReport({
        competitors: Array(5).fill(null).map((_, i) => ({
          name: `Competitor ${i + 1}`,
          priceRange: '$10-15',
          rating: 4.0,
          reviewCount: 100,
          marketPosition: 'premium' as const,
        }))
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('5 main competitors')).toBeInTheDocument();
    });
  });

  describe('Competitors Section', () => {
    it('should expand/collapse competitors section', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const toggleButton = screen.getByRole('button', { name: /top competitors/i });
      
      // Initially collapsed
      expect(screen.queryByText('Test Competitor')).not.toBeInTheDocument();
      
      // Expand
      await user.click(toggleButton);
      await waitFor(() => {
        expect(screen.getByText('Test Competitor')).toBeInTheDocument();
      });
      
      // Collapse
      await user.click(toggleButton);
      await waitFor(() => {
        expect(screen.queryByText('Test Competitor')).not.toBeInTheDocument();
      });
    });

    it('should display competitor details when expanded', async () => {
      const user = userEvent.setup();
      const data = createMockFeasibilityReport({
        competitors: [{
          name: 'Premium Pet Foods',
          priceRange: '$20-25/lb',
          rating: 4.7,
          reviewCount: 1500,
          marketPosition: 'ultra-premium'
        }]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      await user.click(screen.getByRole('button', { name: /top competitors/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Premium Pet Foods')).toBeInTheDocument();
        expect(screen.getByText('$20-25/lb')).toBeInTheDocument();
        expect(screen.getByText('(1500+)')).toBeInTheDocument();
        expect(screen.getByText('ultra-premium')).toBeInTheDocument();
      });
    });

    it('should display star ratings correctly', async () => {
      const user = userEvent.setup();
      const data = createMockFeasibilityReport({
        competitors: [{
          name: 'Test Competitor',
          priceRange: '$15-20',
          rating: 3.5,
          reviewCount: 800,
          marketPosition: 'premium'
        }]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      await user.click(screen.getByRole('button', { name: /top competitors/i }));
      
      await waitFor(() => {
        const starsContainer = screen.getByText('Test Competitor').closest('div');
        const stars = starsContainer?.querySelectorAll('svg');
        expect(stars).toHaveLength(5); // Always 5 stars, some filled, some empty
      });
    });
  });

  describe('Pricing Recommendations', () => {
    it('should display recommended price range', () => {
      const data = createMockFeasibilityReport({
        recommendedPriceRange: '$25-30/unit'
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('Suggested Range: $25-30/unit')).toBeInTheDocument();
    });

    it('should have clickable analysis button', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const analysisButton = screen.getByRole('button', { name: /view analysis →/i });
      expect(analysisButton).toBeInTheDocument();
      
      // Should be clickable but we're not testing the expand functionality here
      await user.click(analysisButton);
    });
  });

  describe('Next Steps', () => {
    it('should display next steps in priority order', () => {
      const data = createMockFeasibilityReport({
        nextSteps: [
          {
            id: 'step-3',
            title: 'Third Step',
            description: 'Third description',
            isUnlocked: false,
            order: 3,
          },
          {
            id: 'step-1',
            title: 'First Step',
            description: 'First description',
            isUnlocked: true,
            order: 1,
          },
          {
            id: 'step-2',
            title: 'Second Step',
            description: 'Second description',
            isUnlocked: false,
            order: 2,
          },
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      const steps = screen.getAllByText(/Step$/);
      expect(steps[0]).toHaveTextContent('First Step');
      expect(steps[1]).toHaveTextContent('Second Step');
      expect(steps[2]).toHaveTextContent('Third Step');
    });

    it('should show START NOW button for unlocked steps', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const startButton = screen.getByRole('button', { name: /start now →/i });
      await user.click(startButton);
      
      expect(mockHandlers.onStartNextStep).toHaveBeenCalledWith('test-step');
    });

    it('should show UNLOCK PAID button for locked steps', async () => {
      const user = userEvent.setup();
      const data = createMockFeasibilityReport({
        nextSteps: [{
          id: 'locked-step',
          title: 'Locked Step',
          description: 'Premium feature',
          isUnlocked: false,
          order: 1,
        }]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      const upgradeButton = screen.getByRole('button', { name: /unlock paid/i });
      await user.click(upgradeButton);
      
      expect(mockHandlers.onUpgrade).toHaveBeenCalledTimes(1);
    });

    it('should display estimated time when provided', () => {
      const data = createMockFeasibilityReport({
        nextSteps: [{
          id: 'timed-step',
          title: 'Timed Step',
          description: 'With time estimate',
          isUnlocked: true,
          order: 1,
          estimatedTime: '30 minutes'
        }]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('~30 minutes')).toBeInTheDocument();
    });

    it('should apply correct styling for unlocked vs locked steps', () => {
      const data = createMockFeasibilityReport({
        nextSteps: [
          {
            id: 'unlocked',
            title: 'Unlocked Step',
            description: 'Available now',
            isUnlocked: true,
            order: 1,
          },
          {
            id: 'locked',
            title: 'Locked Step',
            description: 'Premium only',
            isUnlocked: false,
            order: 2,
          },
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      const unlockedStep = screen.getByText('Unlocked Step').closest('div');
      expect(unlockedStep).toHaveClass('border-blue-200', 'bg-blue-50');
      
      const lockedStep = screen.getByText('Locked Step').closest('div');
      expect(lockedStep).toHaveClass('border-gray-200', 'bg-gray-50');
    });
  });

  describe('Upgrade CTA', () => {
    it('should display upgrade section with benefits', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByText('Unlock Full Potential')).toBeInTheDocument();
      expect(screen.getByText('$249 one-time payment')).toBeInTheDocument();
      expect(screen.getByText('Supplier database with contacts')).toBeInTheDocument();
      expect(screen.getByText('Professional financial models')).toBeInTheDocument();
    });

    it('should call onUpgrade when upgrade button is clicked', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const upgradeButton = screen.getByRole('button', { name: /upgrade to launcher package/i });
      await user.click(upgradeButton);
      
      expect(mockHandlers.onUpgrade).toHaveBeenCalledTimes(1);
    });

    it('should display money-back guarantee', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByText('30-day money-back guarantee')).toBeInTheDocument();
    });

    it('should display all upgrade benefits', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      const benefits = [
        'Supplier database with contacts',
        'Brand positioning & marketing',
        'Website briefs & tech specs',
        'Professional financial models',
        'Legal & compliance templates',
        'Launch readiness checklist'
      ];
      
      benefits.forEach(benefit => {
        expect(screen.getByText(benefit)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toHaveTextContent(/feasibility report/i);
      
      const subHeadings = screen.getAllByRole('heading', { level: 2 });
      expect(subHeadings.length).toBeGreaterThan(0);
    });

    it('should have accessible buttons with proper labels', () => {
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
          onNewAnalysis={mockHandlers.onNewAnalysis}
        />
      );
      
      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toHaveAccessibleName();
      });
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onNewAnalysis={mockHandlers.onNewAnalysis}
        />
      );
      
      const newAnalysisButton = screen.getByRole('button', { name: /← new analysis/i });
      
      await user.tab();
      expect(newAnalysisButton).toHaveFocus();
      
      await user.keyboard('{Enter}');
      expect(mockHandlers.onNewAnalysis).toHaveBeenCalled();
    });

    it('should have proper color contrast for different viability scores', () => {
      const testScores = [30, 60, 85];
      
      testScores.forEach(score => {
        const data = createMockFeasibilityReport({ viabilityScore: score });
        const { rerender } = render(<FeasibilityReport {...defaultProps} data={data} />);
        
        const scoreElement = screen.getByText(score.toString());
        expect(scoreElement).toBeInTheDocument();
        
        // Verify it has appropriate color classes for accessibility
        const hasValidColorClass = scoreElement.className.includes('text-red-600') ||
                                 scoreElement.className.includes('text-yellow-600') ||
                                 scoreElement.className.includes('text-green-600');
        expect(hasValidColorClass).toBe(true);
      });
    });
  });

  describe('Responsive Design', () => {
    it('should handle small screen layouts', () => {
      // Mock small viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });
      
      render(<FeasibilityReport {...defaultProps} />);
      
      // Content should still be visible and accessible
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    it('should adapt button layouts for mobile', () => {
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
        />
      );
      
      // Buttons should have responsive classes
      const buttons = screen.getAllByRole('button');
      const hasResponsiveClasses = buttons.some(button => 
        button.className.includes('sm:') || button.className.includes('md:')
      );
      expect(hasResponsiveClasses).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing or empty data gracefully', () => {
      const minimalData = createMockFeasibilityReport({
        insights: [],
        competitors: [],
        nextSteps: [],
      });
      
      render(<FeasibilityReport {...defaultProps} data={minimalData} />);
      
      expect(screen.getByText('Viability Score')).toBeInTheDocument();
      expect(screen.getByText('0 main competitors')).toBeInTheDocument();
    });

    it('should handle very long product names', () => {
      const longName = 'A'.repeat(200);
      const data = createMockFeasibilityReport({
        productIdea: longName
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      // Should render without breaking layout
      expect(screen.getByText(`${longName} Feasibility Report`)).toBeInTheDocument();
    });

    it('should handle extreme viability scores', () => {
      const testCases = [0, 100, -10, 150];
      
      testCases.forEach(score => {
        const data = createMockFeasibilityReport({ 
          viabilityScore: score 
        });
        
        render(<FeasibilityReport {...defaultProps} data={data} />);
        
        // Should display the score even if extreme
        expect(screen.getByText(score.toString())).toBeInTheDocument();
      });
    });

    it('should handle competitors with extreme ratings', async () => {
      const user = userEvent.setup();
      const data = createMockFeasibilityReport({
        competitors: [
          {
            name: 'Perfect Competitor',
            priceRange: '$50/unit',
            rating: 5.0,
            reviewCount: 10000,
            marketPosition: 'premium'
          },
          {
            name: 'Poor Competitor',
            priceRange: '$1/unit',
            rating: 0.5,
            reviewCount: 1,
            marketPosition: 'economy'
          }
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      await user.click(screen.getByRole('button', { name: /top competitors/i }));
      
      await waitFor(() => {
        expect(screen.getByText('Perfect Competitor')).toBeInTheDocument();
        expect(screen.getByText('Poor Competitor')).toBeInTheDocument();
        expect(screen.getByText('(10000+)')).toBeInTheDocument();
        expect(screen.getByText('(1+)')).toBeInTheDocument();
      });
    });

    it('should handle mixed insight types with custom icons', () => {
      const data = createMockFeasibilityReport({
        insights: [
          { type: 'positive', text: 'Great opportunity', icon: <span data-testid="custom-icon">✅</span> },
          { type: 'warning', text: 'Potential risk' },
          { type: 'neutral', text: 'Market note' },
        ]
      });
      
      render(<FeasibilityReport {...defaultProps} data={data} />);
      
      expect(screen.getByText('Great opportunity')).toBeInTheDocument();
      expect(screen.getByText('Potential risk')).toBeInTheDocument();
      expect(screen.getByText('Market note')).toBeInTheDocument();
    });

    it('should handle pricing section toggle interaction', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const pricingButton = screen.getByRole('button', { name: /view analysis/i });
      
      // Should be clickable and not throw error
      await user.click(pricingButton);
      expect(pricingButton).toBeInTheDocument();
    });

    it('should handle section expansion state correctly', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      const competitorToggle = screen.getByRole('button', { name: /top competitors/i });
      const pricingToggle = screen.getByRole('button', { name: /view analysis/i });
      
      // Expand competitors
      await user.click(competitorToggle);
      await waitFor(() => {
        expect(screen.getByText('Test Competitor')).toBeInTheDocument();
      });
      
      // Click pricing toggle - should not affect competitors
      await user.click(pricingToggle);
      expect(screen.getByText('Test Competitor')).toBeInTheDocument();
      
      // Collapse competitors
      await user.click(competitorToggle);
      await waitFor(() => {
        expect(screen.queryByText('Test Competitor')).not.toBeInTheDocument();
      });
    });
  });

  describe('Data TestIds', () => {
    it('should have all required data-testid attributes', () => {
      render(
        <FeasibilityReport 
          {...defaultProps} 
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
          onNewAnalysis={mockHandlers.onNewAnalysis}
        />
      );
      
      // Main sections
      expect(screen.getByTestId('feasibility-report')).toBeInTheDocument();
      expect(screen.getByTestId('report-header')).toBeInTheDocument();
      expect(screen.getByTestId('report-nav')).toBeInTheDocument();
      expect(screen.getByTestId('report-actions')).toBeInTheDocument();
      expect(screen.getByTestId('report-title')).toBeInTheDocument();
      expect(screen.getByTestId('report-timestamp')).toBeInTheDocument();
      
      // Score section
      expect(screen.getByTestId('viability-insights-section')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score-card')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score-title')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score-chart')).toBeInTheDocument();
      expect(screen.getByTestId('score-circle')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score-value')).toBeInTheDocument();
      expect(screen.getByTestId('viability-score-label')).toBeInTheDocument();
      
      // Insights section
      expect(screen.getByTestId('key-insights-card')).toBeInTheDocument();
      expect(screen.getByTestId('key-insights-title')).toBeInTheDocument();
      expect(screen.getByTestId('insights-list')).toBeInTheDocument();
      
      // Market analysis
      expect(screen.getByTestId('market-analysis-section')).toBeInTheDocument();
      expect(screen.getByTestId('market-analysis-title')).toBeInTheDocument();
      expect(screen.getByTestId('market-metrics')).toBeInTheDocument();
      
      // Action buttons
      expect(screen.getByTestId('new-analysis-button')).toBeInTheDocument();
      expect(screen.getByTestId('share-button')).toBeInTheDocument();
      expect(screen.getByTestId('export-button')).toBeInTheDocument();
    });

    it('should have testids for market metrics', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByTestId('market-size-metric')).toBeInTheDocument();
      expect(screen.getByTestId('market-size-label')).toBeInTheDocument();
      expect(screen.getByTestId('market-size-value')).toBeInTheDocument();
      expect(screen.getByTestId('market-size-description')).toBeInTheDocument();
      
      expect(screen.getByTestId('growth-rate-metric')).toBeInTheDocument();
      expect(screen.getByTestId('growth-rate-label')).toBeInTheDocument();
      expect(screen.getByTestId('growth-rate-value')).toBeInTheDocument();
      expect(screen.getByTestId('growth-rate-description')).toBeInTheDocument();
      
      expect(screen.getByTestId('competition-level-metric')).toBeInTheDocument();
      expect(screen.getByTestId('competition-level-label')).toBeInTheDocument();
      expect(screen.getByTestId('competition-level-value')).toBeInTheDocument();
      expect(screen.getByTestId('competitors-count')).toBeInTheDocument();
    });

    it('should have testids for competitors section', async () => {
      const user = userEvent.setup();
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByTestId('competitors-section')).toBeInTheDocument();
      expect(screen.getByTestId('competitors-toggle')).toBeInTheDocument();
      expect(screen.getByTestId('competitors-title')).toBeInTheDocument();
      expect(screen.getByTestId('competitors-toggle-icon')).toBeInTheDocument();
      
      // Expand to see competitor details
      await user.click(screen.getByTestId('competitors-toggle'));
      
      await waitFor(() => {
        expect(screen.getByTestId('competitors-list')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-name-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-price-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-rating-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-stars-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-review-count-0')).toBeInTheDocument();
        expect(screen.getByTestId('competitor-position-0')).toBeInTheDocument();
      });
    });

    it('should have testids for next steps section', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByTestId('next-steps-section')).toBeInTheDocument();
      expect(screen.getByTestId('next-steps-title')).toBeInTheDocument();
      expect(screen.getByTestId('next-steps-list')).toBeInTheDocument();
      
      // Test individual step testids
      expect(screen.getByTestId('next-step-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('step-number-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('step-title-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('step-time-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('step-description-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('step-action-test-step')).toBeInTheDocument();
      expect(screen.getByTestId('start-step-button-test-step')).toBeInTheDocument();
    });

    it('should have testids for upgrade CTA section', () => {
      render(<FeasibilityReport {...defaultProps} />);
      
      expect(screen.getByTestId('upgrade-cta')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-title')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-description')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-features')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-features-left')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-features-right')).toBeInTheDocument();
      expect(screen.getByTestId('upgrade-button')).toBeInTheDocument();
      expect(screen.getByTestId('guarantee-text')).toBeInTheDocument();
      
      // Feature testids
      expect(screen.getByTestId('feature-suppliers')).toBeInTheDocument();
      expect(screen.getByTestId('feature-branding')).toBeInTheDocument();
      expect(screen.getByTestId('feature-website')).toBeInTheDocument();
      expect(screen.getByTestId('feature-financials')).toBeInTheDocument();
      expect(screen.getByTestId('feature-legal')).toBeInTheDocument();
      expect(screen.getByTestId('feature-checklist')).toBeInTheDocument();
    });
  });

  describe('Component Lifecycle', () => {
    it('should forward ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<FeasibilityReport {...defaultProps} ref={ref} />);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current).toHaveAttribute('data-testid', 'feasibility-report');
    });

    it('should have proper displayName', () => {
      expect(FeasibilityReport.displayName).toBe('FeasibilityReport');
    });

    it('should update when data changes', () => {
      const initialData = createMockFeasibilityReport({ viabilityScore: 50 });
      const updatedData = createMockFeasibilityReport({ viabilityScore: 90 });
      
      const { rerender } = render(<FeasibilityReport {...defaultProps} data={initialData} />);
      
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('MODERATE POTENTIAL')).toBeInTheDocument();
      
      rerender(<FeasibilityReport {...defaultProps} data={updatedData} />);
      
      expect(screen.getByText('90')).toBeInTheDocument();
      expect(screen.getByText('VIABLE CONCEPT')).toBeInTheDocument();
    });
  });
});