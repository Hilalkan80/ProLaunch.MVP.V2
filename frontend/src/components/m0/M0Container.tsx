import { forwardRef, useState, useCallback, useEffect } from 'react';
import { ProductIdeaForm } from './ProductIdeaForm';
import { ProcessingView } from './ProcessingView';
import { FeasibilityReport, FeasibilityReportData } from './FeasibilityReport';
import { ProcessingError, NetworkError } from './ErrorStates';
import { ShareButton, ExportButton } from './ShareComponents';
import { FadeIn, SlideIn, ScaleIn } from './AnimatedTransitions';

interface ProcessingStep {
  id: string;
  label: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  duration?: number;
}

type M0State = 'input' | 'processing' | 'success' | 'error' | 'network-error';

interface M0ContainerProps {
  onUpgrade?: () => void;
  onStartNextStep?: (stepId: string) => void;
  onAnalysisComplete?: (data: FeasibilityReportData) => void;
  className?: string;
}

export const M0Container = forwardRef<HTMLDivElement, M0ContainerProps>(
  ({ onUpgrade, onStartNextStep, onAnalysisComplete, className = '' }, ref) => {
    const [currentState, setCurrentState] = useState<M0State>('input');
    const [productIdea, setProductIdea] = useState('');
    const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [overallProgress, setOverallProgress] = useState(0);
    const [reportData, setReportData] = useState<FeasibilityReportData | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Initialize processing steps
    const initializeSteps = useCallback(() => {
      const steps: ProcessingStep[] = [
        {
          id: 'market-research',
          label: 'Market Research',
          description: 'Analyzing market size and growth trends',
          status: 'pending',
          duration: 15
        },
        {
          id: 'competitor-analysis',
          label: 'Competitor Analysis',
          description: 'Identifying and analyzing key competitors',
          status: 'pending',
          duration: 20
        },
        {
          id: 'pricing-analysis',
          label: 'Pricing Analysis',
          description: 'Determining optimal pricing strategy',
          status: 'pending',
          duration: 10
        },
        {
          id: 'demand-validation',
          label: 'Demand Validation',
          description: 'Assessing market demand and consumer interest',
          status: 'pending',
          duration: 15
        },
        {
          id: 'risk-assessment',
          label: 'Risk Assessment',
          description: 'Evaluating potential challenges and risks',
          status: 'pending',
          duration: 10
        },
        {
          id: 'viability-scoring',
          label: 'Viability Scoring',
          description: 'Calculating overall feasibility score',
          status: 'pending',
          duration: 5
        }
      ];
      setProcessingSteps(steps);
    }, []);

    // Simulate processing steps
    const simulateProcessing = useCallback(async () => {
      const steps = [...processingSteps];
      
      for (let i = 0; i < steps.length; i++) {
        setCurrentStepIndex(i);
        
        // Update current step to processing
        steps[i] = { ...steps[i], status: 'processing' };
        setProcessingSteps([...steps]);
        
        // Simulate processing time
        const duration = steps[i].duration || 10;
        await new Promise(resolve => setTimeout(resolve, duration * 100)); // Speed up for demo
        
        // Complete current step
        steps[i] = { ...steps[i], status: 'completed' };
        setProcessingSteps([...steps]);
        
        // Update overall progress
        const newProgress = ((i + 1) / steps.length) * 100;
        setOverallProgress(newProgress);
        
        // Small delay between steps
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      // Generate mock report data
      const mockReportData: FeasibilityReportData = {
        productIdea: productIdea,
        viabilityScore: 78,
        marketSize: '$2.1B',
        growthRate: '15% YoY',
        competitionLevel: 'moderate',
        insights: [
          {
            type: 'positive',
            text: 'Strong market demand with 15% annual growth'
          },
          {
            type: 'positive',
            text: 'Reasonable competition with 5 main brands'
          },
          {
            type: 'positive',
            text: 'Healthy profit margins possible'
          },
          {
            type: 'warning',
            text: 'Premium positioning required'
          },
          {
            type: 'warning',
            text: 'Supply chain complexity'
          }
        ],
        competitors: [
          {
            name: 'Blue Buffalo Wilderness',
            priceRange: '$15-18/lb',
            rating: 4.2,
            reviewCount: 850,
            marketPosition: 'premium'
          },
          {
            name: "Zuke's Natural Training",
            priceRange: '$12-15/lb',
            rating: 4.4,
            reviewCount: 1200,
            marketPosition: 'premium'
          },
          {
            name: 'Wellness CORE Pure Rewards',
            priceRange: '$14-16/lb',
            rating: 4.1,
            reviewCount: 680,
            marketPosition: 'premium'
          }
        ],
        recommendedPriceRange: '$18-24/lb',
        nextSteps: [
          {
            id: 'm1-unit-economics',
            title: 'Analyze Unit Economics (M1)',
            description: 'Understand true costs and profit margins',
            isUnlocked: true,
            order: 1,
            estimatedTime: '15 minutes'
          },
          {
            id: 'm2-deep-research',
            title: 'Deep Market Research (M2)',
            description: 'Get 10+ competitor analysis and demand validation',
            isUnlocked: false,
            order: 2
          },
          {
            id: 'm3-suppliers',
            title: 'Find Verified Suppliers (M3)',
            description: 'Connect with 3-5 organic treat manufacturers',
            isUnlocked: false,
            order: 3
          },
          {
            id: 'm4-financials',
            title: 'Build Financial Model (M4)',
            description: 'Create 36-month projections for investors',
            isUnlocked: false,
            order: 4
          }
        ],
        generatedAt: new Date()
      };
      
      setReportData(mockReportData);
      setCurrentState('success');
      
      if (onAnalysisComplete) {
        onAnalysisComplete(mockReportData);
      }
    }, [processingSteps, productIdea, onAnalysisComplete]);

    // Handle form submission
    const handleFormSubmit = useCallback(async (data: { productIdea: string }) => {
      try {
        setProductIdea(data.productIdea);
        setCurrentState('processing');
        setError(null);
        initializeSteps();
        setCurrentStepIndex(0);
        setOverallProgress(0);
        
        // Start processing simulation
        await simulateProcessing();
      } catch (err) {
        console.error('Processing error:', err);
        setError(err instanceof Error ? err.message : 'An unexpected error occurred');
        setCurrentState('error');
      }
    }, [initializeSteps, simulateProcessing]);

    // Handle retry
    const handleRetry = useCallback(() => {
      if (productIdea) {
        handleFormSubmit({ productIdea });
      } else {
        setCurrentState('input');
      }
    }, [productIdea, handleFormSubmit]);

    // Handle starting over
    const handleStartOver = useCallback(() => {
      setCurrentState('input');
      setProductIdea('');
      setReportData(null);
      setError(null);
      setOverallProgress(0);
      setCurrentStepIndex(0);
    }, []);

    // Handle cancel
    const handleCancel = useCallback(() => {
      setCurrentState('input');
    }, []);

    // Handle share
    const handleShare = useCallback(() => {
      if (reportData) {
        const url = `${window.location.origin}/report/${btoa(reportData.productIdea)}`;
        return url;
      }
      return '';
    }, [reportData]);

    // Handle export
    const handleExportPDF = useCallback(() => {
      if (reportData) {
        // Mock PDF export
        console.log('Exporting PDF for:', reportData.productIdea);
        // In a real implementation, you'd generate and download the PDF
      }
    }, [reportData]);

    const handleExportJSON = useCallback(() => {
      if (reportData) {
        const dataStr = JSON.stringify(reportData, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `${reportData.productIdea.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_report.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
      }
    }, [reportData]);

    // Auto-retry on network error
    useEffect(() => {
      let retryTimer: NodeJS.Timeout;
      
      if (currentState === 'network-error') {
        retryTimer = setTimeout(() => {
          handleRetry();
        }, 5000);
      }
      
      return () => {
        if (retryTimer) {
          clearTimeout(retryTimer);
        }
      };
    }, [currentState, handleRetry]);

    return (
      <div ref={ref} className={`min-h-screen bg-gray-50 ${className}`} data-testid="m0-container">
        <div className="container mx-auto px-4 py-8" data-testid="m0-content">
          {currentState === 'input' && (
            <FadeIn className="max-w-2xl mx-auto" data-testid="input-state">
              <SlideIn direction="up" delay={200} className="text-center mb-8" data-testid="hero-section">
                <h1 className="text-3xl font-bold text-gray-900 mb-4" data-testid="hero-title">
                  AI Co-Pilot for Ecommerce Validation
                </h1>
                <p className="text-lg text-gray-600" data-testid="hero-description">
                  Transform fuzzy ideas into launch-ready businesses in 9 milestones
                </p>
              </SlideIn>
              
              <ScaleIn delay={400} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6" data-testid="form-container">
                <ProductIdeaForm
                  onSubmit={handleFormSubmit}
                  isLoading={false}
                />
              </ScaleIn>
              
              {/* Social proof section */}
              <FadeIn delay={600} className="mt-8 text-center" data-testid="social-proof">
                <div className="text-sm text-gray-500 mb-4" data-testid="social-proof-tagline">
                  Trusted by entrepreneurs worldwide
                </div>
                <div className="flex items-center justify-center space-x-6 text-sm text-gray-600" data-testid="social-proof-stats">
                  <div className="flex items-center space-x-1" data-testid="rating-stat">
                    <span className="text-yellow-400" data-testid="rating-stars">⭐⭐⭐⭐⭐</span>
                    <span data-testid="rating-value">4.8/5 rating</span>
                  </div>
                  <div data-testid="validation-stat">2,847 businesses validated this month</div>
                </div>
              </FadeIn>
            </FadeIn>
          )}

          {currentState === 'processing' && (
            <FadeIn data-testid="processing-state">
              <ProcessingView
                productIdea={productIdea}
                steps={processingSteps}
                currentStepIndex={currentStepIndex}
                overallProgress={overallProgress}
                onCancel={handleCancel}
              />
            </FadeIn>
          )}

          {currentState === 'success' && reportData && (
            <SlideIn direction="up" duration={600} data-testid="success-state">
              <FeasibilityReport
                data={reportData}
                onStartNextStep={onStartNextStep || (() => {})}
                onUpgrade={onUpgrade || (() => {})}
                onShare={handleShare() ? () => window.open(handleShare()) : undefined}
                onExport={handleExportPDF}
                onNewAnalysis={handleStartOver}
              />
            </SlideIn>
          )}

          {currentState === 'error' && (
            <ScaleIn initialScale={0.9} data-testid="error-state">
              <ProcessingError
                productIdea={productIdea}
                onRetry={handleRetry}
                onStartOver={handleStartOver}
                errorDetails={error || undefined}
              />
            </ScaleIn>
          )}

          {currentState === 'network-error' && (
            <FadeIn className="max-w-2xl mx-auto" data-testid="network-error-state">
              <NetworkError
                onRetry={handleRetry}
              />
            </FadeIn>
          )}
        </div>
      </div>
    );
  }
);

M0Container.displayName = 'M0Container';