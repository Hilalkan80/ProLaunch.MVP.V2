# ProLaunch.AI Implementation Guidelines

## Component Architecture

### Base Components
```tsx
// Button Component
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}

const Button: React.FC<ButtonProps> = ({
  variant,
  size,
  isLoading,
  disabled,
  children,
  onClick
}) => {
  return (
    <button
      className={`btn btn-${variant} btn-${size}`}
      disabled={disabled || isLoading}
      onClick={onClick}
    >
      {isLoading && <Spinner size="sm" />}
      {children}
    </button>
  );
};

// Input Component
interface InputProps {
  label: string;
  type?: 'text' | 'email' | 'password';
  error?: string;
  required?: boolean;
  value: string;
  onChange: (value: string) => void;
}

const Input: React.FC<InputProps> = ({
  label,
  type = 'text',
  error,
  required,
  value,
  onChange
}) => {
  const id = useId();
  
  return (
    <div className="form-field">
      <label htmlFor={id} className="label">
        {label}{required && ' *'}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`input ${error ? 'input-error' : ''}`}
        required={required}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <div id={`${id}-error`} className="error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
};
```

### Chat Components
```tsx
// Chat Message Component
interface MessageProps {
  content: string;
  type: 'user' | 'ai';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

const ChatMessage: React.FC<MessageProps> = ({
  content,
  type,
  timestamp,
  status
}) => {
  return (
    <div className={`message message-${type}`}>
      <div className="message-avatar">
        {type === 'ai' ? <AIIcon /> : <UserIcon />}
      </div>
      <div className="message-content">
        <div className="message-text">{content}</div>
        <div className="message-meta">
          <time dateTime={timestamp.toISOString()}>
            {formatTime(timestamp)}
          </time>
          {status && <MessageStatus status={status} />}
        </div>
      </div>
    </div>
  );
};

// Chat Input Component
interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSend(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
        disabled={disabled}
      />
      <Button
        type="submit"
        variant="primary"
        disabled={disabled || !message.trim()}
      >
        Send
      </Button>
    </form>
  );
};
```

### Milestone Components
```tsx
// Milestone Card Component
interface MilestoneProps {
  id: string;
  title: string;
  description: string;
  status: 'locked' | 'active' | 'completed';
  progress: number;
}

const MilestoneCard: React.FC<MilestoneProps> = ({
  id,
  title,
  description,
  status,
  progress
}) => {
  return (
    <div
      className={`milestone-card milestone-${status}`}
      aria-label={`Milestone ${title}: ${status}`}
    >
      <div className="milestone-header">
        <h3>{title}</h3>
        <Badge variant={status}>{status}</Badge>
      </div>
      <p>{description}</p>
      <ProgressBar
        value={progress}
        max={100}
        aria-label={`${progress}% complete`}
      />
    </div>
  );
};

// Progress Tracking Component
interface ProgressProps {
  currentMilestone: number;
  totalMilestones: number;
  completedMilestones: number[];
}

const ProgressTracker: React.FC<ProgressProps> = ({
  currentMilestone,
  totalMilestones,
  completedMilestones
}) => {
  return (
    <div className="progress-tracker" role="progressbar">
      {Array.from({ length: totalMilestones }).map((_, index) => (
        <div
          key={index}
          className={`progress-step ${
            completedMilestones.includes(index)
              ? 'completed'
              : index === currentMilestone
              ? 'active'
              : ''
          }`}
        />
      ))}
    </div>
  );
};
```

## Animation Patterns

### Transition Components
```tsx
// Fade Transition
const Fade: React.FC<{ in: boolean; children: React.ReactNode }> = ({
  in: inProp,
  children
}) => {
  return (
    <Transition
      in={inProp}
      timeout={200}
      unmountOnExit
    >
      {(state) => (
        <div
          style={{
            transition: 'opacity 200ms ease-out',
            opacity: state === 'entered' ? 1 : 0
          }}
        >
          {children}
        </div>
      )}
    </Transition>
  );
};

// Slide Transition
const Slide: React.FC<{
  in: boolean;
  direction: 'left' | 'right';
  children: React.ReactNode;
}> = ({ in: inProp, direction, children }) => {
  return (
    <Transition
      in={inProp}
      timeout={300}
      unmountOnExit
    >
      {(state) => (
        <div
          style={{
            transition: 'transform 300ms ease-out',
            transform: state === 'entered'
              ? 'translateX(0)'
              : `translateX(${direction === 'left' ? '-100%' : '100%'})`
          }}
        >
          {children}
        </div>
      )}
    </Transition>
  );
};
```

