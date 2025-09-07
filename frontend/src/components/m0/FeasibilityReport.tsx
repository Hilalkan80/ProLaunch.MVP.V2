import { forwardRef, useState } from 'react';
import { Button } from '../ui/Button';

interface CompetitorData {
  name: string;
  priceRange: string;
  rating: number;
  reviewCount: number;
  marketPosition: 'economy' | 'premium' | 'ultra-premium';
}

interface MarketInsight {
  type: 'positive' | 'warning' | 'neutral';
  text: string;
  icon?: React.ReactNode;
}

interface NextStep {
  id: string;
  title: string;
  description: string;
  isUnlocked: boolean;
  order: number;
  estimatedTime?: string;
}

interface FeasibilityReportData {
  productIdea: string;
  viabilityScore: number;
  marketSize: string;
  growthRate: string;
  competitionLevel: 'low' | 'moderate' | 'high';
  insights: MarketInsight[];
  competitors: CompetitorData[];
  recommendedPriceRange: string;
  nextSteps: NextStep[];
  generatedAt: Date;
}

interface FeasibilityReportProps {
  data: FeasibilityReportData;
  onStartNextStep: (stepId: string) => void;
  onUpgrade: () => void;
  onShare?: () => void;
  onExport?: () => void;
  onNewAnalysis?: () => void;
  className?: string;
}

