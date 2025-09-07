# ProLaunch.AI Design System

## Color System

### Primary Colors
```css
:root {
  --primary-100: #EBF8FF;
  --primary-200: #BEE3F8;
  --primary-300: #90CDF4;
  --primary-400: #63B3ED;
  --primary-500: #4299E1;
  --primary-600: #3182CE;
  --primary-700: #2B6CB0;
  --primary-800: #2C5282;
  --primary-900: #2A4365;
}
```

### Semantic Colors
```css
:root {
  --success-500: #48BB78;
  --warning-500: #ECC94B;
  --error-500: #F56565;
  --info-500: #4299E1;
}
```

### Neutral Colors
```css
:root {
  --neutral-100: #F7FAFC;
  --neutral-200: #EDF2F7;
  --neutral-300: #E2E8F0;
  --neutral-400: #CBD5E0;
  --neutral-500: #A0AEC0;
  --neutral-600: #718096;
  --neutral-700: #4A5568;
  --neutral-800: #2D3748;
  --neutral-900: #1A202C;
}
```

### Dark Mode Colors
```css
[data-theme="dark"] {
  --primary-100: #2A4365;
  --primary-900: #EBF8FF;
  --neutral-100: #1A202C;
  --neutral-900: #F7FAFC;
}
```

## Typography

### Font Stack
```css
:root {
  --font-sans: 'Inter', -apple-system, system-ui, sans-serif;
  --font-display: 'Cal Sans', 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
```

### Font Sizes
```css
:root {
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.825rem + 0.25vw, 1rem);
  --text-base: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1.075rem + 0.25vw, 1.25rem);
  --text-xl: clamp(1.25rem, 1.2rem + 0.25vw, 1.5rem);
  --text-2xl: clamp(1.5rem, 1.45rem + 0.25vw, 1.875rem);
  --text-3xl: clamp(1.875rem, 1.825rem + 0.25vw, 2.25rem);
  --text-4xl: clamp(2.25rem, 2.2rem + 0.25vw, 3rem);
  --text-5xl: clamp(3rem, 2.95rem + 0.25vw, 4rem);
}
```

### Line Heights
```css
:root {
  --leading-none: 1;
  --leading-tight: 1.25;
  --leading-snug: 1.375;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  --leading-loose: 2;
}
```

## Spacing System

### Base Scale
```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  --space-24: 96px;
  --space-32: 128px;
  --space-40: 160px;
  --space-48: 192px;
  --space-56: 224px;
  --space-64: 256px;
}
```

## Component Library

### Buttons
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-weight: 500;
  transition: all 150ms ease;
}

.btn-primary {
  background: var(--primary-500);
  color: white;
}

.btn-secondary {
  background: var(--neutral-200);
  color: var(--neutral-900);
}

.btn-ghost {
  background: transparent;
  color: var(--primary-500);
}
```

### Chat Components
```css
.chat-message {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--neutral-100);
}

.chat-input {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-4);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-lg);
}
```

### Cards
```css
.card {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-6);
}

.card-interactive {
  transition: transform 150ms ease;
  cursor: pointer;
}

.card-interactive:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
```

### Form Elements
```css
.input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
}

.input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--primary-100);
}

.label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--neutral-700);
}
```

## Layout System

### Container Sizes
```css
:root {
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
}
```

### Grid System
```css
.grid {
  display: grid;
  gap: var(--space-4);
}

.grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-4 { grid-template-columns: repeat(4, 1fr); }

@media (min-width: 768px) {
  .md\\:grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
  .md\\:grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
  .md\\:grid-cols-4 { grid-template-columns: repeat(4, 1fr); }
}
```

## Animation System

### Timing Functions
```css
:root {
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Duration Scale
```css
:root {
  --duration-75: 75ms;
  --duration-100: 100ms;
  --duration-150: 150ms;
  --duration-200: 200ms;
  --duration-300: 300ms;
  --duration-500: 500ms;
  --duration-700: 700ms;
  --duration-1000: 1000ms;
}
```

### Common Animations
```css
.fade-in {
  animation: fadeIn var(--duration-200) var(--ease-out);
}

.slide-up {
  animation: slideUp var(--duration-300) var(--ease-out);
}

.scale {
  animation: scale var(--duration-150) var(--ease-in-out);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes scale {
  from { transform: scale(0.95); }
  to { transform: scale(1); }
}
```

## Icons

### Icon Grid
- Base size: 24x24px
- Stroke width: 2px
- Corner radius: 2px
- Padding: 1px

### Icon Categories
- Navigation
- Actions
- Status
- File types
- Social
- Arrows
- Misc

## Accessibility

### Color Contrast
- Regular text: 4.5:1 minimum
- Large text: 3:1 minimum
- Active elements: 3:1 minimum

### Focus States
```css
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--primary-100);
  border-radius: var(--radius-sm);
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

## Responsive Design

### Breakpoints
```css
:root {
  --screen-sm: 640px;
  --screen-md: 768px;
  --screen-lg: 1024px;
  --screen-xl: 1280px;
  --screen-2xl: 1536px;
}

@media (min-width: 640px) { .sm\\:class {} }
@media (min-width: 768px) { .md\\:class {} }
@media (min-width: 1024px) { .lg\\:class {} }
@media (min-width: 1280px) { .xl\\:class {} }
@media (min-width: 1536px) { .\\2xl\\:class {} }
```

### Touch Targets
```css
@media (hover: none) and (pointer: coarse) {
  .interactive {
    min-height: 44px;
    min-width: 44px;
  }
}
```