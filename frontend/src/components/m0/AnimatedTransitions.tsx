import { forwardRef, ReactNode, useEffect, useState } from 'react';

interface FadeInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export const FadeIn = forwardRef<HTMLDivElement, FadeInProps>(
  ({ children, delay = 0, duration = 300, className = '' }, ref) => {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, delay);

      return () => clearTimeout(timer);
    }, [delay]);

    return (
      <div
        ref={ref}
        className={`transition-all ease-out ${className}`}
        style={{
          opacity: isVisible ? 1 : 0,
          transform: isVisible ? 'translateY(0)' : 'translateY(10px)',
          transitionDuration: `${duration}ms`,
        }}
        data-testid="fade-in"
      >
        {children}
      </div>
    );
  }
);

FadeIn.displayName = 'FadeIn';

interface SlideInProps {
  children: ReactNode;
  direction?: 'left' | 'right' | 'up' | 'down';
  delay?: number;
  duration?: number;
  distance?: number;
  className?: string;
}

export const SlideIn = forwardRef<HTMLDivElement, SlideInProps>(
  ({ 
    children, 
    direction = 'up', 
    delay = 0, 
    duration = 400, 
    distance = 20,
    className = '' 
  }, ref) => {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, delay);

      return () => clearTimeout(timer);
    }, [delay]);

    const getTransform = () => {
      if (isVisible) return 'translate3d(0, 0, 0)';
      
      switch (direction) {
        case 'left':
          return `translate3d(-${distance}px, 0, 0)`;
        case 'right':
          return `translate3d(${distance}px, 0, 0)`;
        case 'down':
          return `translate3d(0, ${distance}px, 0)`;
        default: // up
          return `translate3d(0, ${distance}px, 0)`;
      }
    };

    return (
      <div
        ref={ref}
        className={`transition-all ease-out ${className}`}
        style={{
          opacity: isVisible ? 1 : 0,
          transform: getTransform(),
          transitionDuration: `${duration}ms`,
        }}
        data-testid="slide-in"
      >
        {children}
      </div>
    );
  }
);

SlideIn.displayName = 'SlideIn';

interface ScaleInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  initialScale?: number;
  className?: string;
}

export const ScaleIn = forwardRef<HTMLDivElement, ScaleInProps>(
  ({ children, delay = 0, duration = 300, initialScale = 0.95, className = '' }, ref) => {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, delay);

      return () => clearTimeout(timer);
    }, [delay]);

    return (
      <div
        ref={ref}
        className={`transition-all ease-out ${className}`}
        style={{
          opacity: isVisible ? 1 : 0,
          transform: isVisible ? 'scale(1)' : `scale(${initialScale})`,
          transitionDuration: `${duration}ms`,
        }}
        data-testid="scale-in"
      >
        {children}
      </div>
    );
  }
);

ScaleIn.displayName = 'ScaleIn';

interface StaggeredListProps {
  children: ReactNode[];
  staggerDelay?: number;
  itemDelay?: number;
  className?: string;
}

export const StaggeredList = forwardRef<HTMLDivElement, StaggeredListProps>(
  ({ children, staggerDelay = 100, itemDelay = 0, className = '' }, ref) => {
    return (
      <div ref={ref} className={className} data-testid="staggered-list">
        {children.map((child, index) => (
          <FadeIn 
            key={index} 
            delay={itemDelay + (index * staggerDelay)}
          >
            {child}
          </FadeIn>
        ))}
      </div>
    );
  }
);

StaggeredList.displayName = 'StaggeredList';

interface TypewriterProps {
  text: string;
  speed?: number;
  delay?: number;
  className?: string;
  onComplete?: () => void;
}