## Responsive Patterns

### Layout Components
```tsx
// Responsive Container
interface ContainerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
}

const Container: React.FC<ContainerProps> = ({
  size = 'lg',
  children
}) => {
  return (
    <div className={`container container-${size}`}>
      {children}
    </div>
  );
};

// Grid System
interface GridProps {
  columns: {
    base?: number;
    sm?: number;
    md?: number;
    lg?: number;
  };
  gap?: number;
  children: React.ReactNode;
}

const Grid: React.FC<GridProps> = ({
  columns,
  gap = 4,
  children
}) => {
  return (
    <div
      style={{
        display: 'grid',
        gap: `var(--space-${gap})`,
        gridTemplateColumns: {
          base: `repeat(${columns.base || 1}, 1fr)`,
          sm: columns.sm && `repeat(${columns.sm}, 1fr)`,
          md: columns.md && `repeat(${columns.md}, 1fr)`,
          lg: columns.lg && `repeat(${columns.lg}, 1fr)`
        }
      }}
    >
      {children}
    </div>
  );
};
```

## Performance Optimization

### Image Optimization
```tsx
// Optimized Image Component
interface ImageProps {
  src: string;
  alt: string;
  width: number;
  height: number;
  loading?: 'lazy' | 'eager';
}

const Image: React.FC<ImageProps> = ({
  src,
  alt,
  width,
  height,
  loading = 'lazy'
}) => {
  return (
    <img
      src={src}
      alt={alt}
      width={width}
      height={height}
      loading={loading}
      srcSet={`
        ${src}?w=${width} 1x,
        ${src}?w=${width * 2} 2x
      `}
      onLoad={() => {
        // Performance tracking
        if (window.performance) {
          const loadTime = performance.now();
          // Report to analytics
        }
      }}
    />
  );
};
```

### Code Splitting
```tsx
// Lazy Loading Routes
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Milestones = lazy(() => import('./pages/Milestones'));
const Settings = lazy(() => import('./pages/Settings'));

const Routes: React.FC = () => {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Switch>
        <Route path="/dashboard" component={Dashboard} />
        <Route path="/milestones" component={Milestones} />
        <Route path="/settings" component={Settings} />
      </Switch>
    </Suspense>
  );
};
```

## Error Handling

### Error Boundary
```tsx
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to monitoring service
    logError(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-screen">
          <h1>Something went wrong</h1>
          <Button
            onClick={() => window.location.reload()}
            variant="primary"
          >
            Refresh Page
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## Testing Patterns

### Component Testing
```tsx
// Button Component Test
import { render, fireEvent } from '@testing-library/react';

describe('Button', () => {
  test('renders correctly', () => {
    const { getByRole } = render(
      <Button variant="primary">Click Me</Button>
    );
    expect(getByRole('button')).toHaveTextContent('Click Me');
  });

  test('handles click events', () => {
    const onClick = jest.fn();
    const { getByRole } = render(
      <Button variant="primary" onClick={onClick}>
        Click Me
      </Button>
    );
    fireEvent.click(getByRole('button'));
    expect(onClick).toHaveBeenCalled();
  });

  test('shows loading state', () => {
    const { getByRole } = render(
      <Button variant="primary" isLoading>
        Click Me
      </Button>
    );
    expect(getByRole('button')).toBeDisabled();
    expect(getByRole('button')).toContainElement(
      document.querySelector('.spinner')
    );
  });
});
```

### Integration Testing
```tsx
// Chat Feature Test
describe('Chat Feature', () => {
  test('sends and receives messages', async () => {
    const { getByPlaceholderText, findByText } = render(<Chat />);
    
    // Send message
    const input = getByPlaceholderText('Type your message...');
    fireEvent.change(input, {
      target: { value: 'Hello AI' }
    });
    fireEvent.keyPress(input, {
      key: 'Enter',
      code: 13,
      charCode: 13
    });

    // Wait for response
    const response = await findByText(/Hi there!/i);
    expect(response).toBeInTheDocument();
  });
});
```

## Accessibility Testing
```tsx
// Accessibility Test
describe('Accessibility', () => {
  test('has no accessibility violations', async () => {
    const { container } = render(<App />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  test('supports keyboard navigation', () => {
    const { getAllByRole } = render(<Navigation />);
    const links = getAllByRole('link');
    
    // Tab through all links
    links.forEach(link => {
      link.focus();
      expect(document.activeElement).toBe(link);
    });
  });
});
```