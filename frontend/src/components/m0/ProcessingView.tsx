import { forwardRef, useEffect, useState } from 'react';
import { ProgressBar, LoadingSpinner, PulseLoader } from './LoadingStates';

interface ProcessingStep {
  id: string;
  label: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  duration?: number; // estimated duration in seconds
}

interface ProcessingViewProps {
  productIdea: string;
  steps: ProcessingStep[];
  currentStepIndex: number;
  overallProgress: number;
  onCancel?: () => void;
  className?: string;
}

export const ProcessingView = forwardRef<HTMLDivElement, ProcessingViewProps>(
  ({ 
    productIdea, 
    steps, 
    currentStepIndex, 
    overallProgress, 
    onCancel, 
    className = '' 
  }, ref) => {
    const [timeElapsed, setTimeElapsed] = useState(0);
    const currentStep = steps[currentStepIndex] || steps[steps.length - 1];

    useEffect(() => {
      const timer = setInterval(() => {
        setTimeElapsed(prev => prev + 1);
      }, 1000);

      return () => clearInterval(timer);
    }, []);

    const formatTime = (seconds: number) => {
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getStepIcon = (step: ProcessingStep) => {
      switch (step.status) {
        case 'completed':
          return (
            <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          );
        case 'processing':
          return <LoadingSpinner size="sm" className="text-blue-600" />;
        case 'error':
          return (
            <div className="w-6 h-6 bg-red-600 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
          );
        default:
          return (
            <div className="w-6 h-6 bg-gray-300 rounded-full flex items-center justify-center">
              <span className="text-xs text-gray-600 font-medium">
                {steps.indexOf(step) + 1}
              </span>
            </div>
          );
      }
    };

    return (
      <div ref={ref} className={`w-full max-w-2xl mx-auto p-6 ${className}`} data-testid="processing-view">
        {/* Header */}
        <div className="text-center mb-8" data-testid="processing-header">
          <div className="mb-4" data-testid="processing-loader">
            <PulseLoader size="lg" color="blue" className="mx-auto" />
          </div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2" data-testid="processing-title">
            Analyzing Your Product Idea
          </h2>
          
          <p className="text-gray-600 mb-4" data-testid="product-idea-display">
            "{productIdea.length > 60 ? `${productIdea.substring(0, 60)}...` : productIdea}"
          </p>
          
          <div className="text-sm text-gray-500" data-testid="time-elapsed">
            Time elapsed: {formatTime(timeElapsed)}
          </div>
        </div>

        {/* Overall Progress */}
        <div className="mb-8" data-testid="overall-progress">
          <ProgressBar
            progress={overallProgress}
            showPercentage={true}
            className="mb-4"
          />
          
          <div className="flex justify-between items-center text-sm text-gray-600" data-testid="progress-info">
            <span data-testid="progress-label">Overall Progress</span>
            <span data-testid="step-counter">
              Step {Math.min(currentStepIndex + 1, steps.length)} of {steps.length}
            </span>
          </div>
        </div>

        {/* Current Step Highlight */}
        {currentStep && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6" data-testid="current-step-highlight">
            <div className="flex items-start space-x-3">
              {getStepIcon(currentStep)}
              <div className="flex-1">
                <h3 className="font-medium text-blue-900 mb-1" data-testid="current-step-label">
                  {currentStep.label}
                </h3>
                <p className="text-blue-700 text-sm" data-testid="current-step-description">
                  {currentStep.description}
                </p>
                {currentStep.status === 'processing' && currentStep.duration && (
                  <p className="text-blue-600 text-xs mt-2" data-testid="current-step-duration">
                    Estimated time: ~{currentStep.duration} seconds
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Steps List */}
        <div className="space-y-4 mb-8" data-testid="steps-list">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-start space-x-3 p-3 rounded-lg transition-all duration-200 ${
                index === currentStepIndex
                  ? 'bg-blue-50 border border-blue-200'
                  : index < currentStepIndex
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-gray-50 border border-gray-200'
              }`}
              data-testid={`processing-step-${step.id}`}
            >
              {getStepIcon(step)}
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className={`font-medium text-sm ${
                    step.status === 'completed'
                      ? 'text-green-800'
                      : step.status === 'processing'
                      ? 'text-blue-800'
                      : step.status === 'error'
                      ? 'text-red-800'
                      : 'text-gray-600'
                  }`} data-testid={`step-label-${step.id}`}>
                    {step.label}
                  </h4>
                  
                  {step.status === 'processing' && (
                    <span className="text-xs text-blue-600 font-medium" data-testid={`step-status-${step.id}`}>
                      In Progress
                    </span>
                  )}
                  
                  {step.status === 'completed' && (
                    <span className="text-xs text-green-600 font-medium" data-testid={`step-status-${step.id}`}>
                      Complete
                    </span>
                  )}
                </div>
                
                <p className={`text-xs mt-1 ${
                  step.status === 'completed'
                    ? 'text-green-700'
                    : step.status === 'processing'
                    ? 'text-blue-700'
                    : step.status === 'error'
                    ? 'text-red-700'
                    : 'text-gray-500'
                }`} data-testid={`step-description-${step.id}`}>
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4" data-testid="processing-actions">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
              data-testid="cancel-analysis-button"
            >
              Cancel Analysis
            </button>
          )}
          
          <div className="text-xs text-gray-500 flex items-center space-x-2" data-testid="processing-info">
            <span data-testid="processing-duration-info">This usually takes 60-90 seconds</span>
            <div className="flex space-x-1" data-testid="processing-dots">
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" data-testid="processing-dot-1" />
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} data-testid="processing-dot-2" />
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} data-testid="processing-dot-3" />
            </div>
          </div>
        </div>
      </div>
    );
  }
);

ProcessingView.displayName = 'ProcessingView';