export const FeasibilityReport = forwardRef<HTMLDivElement, FeasibilityReportProps>(
  ({ 
    data, 
    onStartNextStep, 
    onUpgrade, 
    onShare, 
    onExport, 
    onNewAnalysis,
    className = '' 
  }, ref) => {
    const [expandedSection, setExpandedSection] = useState<string | null>(null);

    const getViabilityColor = (score: number) => {
      if (score >= 70) return 'text-green-600';
      if (score >= 50) return 'text-yellow-600';
      return 'text-red-600';
    };

    const getViabilityBg = (score: number) => {
      if (score >= 70) return 'bg-green-600';
      if (score >= 50) return 'bg-yellow-500';
      return 'bg-red-600';
    };

    const getViabilityLabel = (score: number) => {
      if (score >= 70) return 'VIABLE CONCEPT';
      if (score >= 50) return 'MODERATE POTENTIAL';
      return 'HIGH RISK';
    };

    const getInsightIcon = (type: MarketInsight['type']) => {
      switch (type) {
        case 'positive':
          return (
            <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          );
        case 'warning':
          return (
            <div className="w-5 h-5 bg-yellow-100 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
          );
        default:
          return (
            <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
          );
      }
    };

    const toggleSection = (section: string) => {
      setExpandedSection(expandedSection === section ? null : section);
    };

    return (
      <div ref={ref} className={`w-full max-w-6xl mx-auto p-6 space-y-8 ${className}`} data-testid="feasibility-report">
        {/* Header */}
        <div className="text-center mb-8" data-testid="report-header">
          <div className="flex items-center justify-between mb-4" data-testid="report-nav">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={onNewAnalysis}
              className="text-gray-600"
              data-testid="new-analysis-button"
            >
              ← New Analysis
            </Button>
            
            <div className="flex items-center space-x-2" data-testid="report-actions">
              {onShare && (
                <Button variant="ghost" size="sm" onClick={onShare} data-testid="share-button">
                  Share
                </Button>
              )}
              {onExport && (
                <Button variant="ghost" size="sm" onClick={onExport} data-testid="export-button">
                  Export
                </Button>
              )}
            </div>
          </div>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2" data-testid="report-title">
            {data.productIdea} Feasibility Report
          </h1>
          
          <p className="text-gray-600" data-testid="report-timestamp">
            Generated: {data.generatedAt.toLocaleDateString()} • {data.generatedAt.toLocaleTimeString()}
          </p>
        </div>

        {/* Viability Score & Key Insights */}
        <div className="grid md:grid-cols-2 gap-6 mb-8" data-testid="viability-insights-section">
          {/* Viability Score */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 text-center" data-testid="viability-score-card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4" data-testid="viability-score-title">Viability Score</h2>
            
            <div className="relative w-32 h-32 mx-auto mb-4" data-testid="viability-score-chart">
              <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 36 36" data-testid="score-circle">
                <path
                  className="text-gray-200"
                  stroke="currentColor"
                  strokeWidth="2"
                  fill="transparent"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className={getViabilityColor(data.viabilityScore)}
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeDasharray={`${data.viabilityScore}, 100`}
                  strokeLinecap="round"
                  fill="transparent"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-3xl font-bold ${getViabilityColor(data.viabilityScore)}`} data-testid="viability-score-value">
                  {data.viabilityScore}
                </span>
              </div>
            </div>
            
            <div className={`inline-block px-4 py-2 rounded-full text-sm font-medium text-white ${getViabilityBg(data.viabilityScore)}`} data-testid="viability-score-label">
              {getViabilityLabel(data.viabilityScore)}
            </div>
            
            <p className="text-gray-600 text-sm mt-2" data-testid="viability-score-description">
              Ready for detailed analysis
            </p>
          </div>

          {/* Key Insights */}
          <div className="bg-white rounded-lg border border-gray-200 p-6" data-testid="key-insights-card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4" data-testid="key-insights-title">Key Insights</h2>
            
            <div className="space-y-3" data-testid="insights-list">
              {data.insights.map((insight, index) => (
                <div key={index} className="flex items-start space-x-3" data-testid={`insight-${index}`}>
                  {getInsightIcon(insight.type)}
                  <span className="text-sm text-gray-700 flex-1" data-testid={`insight-text-${index}`}>
                    {insight.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Market Analysis */}
        <div className="bg-white rounded-lg border border-gray-200 p-6" data-testid="market-analysis-section">
          <h2 className="text-xl font-semibold text-gray-900 mb-4" data-testid="market-analysis-title">Market Analysis</h2>
          
          <div className="grid md:grid-cols-3 gap-6 mb-6" data-testid="market-metrics">
            <div data-testid="market-size-metric">
              <h3 className="font-medium text-gray-900 mb-2" data-testid="market-size-label">Market Size</h3>
              <p className="text-2xl font-bold text-blue-600" data-testid="market-size-value">{data.marketSize}</p>
              <p className="text-sm text-gray-600" data-testid="market-size-description">annually (US market)</p>
            </div>
            
            <div data-testid="growth-rate-metric">
              <h3 className="font-medium text-gray-900 mb-2" data-testid="growth-rate-label">Growth Rate</h3>
              <p className="text-2xl font-bold text-green-600" data-testid="growth-rate-value">{data.growthRate}</p>
              <p className="text-sm text-gray-600" data-testid="growth-rate-description">year-over-year growth</p>
            </div>
            
            <div data-testid="competition-level-metric">
              <h3 className="font-medium text-gray-900 mb-2" data-testid="competition-level-label">Competition Level</h3>
              <p className={`text-2xl font-bold capitalize ${
                data.competitionLevel === 'low' ? 'text-green-600' :
                data.competitionLevel === 'moderate' ? 'text-yellow-600' : 'text-red-600'
              }`} data-testid="competition-level-value">                {data.competitionLevel}
              </p>
              <p className="text-sm text-gray-600" data-testid="competitors-count">{data.competitors.length} main competitors</p>
            </div>
          </div>

          {/* Competitors Section */}
          <div className="border-t pt-6" data-testid="competitors-section">
            <button
              onClick={() => toggleSection('competitors')}
              className="flex items-center justify-between w-full text-left"
              data-testid="competitors-toggle"
            >
              <h3 className="font-medium text-gray-900" data-testid="competitors-title">Top Competitors</h3>
              <svg 
                className={`w-5 h-5 text-gray-500 transform transition-transform ${
                  expandedSection === 'competitors' ? 'rotate-180' : ''
                }`}
                fill="currentColor" 
                viewBox="0 0 20 20"
                data-testid="competitors-toggle-icon"
              >
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
            
            {expandedSection === 'competitors' && (
              <div className="mt-4 space-y-3" data-testid="competitors-list">
                {data.competitors.map((competitor, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg" data-testid={`competitor-${index}`}>
                    <div>
                      <h4 className="font-medium text-gray-900" data-testid={`competitor-name-${index}`}>{competitor.name}</h4>
                      <p className="text-sm text-gray-600" data-testid={`competitor-price-${index}`}>{competitor.priceRange}</p>
                    </div>
                    
                    <div className="text-right" data-testid={`competitor-rating-${index}`}>
                      <div className="flex items-center space-x-1" data-testid={`competitor-stars-${index}`}>
                        {Array.from({ length: 5 }).map((_, i) => (
                          <svg
                            key={i}
                            className={`w-4 h-4 ${
                              i < Math.floor(competitor.rating) ? 'text-yellow-400' : 'text-gray-300'
                            }`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                            data-testid={`star-${index}-${i}`}
                          >
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        ))}
                        <span className="text-sm text-gray-600" data-testid={`competitor-review-count-${index}`}>({competitor.reviewCount}+)</span>
                      </div>
                      <p className="text-xs text-gray-500 capitalize" data-testid={`competitor-position-${index}`}>{competitor.marketPosition}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pricing Recommendations */}
          <div className="border-t pt-6 mt-6" data-testid="pricing-section">
            <h3 className="font-medium text-gray-900 mb-3" data-testid="pricing-title">Recommended Pricing</h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4" data-testid="pricing-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-900 font-medium" data-testid="recommended-price-range">Suggested Range: {data.recommendedPriceRange}</p>
                  <p className="text-blue-700 text-sm" data-testid="pricing-rationale">Based on premium organic positioning</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleSection('pricing')}
                  className="text-blue-600"
                  data-testid="view-pricing-analysis-button"
                >
                  View Analysis →
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Next Steps */}
        <div className="bg-white rounded-lg border border-gray-200 p-6" data-testid="next-steps-section">
          <h2 className="text-xl font-semibold text-gray-900 mb-4" data-testid="next-steps-title">Next Steps (Priority Order)</h2>
          
          <div className="space-y-4" data-testid="next-steps-list">
            {data.nextSteps
              .sort((a, b) => a.order - b.order)
              .map((step, index) => (
              <div 
                key={step.id}
                className={`flex items-center justify-between p-4 rounded-lg border ${
                  step.isUnlocked 
                    ? 'border-blue-200 bg-blue-50' 
                    : 'border-gray-200 bg-gray-50'
                }`}
                data-testid={`next-step-${step.id}`}
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <span className={`flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium ${
                      step.isUnlocked 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-400 text-white'
                    }`} data-testid={`step-number-${step.id}`}>
                      {index + 1}
                    </span>
                    <h3 className={`font-medium ${
                      step.isUnlocked ? 'text-blue-900' : 'text-gray-500'
                    }`} data-testid={`step-title-${step.id}`}>
                      {step.title}
                    </h3>
                    {step.estimatedTime && (
                      <span className="text-xs text-gray-500" data-testid={`step-time-${step.id}`}>
                        ~{step.estimatedTime}
                      </span>
                    )}
                  </div>
                  <p className={`text-sm ${
                    step.isUnlocked ? 'text-blue-700' : 'text-gray-500'
                  }`} data-testid={`step-description-${step.id}`}>
                    {step.description}
                  </p>
                </div>
                
                <div className="ml-4" data-testid={`step-action-${step.id}`}>
                  {step.isUnlocked ? (
                    <Button
                      onClick={() => onStartNextStep(step.id)}
                      size="sm"
                      data-testid={`start-step-button-${step.id}`}
                    >
                      START NOW →
                    </Button>
                  ) : (
                    <Button
                      onClick={onUpgrade}
                      variant="secondary"
                      size="sm"
                      data-testid={`unlock-step-button-${step.id}`}
                    >
                      UNLOCK PAID
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upgrade CTA */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6" data-testid="upgrade-cta">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-900 mb-2" data-testid="upgrade-title">
              Unlock Full Potential
            </h2>
            
            <p className="text-gray-600 mb-4" data-testid="upgrade-description">
              Get complete milestone suite for $249 one-time payment:
            </p>
            
            <div className="grid md:grid-cols-2 gap-4 mb-6 text-sm" data-testid="upgrade-features">
              <div className="space-y-2" data-testid="upgrade-features-left">
                <div className="flex items-center text-green-600" data-testid="feature-suppliers">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Supplier database with contacts
                </div>
                <div className="flex items-center text-green-600" data-testid="feature-branding">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Brand positioning & marketing
                </div>
                <div className="flex items-center text-green-600" data-testid="feature-website">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Website briefs & tech specs
                </div>
              </div>
              
              <div className="space-y-2" data-testid="upgrade-features-right">
                <div className="flex items-center text-green-600" data-testid="feature-financials">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Professional financial models
                </div>
                <div className="flex items-center text-green-600" data-testid="feature-legal">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Legal & compliance templates
                </div>
                <div className="flex items-center text-green-600" data-testid="feature-checklist">
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Launch readiness checklist
                </div>
              </div>
            </div>
            
            <Button
              onClick={onUpgrade}
              size="lg"
              className="mb-2"
              data-testid="upgrade-button"
            >
              UPGRADE TO LAUNCHER PACKAGE
            </Button>
            
            <p className="text-sm text-gray-500" data-testid="guarantee-text">
              30-day money-back guarantee
            </p>
          </div>
        </div>
      </div>
    );
  }
);

FeasibilityReport.displayName = 'FeasibilityReport';