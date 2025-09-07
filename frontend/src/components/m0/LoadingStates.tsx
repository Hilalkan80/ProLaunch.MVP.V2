import { forwardRef, useEffect, useState } from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner = forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size = 'md', className = '' }, ref) => {
    const sizeClasses = {
      sm: 'h-4 w-4',
      md: 'h-6 w-6',
      lg: 'h-8 w-8'
    };

    return (
      <div
        ref={ref}
        className={`animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 ${sizeClasses[size]} ${className}`}
        role="status"
        aria-label="Loading"
        data-testid="loading-spinner"
      >
        <span className="sr-only">Loading...</span>
      </div>
    );
  }
);

LoadingSpinner.displayName = 'LoadingSpinner';

interface ProgressBarProps {
  progress: number; // 0-100
  showPercentage?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: 'blue' | 'green' | 'yellow' | 'red';
}

export const ProgressBar = forwardRef<HTMLDivElement, ProgressBarProps>(
  ({ 
    progress, 
    showPercentage = true, 
    className = '', 
    size = 'md',
    color = 'blue'
  }, ref) => {
    const [animatedProgress, setAnimatedProgress] = useState(0);

    useEffect(() => {
      const timer = setTimeout(() => {
        setAnimatedProgress(Math.min(100, Math.max(0, progress)));
      }, 100);
      return () => clearTimeout(timer);
    }, [progress]);

    const sizeClasses = {
      sm: 'h-2',
      md: 'h-3',
      lg: 'h-4'
    };

    const colorClasses = {
      blue: 'bg-blue-600',
      green: 'bg-green-600',
      yellow: 'bg-yellow-500',
      red: 'bg-red-600'
    };

    return (
      <div ref={ref} className={`w-full ${className}`} data-testid="progress-bar">
        {showPercentage && (
          <div className="flex justify-between items-center mb-1" data-testid="progress-bar-header">
            <span className="text-sm font-medium text-gray-700" data-testid="progress-label">Progress</span>
            <span className="text-sm text-gray-500" data-testid="progress-percentage">{Math.round(animatedProgress)}%</span>
          </div>
        )}
        <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`} data-testid="progress-bar-track">
          <div
            className={`${colorClasses[color]} ${sizeClasses[size]} rounded-full transition-all duration-500 ease-out`}
            style={{ width: `${animatedProgress}%` }}
            role="progressbar"
            aria-valuenow={animatedProgress}
            aria-valuemin={0}
            aria-valuemax={100}
            data-testid="progress-bar-fill"
          />
        </div>
      </div>
    );
  }
);

ProgressBar.displayName = 'ProgressBar';

interface LoadingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingDots = forwardRef<HTMLDivElement, LoadingDotsProps>(
  ({ className = '', size = 'md' }, ref) => {
    const sizeClasses = {
      sm: 'h-1 w-1',
      md: 'h-2 w-2',
      lg: 'h-3 w-3'
    };

    const dotClass = `${sizeClasses[size]} bg-blue-600 rounded-full animate-pulse`;

    return (
      <div ref={ref} className={`flex items-center space-x-1 ${className}`} data-testid="loading-dots">
        <div className={dotClass} style={{ animationDelay: '0ms' }} data-testid="loading-dot-1" />
        <div className={dotClass} style={{ animationDelay: '150ms' }} data-testid="loading-dot-2" />
        <div className={dotClass} style={{ animationDelay: '300ms' }} data-testid="loading-dot-3" />
      </div>
    );
  }
);

LoadingDots.displayName = 'LoadingDots';

interface SkeletonProps {
  className?: string;
  lines?: number;
  height?: string;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className = '', lines = 1, height = 'h-4' }, ref) => {
    return (
      <div ref={ref} className={`animate-pulse space-y-2 ${className}`} data-testid="skeleton-loader">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={`bg-gray-200 rounded ${height} ${
              index === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
            }`}
            data-testid={`skeleton-line-${index + 1}`}
          />
        ))}
      </div>
    );
  }
);

Skeleton.displayName = 'Skeleton';

interface TypingIndicatorProps {
  className?: string;
}

export const TypingIndicator = forwardRef<HTMLDivElement, TypingIndicatorProps>(
  ({ className = '' }, ref) => {
    return (
      <div ref={ref} className={`flex items-center space-x-1 ${className}`} data-testid="typing-indicator">
        <span className="text-sm text-gray-500" data-testid="typing-text">AI is typing</span>
        <LoadingDots size="sm" />
      </div>
    );
  }
);

TypingIndicator.displayName = 'TypingIndicator';

interface PulseLoaderProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  color?: 'blue' | 'green' | 'gray';
}

export const PulseLoader = forwardRef<HTMLDivElement, PulseLoaderProps>(
  ({ className = '', size = 'md', color = 'blue' }, ref) => {
    const sizeClasses = {
      sm: 'h-8 w-8',
      md: 'h-12 w-12',
      lg: 'h-16 w-16'
    };

    const colorClasses = {
      blue: 'bg-blue-600',
      green: 'bg-green-600',
      gray: 'bg-gray-400'
    };

    return (
      <div ref={ref} className={`relative ${sizeClasses[size]} ${className}`} data-testid="pulse-loader">
        <div className={`absolute inset-0 ${colorClasses[color]} rounded-full animate-ping opacity-75`} data-testid="pulse-loader-ring" />
        <div className={`relative ${sizeClasses[size]} ${colorClasses[color]} rounded-full`} data-testid="pulse-loader-core" />
      </div>
    );
  }
);

PulseLoader.displayName = 'PulseLoader';