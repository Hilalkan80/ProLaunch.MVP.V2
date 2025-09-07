import React from 'react';
import { render, createMockFeasibilityReport, createMockProcessingSteps } from './testUtils';
import { ProductIdeaForm } from '../ProductIdeaForm';
import { ProcessingView } from '../ProcessingView';
import { FeasibilityReport } from '../FeasibilityReport';
import { LoadingSpinner, ProgressBar, LoadingDots, Skeleton, TypingIndicator, PulseLoader } from '../LoadingStates';
import { ErrorMessage, NetworkError, ProcessingError, EmptyState } from '../ErrorStates';
import { M0Container } from '../M0Container';

// Mock Date for consistent snapshots
const mockDate = new Date('2023-12-25T10:30:00.000Z');
const originalDate = global.Date;

beforeAll(() => {
  global.Date = class extends Date {
    constructor(...args: any[]) {
      if (args.length === 0) {
        super(mockDate);
      } else {
        super(...args);
      }
    }
    
    static now() {
      return mockDate.getTime();
    }
  } as any;
});

afterAll(() => {
  global.Date = originalDate;
});

// Mock handlers for components that require them
const mockHandlers = {
  onSubmit: jest.fn(),
  onCancel: jest.fn(),
  onRetry: jest.fn(),
  onStartOver: jest.fn(),
  onStartNextStep: jest.fn(),
  onUpgrade: jest.fn(),
  onShare: jest.fn(),
  onExport: jest.fn(),
  onNewAnalysis: jest.fn(),
  onAnalysisComplete: jest.fn(),
  onContactSupport: jest.fn(),
  onDismiss: jest.fn(),
};