export const Typewriter = forwardRef<HTMLSpanElement, TypewriterProps>(
  ({ text, speed = 50, delay = 0, className = '', onComplete }, ref) => {
    const [displayText, setDisplayText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);
    const [started, setStarted] = useState(false);

    useEffect(() => {
      const startTimer = setTimeout(() => {
        setStarted(true);
      }, delay);

      return () => clearTimeout(startTimer);
    }, [delay]);

    useEffect(() => {
      if (!started || currentIndex >= text.length) {
        if (currentIndex >= text.length && onComplete) {
          onComplete();
        }
        return;
      }

      const timer = setTimeout(() => {
        setDisplayText(text.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, speed);

      return () => clearTimeout(timer);
    }, [started, currentIndex, text, speed, onComplete]);

    return (
      <span ref={ref} className={className} data-testid="typewriter">
        {displayText}
        <span className="animate-pulse" data-testid="typewriter-cursor">|</span>
      </span>
    );
  }
);

Typewriter.displayName = 'Typewriter';

interface ProgressiveRevealProps {
  children: ReactNode;
  isRevealed: boolean;
  height?: string;
  duration?: number;
  className?: string;
}

export const ProgressiveReveal = forwardRef<HTMLDivElement, ProgressiveRevealProps>(
  ({ children, isRevealed, height = 'auto', duration = 400, className = '' }, ref) => {
    return (
      <div
        ref={ref}
        className={`overflow-hidden transition-all ease-out ${className}`}
        style={{
          height: isRevealed ? height : '0px',
          transitionDuration: `${duration}ms`,
        }}
        data-testid="progressive-reveal"
      >
        <div className={`transition-opacity ease-out delay-100 ${isRevealed ? 'opacity-100' : 'opacity-0'}`} data-testid="progressive-reveal-content">
          {children}
        </div>
      </div>
    );
  }
);

ProgressiveReveal.displayName = 'ProgressiveReveal';

interface CountUpProps {
  from?: number;
  to: number;
  duration?: number;
  delay?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

export const CountUp = forwardRef<HTMLSpanElement, CountUpProps>(
  ({ from = 0, to, duration = 2000, delay = 0, suffix = '', prefix = '', className = '' }, ref) => {
    const [count, setCount] = useState(from);
    const [started, setStarted] = useState(false);

    useEffect(() => {
      const startTimer = setTimeout(() => {
        setStarted(true);
      }, delay);

      return () => clearTimeout(startTimer);
    }, [delay]);

    useEffect(() => {
      if (!started) return;

      const totalSteps = Math.abs(to - from);
      const stepDuration = duration / totalSteps;
      const increment = to > from ? 1 : -1;

      let currentCount = from;
      const timer = setInterval(() => {
        currentCount += increment;
        setCount(currentCount);

        if (currentCount === to) {
          clearInterval(timer);
        }
      }, stepDuration);

      return () => clearInterval(timer);
    }, [started, from, to, duration]);

    return (
      <span ref={ref} className={className} data-testid="count-up">
        {prefix}{count}{suffix}
      </span>
    );
  }
);

CountUp.displayName = 'CountUp';

interface PulseProps {
  children: ReactNode;
  intensity?: 'light' | 'medium' | 'strong';
  duration?: number;
  className?: string;
}

export const Pulse = forwardRef<HTMLDivElement, PulseProps>(
  ({ children, intensity = 'medium', duration = 2000, className = '' }, ref) => {
    const getIntensityClass = () => {
      switch (intensity) {
        case 'light':
          return 'animate-pulse opacity-75';
        case 'strong':
          return 'animate-pulse opacity-30';
        default:
          return 'animate-pulse opacity-50';
      }
    };

    return (
      <div
        ref={ref}
        className={`${getIntensityClass()} ${className}`}
        style={{
          animationDuration: `${duration}ms`,
        }}
        data-testid="pulse"
      >
        {children}
      </div>
    );
  }
);

Pulse.displayName = 'Pulse';

interface ShimmerProps {
  width?: string;
  height?: string;
  className?: string;
}

export const Shimmer = forwardRef<HTMLDivElement, ShimmerProps>(
  ({ width = '100%', height = '20px', className = '' }, ref) => {
    return (
      <div
        ref={ref}
        className={`bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 animate-pulse ${className}`}
        style={{
          width,
          height,
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s ease-in-out infinite',
        }}
        data-testid="shimmer"
      >
        <style jsx>{`
          @keyframes shimmer {
            0% {
              background-position: -200% 0;
            }
            100% {
              background-position: 200% 0;
            }
          }
        `}</style>
      </div>
    );
  }
);

Shimmer.displayName = 'Shimmer';