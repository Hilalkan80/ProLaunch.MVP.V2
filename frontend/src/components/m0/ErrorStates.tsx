import { forwardRef, ReactNode } from 'react';
import { Button } from '../ui/Button';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
  className?: string;
}

export const ErrorBoundary = forwardRef<HTMLDivElement, ErrorBoundaryProps>(
  ({ children, fallback, onReset, className = '' }, ref) => {
    // This is a simple error boundary wrapper
    // In a real implementation, you'd use React Error Boundary
    return (
      <div ref={ref} className={className} data-testid="error-boundary">
        {fallback ? fallback : children}
      </div>
    );
  }
);

ErrorBoundary.displayName = 'ErrorBoundary';

interface ErrorMessageProps {
  title?: string;
  message: string;
  type?: 'error' | 'warning' | 'info';
  onRetry?: () => void;
  onDismiss?: () => void;
  retryLabel?: string;
  className?: string;
}

export const ErrorMessage = forwardRef<HTMLDivElement, ErrorMessageProps>(
  ({ 
    title = 'Something went wrong',
    message, 
    type = 'error',
    onRetry,
    onDismiss,
    retryLabel = 'Try Again',
    className = '' 
  }, ref) => {
    const getIcon = () => {
      switch (type) {
        case 'warning':
          return (
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
          );
        case 'info':
          return (
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
          );
        default:
          return (
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
          );
      }
    };

    const getBgColor = () => {
      switch (type) {
        case 'warning':
          return 'bg-yellow-50 border-yellow-200';
        case 'info':
          return 'bg-blue-50 border-blue-200';
        default:
          return 'bg-red-50 border-red-200';
      }
    };

    const getTextColor = () => {
      switch (type) {
        case 'warning':
          return 'text-yellow-800';
        case 'info':
          return 'text-blue-800';
        default:
          return 'text-red-800';
      }
    };

    return (
      <div ref={ref} className={`rounded-lg border p-6 ${getBgColor()} ${className}`} data-testid="error-message">
        <div className="flex items-start">
          <div className="flex-shrink-0" data-testid="error-icon">
            {getIcon()}
          </div>
          
          <div className="ml-4 flex-1">
            <h3 className={`text-lg font-medium ${getTextColor()}`} data-testid="error-title">
              {title}
            </h3>
            <p className={`mt-2 text-sm ${getTextColor().replace('800', '700')}`} data-testid="error-message-text">
              {message}
            </p>
            
            <div className="mt-4 flex items-center space-x-3" data-testid="error-actions">
              {onRetry && (
                <Button
                  onClick={onRetry}
                  variant={type === 'error' ? 'danger' : 'primary'}
                  size="sm"
                  data-testid="error-retry-button"
                >
                  {retryLabel}
                </Button>
              )}
              
              {onDismiss && (
                <Button
                  onClick={onDismiss}
                  variant="ghost"
                  size="sm"
                  className="text-gray-600"
                  data-testid="error-dismiss-button"
                >
                  Dismiss
                </Button>
              )}
            </div>
          </div>
          
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="ml-4 text-gray-400 hover:text-gray-600 transition-colors"
              data-testid="error-close-button"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  }
);

ErrorMessage.displayName = 'ErrorMessage';

interface NetworkErrorProps {
  onRetry: () => void;
  onGoOffline?: () => void;
  className?: string;
}

export const NetworkError = forwardRef<HTMLDivElement, NetworkErrorProps>(
  ({ onRetry, onGoOffline, className = '' }, ref) => {
    return (
      <ErrorMessage
        ref={ref}
        title="Connection Error"
        message="We're having trouble connecting to our servers. Please check your internet connection and try again."
        type="error"
        onRetry={onRetry}
        retryLabel="Retry Connection"
        className={className}
        data-testid="network-error"
      />
    );
  }
);

NetworkError.displayName = 'NetworkError';

interface ValidationErrorProps {
  errors: Record<string, string[]>;
  onDismiss?: () => void;
  className?: string;
}

export const ValidationError = forwardRef<HTMLDivElement, ValidationErrorProps>(
  ({ errors, onDismiss, className = '' }, ref) => {
    const errorList = Object.entries(errors).flatMap(([field, messages]) =>
      messages.map(message => `${field}: ${message}`)
    );

    if (errorList.length === 0) return null;

    return (
      <ErrorMessage
        ref={ref}
        title="Validation Error"
        message={errorList.join(', ')}
        type="warning"
        onDismiss={onDismiss}
        className={className}
        data-testid="validation-error"
      />
    );
  }
);

ValidationError.displayName = 'ValidationError';

interface ProcessingErrorProps {
  productIdea: string;
  onRetry: () => void;
  onStartOver: () => void;
  onContactSupport?: () => void;
  errorDetails?: string;
  className?: string;
}

export const ProcessingError = forwardRef<HTMLDivElement, ProcessingErrorProps>(
  ({ 
    productIdea, 
    onRetry, 
    onStartOver, 
    onContactSupport,
    errorDetails,
    className = '' 
  }, ref) => {
    return (
      <div ref={ref} className={`w-full max-w-2xl mx-auto ${className}`} data-testid="processing-error">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center" data-testid="processing-error-card">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4" data-testid="processing-error-icon">
            <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          
          <h2 className="text-2xl font-bold text-red-800 mb-2" data-testid="processing-error-title">
            Analysis Failed
          </h2>
          
          <p className="text-red-700 mb-4" data-testid="processing-error-message">
            We encountered an error while analyzing "{productIdea.length > 60 ? `${productIdea.substring(0, 60)}...` : productIdea}".
            Don't worry - your input has been saved.
          </p>
          
          {errorDetails && (
            <details className="mb-6 text-left" data-testid="error-details">
              <summary className="text-sm text-red-600 cursor-pointer hover:text-red-800" data-testid="error-details-toggle">
                Show technical details
              </summary>
              <div className="mt-2 p-3 bg-red-100 rounded text-xs text-red-700 font-mono" data-testid="error-details-content">
                {errorDetails}
              </div>
            </details>
          )}
          
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center" data-testid="processing-error-actions">
            <Button
              onClick={onRetry}
              variant="danger"
              className="w-full sm:w-auto"
              data-testid="retry-analysis-button"
            >
              Try Analysis Again
            </Button>
            
            <Button
              onClick={onStartOver}
              variant="ghost"
              className="w-full sm:w-auto text-red-600"
              data-testid="start-over-button"
            >
              Start with New Idea
            </Button>
            
            {onContactSupport && (
              <Button
                onClick={onContactSupport}
                variant="ghost"
                size="sm"
                className="w-full sm:w-auto text-gray-600"
                data-testid="contact-support-button"
              >
                Contact Support
              </Button>
            )}
          </div>
        </div>
        
        {/* Helpful suggestions */}
        <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-4" data-testid="error-suggestions">
          <h3 className="font-medium text-gray-900 mb-2" data-testid="suggestions-title">Common solutions:</h3>
          <ul className="text-sm text-gray-600 space-y-1" data-testid="suggestions-list">
            <li data-testid="suggestion-1">• Try rephrasing your product idea with more specific details</li>
            <li data-testid="suggestion-2">• Check your internet connection and try again</li>
            <li data-testid="suggestion-3">• Our AI works best with 10-200 word descriptions</li>
            <li data-testid="suggestion-4">• Avoid special characters or overly technical language</li>
          </ul>
        </div>
      </div>
    );
  }
);

ProcessingError.displayName = 'ProcessingError';

interface EmptyStateProps {
  title?: string;
  message: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ title, message, icon, action, className = '' }, ref) => {
    const defaultIcon = (
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>
    );

    return (
      <div ref={ref} className={`text-center p-8 ${className}`} data-testid="empty-state">
        <div className="mb-4" data-testid="empty-state-icon">
          {icon || defaultIcon}
        </div>
        
        {title && (
          <h3 className="text-lg font-medium text-gray-900 mb-2" data-testid="empty-state-title">
            {title}
          </h3>
        )}
        
        <p className="text-gray-600 mb-6 max-w-sm mx-auto" data-testid="empty-state-message">
          {message}
        </p>
        
        {action && (
          <Button onClick={action.onClick} data-testid="empty-state-action">
            {action.label}
          </Button>
        )}
      </div>
    );
  }
);

EmptyState.displayName = 'EmptyState';