describe('M0 Component Snapshots', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('ProductIdeaForm Snapshots', () => {
    it('should match snapshot in default state', () => {
      const { container } = render(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />
      );
      expect(container.firstChild).toMatchSnapshot('ProductIdeaForm-default');
    });

    it('should match snapshot with custom placeholder', () => {
      const { container } = render(
        <ProductIdeaForm 
          onSubmit={mockHandlers.onSubmit} 
          placeholder="Custom placeholder text for testing"
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProductIdeaForm-custom-placeholder');
    });

    it('should match snapshot in loading state', () => {
      const { container } = render(
        <ProductIdeaForm 
          onSubmit={mockHandlers.onSubmit} 
          isLoading={true}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProductIdeaForm-loading');
    });

    it('should match snapshot with validation error', () => {
      // This would require triggering validation error state
      // For now, we'll test the base form structure
      const { container } = render(
        <ProductIdeaForm onSubmit={mockHandlers.onSubmit} />
      );
      expect(container.firstChild).toMatchSnapshot('ProductIdeaForm-validation-ready');
    });
  });

  describe('ProcessingView Snapshots', () => {
    const defaultProps = {
      productIdea: 'Organic dog treats for health-conscious pet owners',
      steps: createMockProcessingSteps(),
      currentStepIndex: 1,
      overallProgress: 33,
    };

    it('should match snapshot in default processing state', () => {
      const { container } = render(<ProcessingView {...defaultProps} />);
      expect(container.firstChild).toMatchSnapshot('ProcessingView-default');
    });

    it('should match snapshot with cancel button', () => {
      const { container } = render(
        <ProcessingView 
          {...defaultProps} 
          onCancel={mockHandlers.onCancel}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-with-cancel');
    });

    it('should match snapshot with completed steps', () => {
      const stepsWithCompletion = defaultProps.steps.map((step, index) => ({
        ...step,
        status: index < 2 ? 'completed' as const : index === 2 ? 'processing' as const : 'pending' as const
      }));

      const { container } = render(
        <ProcessingView 
          {...defaultProps} 
          steps={stepsWithCompletion}
          currentStepIndex={2}
          overallProgress={66}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-with-completed-steps');
    });

    it('should match snapshot with error state', () => {
      const stepsWithError = defaultProps.steps.map((step, index) => ({
        ...step,
        status: index === 1 ? 'error' as const : index === 0 ? 'completed' as const : 'pending' as const
      }));

      const { container } = render(
        <ProcessingView 
          {...defaultProps} 
          steps={stepsWithError}
          currentStepIndex={1}
          overallProgress={16}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-with-error');
    });

    it('should match snapshot with long product idea', () => {
      const longIdea = 'A'.repeat(100) + ' smart pet feeding system with advanced features';
      
      const { container } = render(
        <ProcessingView 
          {...defaultProps} 
          productIdea={longIdea}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-long-product-idea');
    });
  });

  describe('FeasibilityReport Snapshots', () => {
    const reportData = createMockFeasibilityReport();
    const defaultProps = {
      data: reportData,
      onStartNextStep: mockHandlers.onStartNextStep,
      onUpgrade: mockHandlers.onUpgrade,
    };

    it('should match snapshot in default state', () => {
      const { container } = render(<FeasibilityReport {...defaultProps} />);
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-default');
    });

    it('should match snapshot with all optional handlers', () => {
      const { container } = render(
        <FeasibilityReport 
          {...defaultProps}
          onShare={mockHandlers.onShare}
          onExport={mockHandlers.onExport}
          onNewAnalysis={mockHandlers.onNewAnalysis}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-with-handlers');
    });

    it('should match snapshot with high viability score', () => {
      const highScoreData = createMockFeasibilityReport({
        viabilityScore: 92,
        competitionLevel: 'low',
      });

      const { container } = render(
        <FeasibilityReport 
          {...defaultProps} 
          data={highScoreData}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-high-score');
    });

    it('should match snapshot with low viability score', () => {
      const lowScoreData = createMockFeasibilityReport({
        viabilityScore: 25,
        competitionLevel: 'high',
        insights: [
          { type: 'warning', text: 'High market saturation' },
          { type: 'warning', text: 'Significant regulatory challenges' },
          { type: 'neutral', text: 'Mixed customer feedback' },
        ]
      });

      const { container } = render(
        <FeasibilityReport 
          {...defaultProps} 
          data={lowScoreData}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-low-score');
    });

    it('should match snapshot with no competitors', () => {
      const noCompetitorsData = createMockFeasibilityReport({
        competitors: [],
        competitionLevel: 'low',
      });

      const { container } = render(
        <FeasibilityReport 
          {...defaultProps} 
          data={noCompetitorsData}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-no-competitors');
    });

    it('should match snapshot with many next steps', () => {
      const manyStepsData = createMockFeasibilityReport({
        nextSteps: Array.from({ length: 6 }, (_, i) => ({
          id: `step-${i + 1}`,
          title: `Step ${i + 1} Title`,
          description: `Description for step ${i + 1}`,
          isUnlocked: i < 2,
          order: i + 1,
          estimatedTime: i % 2 === 0 ? '15 minutes' : undefined,
        }))
      });

      const { container } = render(
        <FeasibilityReport 
          {...defaultProps} 
          data={manyStepsData}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-many-steps');
    });
  });

  describe('LoadingStates Snapshots', () => {
    it('should match LoadingSpinner snapshots in different sizes', () => {
      const sizes: Array<'sm' | 'md' | 'lg'> = ['sm', 'md', 'lg'];
      
      sizes.forEach(size => {
        const { container } = render(<LoadingSpinner size={size} />);
        expect(container.firstChild).toMatchSnapshot(`LoadingSpinner-${size}`);
      });
    });

    it('should match ProgressBar snapshots with different values', () => {
      const testCases = [
        { progress: 0, label: 'empty' },
        { progress: 25, label: 'quarter' },
        { progress: 50, label: 'half' },
        { progress: 75, label: 'three-quarters' },
        { progress: 100, label: 'full' },
      ];
      
      testCases.forEach(({ progress, label }) => {
        const { container } = render(<ProgressBar progress={progress} />);
        expect(container.firstChild).toMatchSnapshot(`ProgressBar-${label}`);
      });
    });

    it('should match ProgressBar snapshots with different colors', () => {
      const colors: Array<'blue' | 'green' | 'yellow' | 'red'> = ['blue', 'green', 'yellow', 'red'];
      
      colors.forEach(color => {
        const { container } = render(<ProgressBar progress={60} color={color} />);
        expect(container.firstChild).toMatchSnapshot(`ProgressBar-${color}`);
      });
    });

    it('should match ProgressBar snapshot without percentage', () => {
      const { container } = render(<ProgressBar progress={45} showPercentage={false} />);
      expect(container.firstChild).toMatchSnapshot('ProgressBar-no-percentage');
    });

    it('should match LoadingDots snapshots in different sizes', () => {
      const sizes: Array<'sm' | 'md' | 'lg'> = ['sm', 'md', 'lg'];
      
      sizes.forEach(size => {
        const { container } = render(<LoadingDots size={size} />);
        expect(container.firstChild).toMatchSnapshot(`LoadingDots-${size}`);
      });
    });

    it('should match Skeleton snapshots with different configurations', () => {
      const configs = [
        { lines: 1, height: 'h-4', label: 'single-line' },
        { lines: 3, height: 'h-4', label: 'three-lines' },
        { lines: 2, height: 'h-6', label: 'two-lines-tall' },
        { lines: 5, height: 'h-3', label: 'five-lines-short' },
      ];
      
      configs.forEach(({ lines, height, label }) => {
        const { container } = render(<Skeleton lines={lines} height={height} />);
        expect(container.firstChild).toMatchSnapshot(`Skeleton-${label}`);
      });
    });

    it('should match TypingIndicator snapshot', () => {
      const { container } = render(<TypingIndicator />);
      expect(container.firstChild).toMatchSnapshot('TypingIndicator-default');
    });

    it('should match PulseLoader snapshots', () => {
      const configs = [
        { size: 'sm', color: 'blue', label: 'small-blue' },
        { size: 'md', color: 'green', label: 'medium-green' },
        { size: 'lg', color: 'gray', label: 'large-gray' },
      ] as const;
      
      configs.forEach(({ size, color, label }) => {
        const { container } = render(<PulseLoader size={size} color={color} />);
        expect(container.firstChild).toMatchSnapshot(`PulseLoader-${label}`);
      });
    });
  });

  describe('ErrorStates Snapshots', () => {
    it('should match ErrorMessage snapshots for different types', () => {
      const types: Array<'error' | 'warning' | 'info'> = ['error', 'warning', 'info'];
      
      types.forEach(type => {
        const { container } = render(
          <ErrorMessage 
            message={`This is a ${type} message for testing`}
            type={type}
            onRetry={mockHandlers.onRetry}
            onDismiss={mockHandlers.onDismiss}
          />
        );
        expect(container.firstChild).toMatchSnapshot(`ErrorMessage-${type}`);
      });
    });

    it('should match ErrorMessage snapshot with custom title and no actions', () => {
      const { container } = render(
        <ErrorMessage 
          title="Custom Error Title"
          message="This is a custom error message without action buttons"
          type="error"
        />
      );
      expect(container.firstChild).toMatchSnapshot('ErrorMessage-custom-no-actions');
    });

    it('should match NetworkError snapshot', () => {
      const { container } = render(
        <NetworkError onRetry={mockHandlers.onRetry} />
      );
      expect(container.firstChild).toMatchSnapshot('NetworkError-default');
    });

    it('should match ProcessingError snapshots', () => {
      const { container } = render(
        <ProcessingError 
          productIdea="Smart home automation system"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingError-basic');
    });

    it('should match ProcessingError snapshot with all features', () => {
      const { container } = render(
        <ProcessingError 
          productIdea="Advanced AI-powered productivity app"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
          onContactSupport={mockHandlers.onContactSupport}
          errorDetails="Network timeout: Connection failed after 30 seconds. Stack trace: Error at line 42..."
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingError-full-features');
    });

    it('should match ProcessingError snapshot with long product name', () => {
      const longProductIdea = 'Revolutionary blockchain-based decentralized autonomous organization management platform with advanced AI integration and multi-chain compatibility';
      
      const { container } = render(
        <ProcessingError 
          productIdea={longProductIdea}
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingError-long-name');
    });

    it('should match EmptyState snapshots', () => {
      const { container } = render(
        <EmptyState message="No data available at this time" />
      );
      expect(container.firstChild).toMatchSnapshot('EmptyState-basic');
    });

    it('should match EmptyState snapshot with title and action', () => {
      const { container } = render(
        <EmptyState 
          title="No Results Found"
          message="Try adjusting your search criteria or browse our categories"
          action={{
            label: 'Browse Categories',
            onClick: mockHandlers.onSubmit
          }}
        />
      );
      expect(container.firstChild).toMatchSnapshot('EmptyState-with-action');
    });

    it('should match EmptyState snapshot with custom icon', () => {
      const customIcon = (
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
          <span className="text-blue-600 text-2xl">📊</span>
        </div>
      );

      const { container } = render(
        <EmptyState 
          title="No Analytics Data"
          message="Start tracking to see your analytics dashboard"
          icon={customIcon}
        />
      );
      expect(container.firstChild).toMatchSnapshot('EmptyState-custom-icon');
    });
  });

  describe('M0Container Snapshots', () => {
    it('should match snapshot in initial state', () => {
      const { container } = render(<M0Container />);
      expect(container.firstChild).toMatchSnapshot('M0Container-initial');
    });

    it('should match snapshot with all handlers provided', () => {
      const { container } = render(
        <M0Container 
          onUpgrade={mockHandlers.onUpgrade}
          onStartNextStep={mockHandlers.onStartNextStep}
          onAnalysisComplete={mockHandlers.onAnalysisComplete}
          className="test-container-class"
        />
      );
      expect(container.firstChild).toMatchSnapshot('M0Container-with-handlers');
    });
  });

  describe('Responsive Design Snapshots', () => {
    // Note: These tests would ideally use different viewport sizes
    // For now, we'll test the base responsive classes
    
    it('should match responsive layout snapshots', () => {
      const { container } = render(
        <FeasibilityReport 
          data={createMockFeasibilityReport()}
          onStartNextStep={mockHandlers.onStartNextStep}
          onUpgrade={mockHandlers.onUpgrade}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-responsive');
    });

    it('should match mobile-friendly button layouts', () => {
      const { container } = render(
        <ProcessingError 
          productIdea="Mobile layout test"
          onRetry={mockHandlers.onRetry}
          onStartOver={mockHandlers.onStartOver}
          onContactSupport={mockHandlers.onContactSupport}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingError-mobile-layout');
    });
  });

  describe('Theme Variations Snapshots', () => {
    it('should match different viability score themes', () => {
      const scoreVariations = [
        { score: 95, label: 'excellent' },
        { score: 75, label: 'good' },
        { score: 55, label: 'moderate' },
        { score: 25, label: 'poor' },
      ];
      
      scoreVariations.forEach(({ score, label }) => {
        const data = createMockFeasibilityReport({ viabilityScore: score });
        const { container } = render(
          <FeasibilityReport 
            data={data}
            onStartNextStep={mockHandlers.onStartNextStep}
            onUpgrade={mockHandlers.onUpgrade}
          />
        );
        expect(container.firstChild).toMatchSnapshot(`FeasibilityReport-score-${label}`);
      });
    });

    it('should match different competition level themes', () => {
      const competitionLevels: Array<'low' | 'moderate' | 'high'> = ['low', 'moderate', 'high'];
      
      competitionLevels.forEach(level => {
        const data = createMockFeasibilityReport({ competitionLevel: level });
        const { container } = render(
          <FeasibilityReport 
            data={data}
            onStartNextStep={mockHandlers.onStartNextStep}
            onUpgrade={mockHandlers.onUpgrade}
          />
        );
        expect(container.firstChild).toMatchSnapshot(`FeasibilityReport-competition-${level}`);
      });
    });
  });

  describe('Edge Case Snapshots', () => {
    it('should match snapshot with minimal data', () => {
      const minimalData = createMockFeasibilityReport({
        insights: [],
        competitors: [],
        nextSteps: [],
      });
      
      const { container } = render(
        <FeasibilityReport 
          data={minimalData}
          onStartNextStep={mockHandlers.onStartNextStep}
          onUpgrade={mockHandlers.onUpgrade}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-minimal-data');
    });

    it('should match snapshot with maximum data', () => {
      const maximalData = createMockFeasibilityReport({
        insights: Array.from({ length: 8 }, (_, i) => ({
          type: (['positive', 'warning', 'neutral'] as const)[i % 3],
          text: `Insight number ${i + 1} with detailed information about the market analysis`
        })),
        competitors: Array.from({ length: 10 }, (_, i) => ({
          name: `Competitor ${i + 1} Inc.`,
          priceRange: `$${10 + i}-${15 + i}/unit`,
          rating: 3.5 + (i * 0.1),
          reviewCount: 100 + (i * 50),
          marketPosition: (['economy', 'premium', 'ultra-premium'] as const)[i % 3],
        })),
        nextSteps: Array.from({ length: 8 }, (_, i) => ({
          id: `max-step-${i + 1}`,
          title: `Comprehensive Step ${i + 1}`,
          description: `Detailed description for step ${i + 1} with comprehensive information`,
          isUnlocked: i < 3,
          order: i + 1,
          estimatedTime: i % 2 === 0 ? `${15 + (i * 5)} minutes` : undefined,
        }))
      });
      
      const { container } = render(
        <FeasibilityReport 
          data={maximalData}
          onStartNextStep={mockHandlers.onStartNextStep}
          onUpgrade={mockHandlers.onUpgrade}
        />
      );
      expect(container.firstChild).toMatchSnapshot('FeasibilityReport-maximal-data');
    });

    it('should match snapshot with empty steps array', () => {
      const { container } = render(
        <ProcessingView 
          productIdea="Test with no steps"
          steps={[]}
          currentStepIndex={0}
          overallProgress={0}
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-no-steps');
    });

    it('should match snapshot with extreme progress values', () => {
      const { container } = render(
        <ProcessingView 
          productIdea="Extreme progress test"
          steps={createMockProcessingSteps()}
          currentStepIndex={10} // Beyond array bounds
          overallProgress={150} // Over 100%
        />
      );
      expect(container.firstChild).toMatchSnapshot('ProcessingView-extreme-values');
    });
  });

  describe('Animation State Snapshots', () => {
    it('should match snapshot with disabled animations', () => {
      // Animations are disabled in test environment by default
      const { container } = render(<LoadingSpinner />);
      expect(container.firstChild).toMatchSnapshot('LoadingSpinner-no-animations');
    });

    it('should match snapshot of progress bar at various stages', () => {
      const progressValues = [0, 15, 33, 50, 67, 85, 100];
      
      progressValues.forEach(progress => {
        const { container } = render(
          <ProgressBar progress={progress} />
        );
        expect(container.firstChild).toMatchSnapshot(`ProgressBar-${progress}percent`);
      });
    });
  });
});