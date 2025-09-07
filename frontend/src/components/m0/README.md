# M0 UI Components

This directory contains all the UI components for the M0 (Milestone 0) feature of ProLaunch.AI - the initial product feasibility analysis.

## Overview

The M0 components provide a complete user journey for product idea validation:

1. **Input Form** - Collect and validate user's product idea
2. **Processing View** - Show analysis progress with real-time updates
3. **Results Display** - Present comprehensive feasibility report
4. **Error Handling** - Graceful error states and recovery
5. **Share Functionality** - Share and export capabilities
6. **Animations** - Smooth transitions between states

## Component Architecture

### Main Container
- `M0Container` - Main orchestrator component that manages the entire M0 flow

### Form Components
- `ProductIdeaForm` - Input form with validation and suggestions

### Loading & Processing
- `LoadingStates` - Various loading indicators (spinner, progress bar, dots, etc.)
- `ProcessingView` - Real-time processing progress with step-by-step updates

### Results & Success
- `FeasibilityReport` - Comprehensive results display with insights and next steps

### Error Handling
- `ErrorStates` - Complete error handling UI (network errors, validation errors, processing errors)

### Sharing & Export
- `ShareComponents` - Social sharing and data export functionality

### Animations
- `AnimatedTransitions` - Reusable animation components for smooth UX

## Key Features

### 🎯 Product Idea Validation
- Character count and validation
- Quick suggestion chips
- Real-time form validation with Zod schema
- Keyboard shortcuts (Enter to submit, Shift+Enter for new line)

### ⚡ Real-time Processing
- Step-by-step progress tracking
- Estimated time remaining
- Cancellation capability
- Visual progress indicators

### 📊 Comprehensive Reporting
- Viability scoring with visual indicators
- Market analysis with competitor data
- Pricing recommendations
- Next steps prioritization
- Upgrade prompts for advanced features

### 🔄 Error Recovery
- Network error handling with auto-retry
- Validation errors with clear messaging
- Processing error recovery options
- Graceful degradation

### 📱 Responsive Design
- Mobile-first approach
- Breakpoint-based layouts
- Touch-optimized interactions
- Progressive enhancement

### 🎨 Smooth Animations
- Fade in/out transitions
- Slide animations
- Scale effects
- Staggered list animations
- Typewriter effects
- Count-up animations

## Usage Examples

### Basic Implementation
```tsx
import { M0Container } from '../components/m0';

function MyPage() {
  return (
    <M0Container
      onUpgrade={() => console.log('Upgrade requested')}
      onStartNextStep={(stepId) => console.log('Next step:', stepId)}
      onAnalysisComplete={(data) => console.log('Analysis done:', data)}
    />
  );
}
```

### Individual Components
```tsx
import { 
  ProductIdeaForm, 
  ProcessingView, 
  FeasibilityReport,
  LoadingSpinner 
} from '../components/m0';

// Form only
<ProductIdeaForm 
  onSubmit={(data) => console.log(data.productIdea)}
  isLoading={false}
/>

// Loading indicator
<LoadingSpinner size="lg" />

// Processing view
<ProcessingView
  productIdea="Organic dog treats"
  steps={processingSteps}
  currentStepIndex={2}
  overallProgress={45}
  onCancel={() => console.log('Cancelled')}
/>
```

### With Animations
```tsx
import { FadeIn, SlideIn, StaggeredList } from '../components/m0';

<FadeIn delay={300}>
  <h1>Welcome to M0</h1>
</FadeIn>

<SlideIn direction="up" duration={500}>
  <ProductIdeaForm onSubmit={handleSubmit} />
</SlideIn>

<StaggeredList staggerDelay={100}>
  {items.map(item => <div key={item.id}>{item.content}</div>)}
</StaggeredList>
```

## State Management

The M0Container manages these states:
- `input` - Initial form state
- `processing` - Analysis in progress
- `success` - Results display
- `error` - Processing error
- `network-error` - Connection issues

## Styling

Components use Tailwind CSS with:
- Design system colors (blue primary, green success, red error)
- Consistent spacing and typography
- Responsive breakpoints
- Accessibility-compliant contrast ratios

## Accessibility

All components follow WCAG AA guidelines:
- Semantic HTML structure
- ARIA labels and roles
- Keyboard navigation support
- Screen reader compatibility
- Color contrast compliance
- Focus management

## Performance

- Lazy loading for heavy components
- Optimistic UI updates
- Efficient re-renders with React.memo where appropriate
- Progressive disclosure patterns
- Image optimization for icons and graphics

## Testing

Components are designed for testing with:
- Semantic queries (getByRole, getByLabelText)
- Data test IDs where needed
- Mock API responses
- Error boundary testing
- Accessibility testing

## Browser Support

- Modern browsers (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Mobile browsers (iOS Safari, Chrome Mobile, Samsung Internet)
- Progressive enhancement for older browsers
- Graceful degradation when JavaScript is disabled

## File Structure

```
m0/
├── M0Container.tsx           # Main orchestrator
├── ProductIdeaForm.tsx       # Input form
├── LoadingStates.tsx         # Loading components
├── ProcessingView.tsx        # Processing display
├── FeasibilityReport.tsx     # Results display
├── ErrorStates.tsx           # Error handling
├── ShareComponents.tsx       # Share functionality
├── AnimatedTransitions.tsx   # Animation components
├── index.ts                  # Export file
└── README.md                 # This file
```

## Contributing

When adding new M0 components:

1. Follow the existing component patterns
2. Include TypeScript interfaces
3. Add proper error handling
4. Implement responsive design
5. Include accessibility features
6. Add animation support where appropriate
7. Update the index.ts export file
8. Document component props and usage