# ProLaunch.AI Complete Design System

## Overview
This comprehensive design system provides all visual and interaction specifications for ProLaunch.AI, including light and dark mode variants, component library, and implementation guidelines.

---

## 1. Color System

### Light Mode Palette
```css
:root {
  /* Primary Brand Colors */
  --color-primary-50: #EFF6FF;
  --color-primary-100: #DBEAFE;
  --color-primary-200: #BFDBFE;
  --color-primary-300: #93C5FD;
  --color-primary-400: #60A5FA;
  --color-primary-500: #1A8CFF; /* Primary Brand */
  --color-primary-600: #0073E6;
  --color-primary-700: #0059B3;
  --color-primary-800: #004080;
  --color-primary-900: #00264D;
  
  /* Semantic Colors - Light Mode */
  --color-success-50: #F0FDF4;
  --color-success-100: #DCFCE7;
  --color-success-500: #22C55E;
  --color-success-600: #16A34A;
  --color-success-900: #14532D;
  
  --color-warning-50: #FFFBEB;
  --color-warning-100: #FEF3C7;
  --color-warning-500: #F59E0B;
  --color-warning-600: #D97706;
  --color-warning-900: #78350F;
  
  --color-error-50: #FEF2F2;
  --color-error-100: #FEE2E2;
  --color-error-500: #EF4444;
  --color-error-600: #DC2626;
  --color-error-900: #7F1D1D;
  
  /* Neutral Colors - Light Mode */
  --color-neutral-0: #FFFFFF;
  --color-neutral-50: #FAFAFA;
  --color-neutral-100: #F5F5F5;
  --color-neutral-200: #E5E5E5;
  --color-neutral-300: #D4D4D4;
  --color-neutral-400: #A3A3A3;
  --color-neutral-500: #737373;
  --color-neutral-600: #525252;
  --color-neutral-700: #404040;
  --color-neutral-800: #262626;
  --color-neutral-900: #171717;
  
  /* Surface Colors - Light Mode */
  --color-surface-primary: var(--color-neutral-0);
  --color-surface-secondary: var(--color-neutral-50);
  --color-surface-tertiary: var(--color-neutral-100);
  --color-surface-elevated: var(--color-neutral-0);
  
  /* Text Colors - Light Mode */
  --color-text-primary: var(--color-neutral-900);
  --color-text-secondary: var(--color-neutral-700);
  --color-text-tertiary: var(--color-neutral-500);
  --color-text-inverse: var(--color-neutral-0);
  
  /* Border Colors - Light Mode */
  --color-border-primary: var(--color-neutral-200);
  --color-border-secondary: var(--color-neutral-100);
  --color-border-focus: var(--color-primary-500);
}
```

### Dark Mode Palette
```css
[data-theme="dark"] {
  /* Primary Brand Colors (Same as light mode) */
  --color-primary-50: #1E293B;
  --color-primary-100: #334155;
  --color-primary-200: #475569;
  --color-primary-300: #64748B;
  --color-primary-400: #60A5FA;
  --color-primary-500: #1A8CFF; /* Primary Brand */
  --color-primary-600: #3B82F6;
  --color-primary-700: #60A5FA;
  --color-primary-800: #93C5FD;
  --color-primary-900: #DBEAFE;
  
  /* Semantic Colors - Dark Mode */
  --color-success-50: #0F1A0F;
  --color-success-100: #1A2E1A;
  --color-success-500: #22C55E;
  --color-success-600: #4ADE80;
  --color-success-900: #BBF7D0;
  
  --color-warning-50: #1C1917;
  --color-warning-100: #2D2A23;
  --color-warning-500: #F59E0B;
  --color-warning-600: #FBBF24;
  --color-warning-900: #FDE68A;
  
  --color-error-50: #1F1415;
  --color-error-100: #2D1B1E;
  --color-error-500: #EF4444;
  --color-error-600: #F87171;
  --color-error-900: #FCA5A5;
  
  /* Neutral Colors - Dark Mode */
  --color-neutral-0: #000000;
  --color-neutral-50: #0A0A0A;
  --color-neutral-100: #171717;
  --color-neutral-200: #262626;
  --color-neutral-300: #404040;
  --color-neutral-400: #525252;
  --color-neutral-500: #737373;
  --color-neutral-600: #A3A3A3;
  --color-neutral-700: #D4D4D4;
  --color-neutral-800: #E5E5E5;
  --color-neutral-900: #F5F5F5;
  
  /* Surface Colors - Dark Mode */
  --color-surface-primary: #0F172A;
  --color-surface-secondary: #1E293B;
  --color-surface-tertiary: #334155;
  --color-surface-elevated: #1E293B;
  
  /* Text Colors - Dark Mode */
  --color-text-primary: var(--color-neutral-900);
  --color-text-secondary: var(--color-neutral-700);
  --color-text-tertiary: var(--color-neutral-500);
  --color-text-inverse: var(--color-neutral-100);
  
  /* Border Colors - Dark Mode */
  --color-border-primary: var(--color-neutral-300);
  --color-border-secondary: var(--color-neutral-200);
  --color-border-focus: var(--color-primary-400);
}
```

### Accessibility-Compliant Contrast Ratios
```css
/* WCAG AA Compliant Color Combinations */
.text-on-primary { 
  color: var(--color-text-inverse); 
  /* Contrast: 4.5:1 minimum */
}

.text-on-surface { 
  color: var(--color-text-primary); 
  /* Contrast: 7:1 preferred */
}

.text-secondary { 
  color: var(--color-text-secondary); 
  /* Contrast: 4.5:1 minimum */
}

.text-disabled { 
  color: var(--color-text-tertiary); 
  /* Contrast: 3:1 minimum for large text */
}
```

---

## 2. Typography System

### Font Stack
```css
:root {
  /* Primary Font (UI Text) */
  --font-family-primary: "Inter", -apple-system, BlinkMacSystemFont, 
                         "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", 
                         "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif;
  
  /* Secondary Font (Display/Headings) */
  --font-family-secondary: "Cal Sans", -apple-system, BlinkMacSystemFont, 
                          "Segoe UI", sans-serif;
  
  /* Monospace Font (Code/Data) */
  --font-family-mono: "SF Mono", SFMono-Regular, "Monaco", "Inconsolata", 
                      "Fira Code", "Droid Sans Mono", "Courier New", monospace;
}
```

### Type Scale & Hierarchy
```css
:root {
  /* Font Sizes (Fluid Responsive) */
  --font-size-xs: clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);    /* 12-14px */
  --font-size-sm: clamp(0.875rem, 0.8rem + 0.3vw, 1rem);       /* 14-16px */
  --font-size-base: clamp(1rem, 0.9rem + 0.4vw, 1.125rem);     /* 16-18px */
  --font-size-lg: clamp(1.125rem, 1rem + 0.5vw, 1.25rem);      /* 18-20px */
  --font-size-xl: clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem);      /* 20-24px */
  --font-size-2xl: clamp(1.5rem, 1.3rem + 0.8vw, 1.875rem);    /* 24-30px */
  --font-size-3xl: clamp(1.875rem, 1.6rem + 1vw, 2.25rem);     /* 30-36px */
  --font-size-4xl: clamp(2.25rem, 2rem + 1.2vw, 3rem);         /* 36-48px */
  --font-size-5xl: clamp(3rem, 2.5rem + 2vw, 3.75rem);         /* 48-60px */
  
  /* Font Weights */
  --font-weight-light: 300;
  --font-weight-regular: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  
  /* Line Heights */
  --line-height-tight: 1.25;
  --line-height-snug: 1.375;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.625;
  --line-height-loose: 2;
  
  /* Letter Spacing */
  --letter-spacing-tighter: -0.05em;
  --letter-spacing-tight: -0.025em;
  --letter-spacing-normal: 0em;
  --letter-spacing-wide: 0.025em;
  --letter-spacing-wider: 0.05em;
}
```

### Typography Classes
```css
/* Heading Styles */
.heading-1 {
  font-family: var(--font-family-secondary);
  font-size: var(--font-size-5xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  letter-spacing: var(--letter-spacing-tighter);
  color: var(--color-text-primary);
}

.heading-2 {
  font-family: var(--font-family-secondary);
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  letter-spacing: var(--letter-spacing-tight);
  color: var(--color-text-primary);
}

.heading-3 {
  font-family: var(--font-family-secondary);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  color: var(--color-text-primary);
}

.heading-4 {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-snug);
  color: var(--color-text-primary);
}

/* Body Text Styles */
.body-large {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-primary);
}

.body-base {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
}

.body-small {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-normal);
  color: var(--color-text-secondary);
}

/* Special Text Styles */
.caption {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: var(--line-height-tight);
  color: var(--color-text-tertiary);
  letter-spacing: var(--letter-spacing-wide);
}

.overline {
  font-family: var(--font-family-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-tight);
  color: var(--color-text-tertiary);
  letter-spacing: var(--letter-spacing-wider);
  text-transform: uppercase;
}

.code {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-regular);
  line-height: var(--line-height-snug);
  color: var(--color-primary-600);
  background: var(--color-surface-secondary);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
}
```

---

## 3. Spacing & Layout System

### Spacing Scale
```css
:root {
  /* Base spacing unit: 4px */
  --space-0: 0;
  --space-px: 1px;
  --space-0-5: 0.125rem;  /* 2px */
  --space-1: 0.25rem;     /* 4px */
  --space-1-5: 0.375rem;  /* 6px */
  --space-2: 0.5rem;      /* 8px */
  --space-2-5: 0.625rem;  /* 10px */
  --space-3: 0.75rem;     /* 12px */
  --space-3-5: 0.875rem;  /* 14px */
  --space-4: 1rem;        /* 16px */
  --space-5: 1.25rem;     /* 20px */
  --space-6: 1.5rem;      /* 24px */
  --space-7: 1.75rem;     /* 28px */
  --space-8: 2rem;        /* 32px */
  --space-9: 2.25rem;     /* 36px */
  --space-10: 2.5rem;     /* 40px */
  --space-12: 3rem;       /* 48px */
  --space-14: 3.5rem;     /* 56px */
  --space-16: 4rem;       /* 64px */
  --space-20: 5rem;       /* 80px */
  --space-24: 6rem;       /* 96px */
  --space-32: 8rem;       /* 128px */
  --space-40: 10rem;      /* 160px */
  --space-48: 12rem;      /* 192px */
  --space-56: 14rem;      /* 224px */
  --space-64: 16rem;      /* 256px */
}
```

### Container & Grid System
```css
/* Container Sizes */
.container {
  width: 100%;
  margin: 0 auto;
  padding-left: var(--space-4);
  padding-right: var(--space-4);
}

.container-sm { max-width: 640px; }
.container-md { max-width: 768px; }
.container-lg { max-width: 1024px; }
.container-xl { max-width: 1280px; }
.container-2xl { max-width: 1536px; }

/* Grid System */
.grid {
  display: grid;
  gap: var(--space-6);
}

.grid-cols-1 { grid-template-columns: repeat(1, 1fr); }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-4 { grid-template-columns: repeat(4, 1fr); }
.grid-cols-12 { grid-template-columns: repeat(12, 1fr); }

/* Flexbox Utilities */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-row { flex-direction: row; }
.justify-start { justify-content: flex-start; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.items-start { align-items: flex-start; }
.items-center { align-items: center; }
.items-end { align-items: flex-end; }
```

### Responsive Breakpoints
```css
:root {
  /* Breakpoint Variables */
  --breakpoint-sm: 640px;   /* Mobile landscape */
  --breakpoint-md: 768px;   /* Tablet portrait */
  --breakpoint-lg: 1024px;  /* Desktop */
  --breakpoint-xl: 1280px;  /* Large desktop */
  --breakpoint-2xl: 1536px; /* Extra large desktop */
}

/* Responsive Grid */
@media (max-width: 767px) {
  .grid-cols-2,
  .grid-cols-3,
  .grid-cols-4 {
    grid-template-columns: 1fr;
  }
  
  .container {
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }
}

@media (min-width: 768px) and (max-width: 1023px) {
  .grid-cols-3,
  .grid-cols-4 {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .container {
    padding-left: var(--space-6);
    padding-right: var(--space-6);
  }
}

@media (min-width: 1024px) {
  .container {
    padding-left: var(--space-8);
    padding-right: var(--space-8);
  }
}
```

---

## 4. Component Library

### Button Components
```css
/* Base Button Styles */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  font-family: var(--font-family-primary);
  font-weight: var(--font-weight-semibold);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  min-height: 44px; /* Touch target size */
  white-space: nowrap;
}

/* Button Sizes */
.btn-sm {
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-sm);
  min-height: 36px;
}

.btn-base {
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-size-base);
  min-height: 44px;
}

.btn-lg {
  padding: var(--space-4) var(--space-6);
  font-size: var(--font-size-lg);
  min-height: 52px;
}

/* Button Variants */
.btn-primary {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  border-color: var(--color-primary-500);
}

.btn-primary:hover {
  background: var(--color-primary-600);
  border-color: var(--color-primary-600);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(26, 140, 255, 0.3);
}

.btn-secondary {
  background: var(--color-surface-primary);
  color: var(--color-text-primary);
  border-color: var(--color-border-primary);
}

.btn-secondary:hover {
  background: var(--color-surface-secondary);
  border-color: var(--color-border-focus);
  transform: translateY(-1px);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text-primary);
  border-color: transparent;
}

.btn-ghost:hover {
  background: var(--color-surface-secondary);
}

.btn-danger {
  background: var(--color-error-500);
  color: var(--color-text-inverse);
  border-color: var(--color-error-500);
}

.btn-danger:hover {
  background: var(--color-error-600);
  border-color: var(--color-error-600);
}

/* Button States */
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--color-primary-200);
}
```

### Chat Interface Components
```css
/* Chat Container */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 768px;
  margin: 0 auto;
  background: var(--color-surface-primary);
}

.chat-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-elevated);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Message Bubbles */
.message {
  display: flex;
  gap: var(--space-3);
  max-width: 100%;
}

.message-user {
  flex-direction: row-reverse;
}

.message-bubble {
  max-width: 75%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  word-wrap: break-word;
}

.message-user .message-bubble {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  border-bottom-right-radius: var(--radius-sm);
}

.message-ai .message-bubble {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-primary);
  border-bottom-left-radius: var(--radius-sm);
}

.message-system {
  justify-content: center;
}

.message-system .message-bubble {
  background: var(--color-surface-tertiary);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  max-width: 60%;
  text-align: center;
}

/* Avatar Styles */
.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-primary-100);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-700);
  flex-shrink: 0;
}

/* Chat Input */
.chat-input-container {
  padding: var(--space-4);
  border-top: 1px solid var(--color-border-primary);
  background: var(--color-surface-elevated);
}

.chat-input-wrapper {
  position: relative;
  display: flex;
  align-items: end;
  gap: var(--space-2);
}

.chat-input {
  flex: 1;
  min-height: 44px;
  max-height: 120px;
  padding: var(--space-3);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
  background: var(--color-surface-primary);
  resize: none;
  outline: none;
}

.chat-input:focus {
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

.chat-input::placeholder {
  color: var(--color-text-tertiary);
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
  font-style: italic;
}

.typing-dots {
  display: flex;
  gap: var(--space-1);
}

.typing-dot {
  width: 4px;
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--color-text-tertiary);
  animation: typing-pulse 1.4s ease-in-out infinite both;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-pulse {
  0%, 80%, 100% { opacity: 0.4; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
```

### Card Components
```css
/* Base Card */
.card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* Milestone Card */
.milestone-card {
  position: relative;
  overflow: hidden;
}

.milestone-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--color-neutral-300);
  transition: background-color 0.2s ease;
}

.milestone-card[data-status="completed"]::before {
  background: var(--color-success-500);
}

.milestone-card[data-status="in-progress"]::before {
  background: var(--color-primary-500);
}

.milestone-card[data-status="locked"]::before {
  background: var(--color-neutral-300);
}

.milestone-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.milestone-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.milestone-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.milestone-status[data-status="completed"] {
  background: var(--color-success-100);
  color: var(--color-success-700);
}

.milestone-status[data-status="in-progress"] {
  background: var(--color-primary-100);
  color: var(--color-primary-700);
}

.milestone-status[data-status="locked"] {
  background: var(--color-neutral-100);
  color: var(--color-neutral-600);
}

.milestone-description {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
  line-height: var(--line-height-relaxed);
}

/* Progress Bar */
.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin: var(--space-4) 0;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary-500);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
  position: relative;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3));
  border-radius: var(--radius-full);
}
```

### Form Components
```css
/* Form Field Container */
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.field-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.field-label.required::after {
  content: ' *';
  color: var(--color-error-500);
}

/* Input Styles */
.input {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  background: var(--color-surface-primary);
  transition: all 0.2s ease;
  min-height: 44px;
}

.input:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px var(--color-primary-100);
}

.input:disabled {
  background: var(--color-surface-secondary);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.input.error {
  border-color: var(--color-error-500);
}

.input.error:focus {
  box-shadow: 0 0 0 3px var(--color-error-100);
}

/* Textarea */
.textarea {
  min-height: 100px;
  resize: vertical;
  font-family: var(--font-family-primary);
}

/* Select */
.select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e");
  background-position: right var(--space-3) center;
  background-repeat: no-repeat;
  background-size: 16px;
  padding-right: var(--space-10);
}

/* Field Helper Text */
.field-help {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  line-height: var(--line-height-normal);
}

.field-error {
  font-size: var(--font-size-sm);
  color: var(--color-error-600);
  line-height: var(--line-height-normal);
}

/* Checkbox & Radio */
.checkbox,
.radio {
  appearance: none;
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  cursor: pointer;
  position: relative;
  margin-right: var(--space-2);
  flex-shrink: 0;
}

.checkbox {
  border-radius: var(--radius-sm);
}

.radio {
  border-radius: var(--radius-full);
}

.checkbox:checked,
.radio:checked {
  border-color: var(--color-primary-500);
  background: var(--color-primary-500);
}

.checkbox:checked::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--color-text-inverse);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.radio:checked::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-text-inverse);
}
```

### Loading & Feedback States
```css
/* Loading Spinner */
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border-primary);
  border-top-color: var(--color-primary-500);
  border-radius: var(--radius-full);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner-sm { width: 16px; height: 16px; }
.spinner-lg { width: 32px; height: 32px; }

/* Skeleton Loading */
.skeleton {
  background: linear-gradient(90deg, 
    var(--color-surface-secondary) 25%, 
    var(--color-surface-tertiary) 50%, 
    var(--color-surface-secondary) 75%
  );
  background-size: 200% 100%;
  animation: loading 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-text {
  height: 1em;
  margin-bottom: var(--space-2);
}

.skeleton-text:last-child {
  width: 60%;
}

/* Toast Notifications */
.toast {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  min-width: 300px;
  position: relative;
}

.toast-success {
  background: var(--color-success-50);
  color: var(--color-success-700);
  border: 1px solid var(--color-success-200);
}

.toast-error {
  background: var(--color-error-50);
  color: var(--color-error-700);
  border: 1px solid var(--color-error-200);
}

.toast-warning {
  background: var(--color-warning-50);
  color: var(--color-warning-700);
  border: 1px solid var(--color-warning-200);
}

.toast-info {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  border: 1px solid var(--color-primary-200);
}

/* Alert Components */
.alert {
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
}

.alert-success {
  background: var(--color-success-50);
  color: var(--color-success-700);
  border-color: var(--color-success-200);
}

.alert-error {
  background: var(--color-error-50);
  color: var(--color-error-700);
  border-color: var(--color-error-200);
}

.alert-warning {
  background: var(--color-warning-50);
  color: var(--color-warning-700);
  border-color: var(--color-warning-200);
}

.alert-info {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  border-color: var(--color-primary-200);
}
```

---

## 5. Animation & Motion System

### Timing & Easing
```css
:root {
  /* Duration Scale */
  --duration-75: 75ms;
  --duration-100: 100ms;
  --duration-150: 150ms;
  --duration-200: 200ms;
  --duration-300: 300ms;
  --duration-500: 500ms;
  --duration-700: 700ms;
  --duration-1000: 1000ms;
  
  /* Easing Functions */
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-sharp: cubic-bezier(0.4, 0, 0.6, 1);
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
```

### Animation Classes
```css
/* Fade Transitions */
.fade-enter {
  opacity: 0;
  transform: translateY(var(--space-2));
}

.fade-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: opacity var(--duration-300) var(--ease-out),
              transform var(--duration-300) var(--ease-out);
}

.fade-exit {
  opacity: 1;
  transform: translateY(0);
}

.fade-exit-active {
  opacity: 0;
  transform: translateY(calc(-1 * var(--space-2)));
  transition: opacity var(--duration-200) var(--ease-in),
              transform var(--duration-200) var(--ease-in);
}

/* Slide Transitions */
.slide-up-enter {
  opacity: 0;
  transform: translateY(var(--space-8));
}

.slide-up-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: all var(--duration-300) var(--ease-out);
}

/* Scale Animations */
.scale-enter {
  opacity: 0;
  transform: scale(0.95);
}

.scale-enter-active {
  opacity: 1;
  transform: scale(1);
  transition: all var(--duration-200) var(--ease-out);
}

/* Hover Animations */
.hover-lift {
  transition: transform var(--duration-200) var(--ease-out);
}

.hover-lift:hover {
  transform: translateY(-2px);
}

.hover-grow {
  transition: transform var(--duration-200) var(--ease-out);
}

.hover-grow:hover {
  transform: scale(1.05);
}

/* Loading Animations */
.pulse {
  animation: pulse var(--duration-1000) var(--ease-in-out) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.bounce {
  animation: bounce var(--duration-1000) var(--ease-bounce) infinite;
}

@keyframes bounce {
  0%, 20%, 53%, 80%, 100% { transform: translate3d(0,0,0); }
  40%, 43% { transform: translate3d(0, -30px, 0); }
  70% { transform: translate3d(0, -15px, 0); }
  90% { transform: translate3d(0, -4px, 0); }
}
```

---

## 6. Accessibility Specifications

### Focus Management
```css
/* Focus Ring System */
:root {
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
  --focus-ring-color: var(--color-primary-500);
}

*:focus {
  outline: none;
}

.focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

/* High Contrast Focus for Form Elements */
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
button:focus-visible {
  box-shadow: 0 0 0 2px var(--color-surface-primary),
              0 0 0 4px var(--focus-ring-color);
}

/* Skip Links */
.skip-link {
  position: absolute;
  top: var(--space-4);
  left: var(--space-4);
  background: var(--color-surface-primary);
  color: var(--color-text-primary);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  z-index: 1000;
  transform: translateY(-100px);
  transition: transform var(--duration-200) var(--ease-out);
}

.skip-link:focus {
  transform: translateY(0);
}

/* Screen Reader Only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.sr-only-focusable:focus {
  position: static;
  width: auto;
  height: auto;
  overflow: visible;
  clip: auto;
  white-space: normal;
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
  :root {
    --color-border-primary: var(--color-neutral-900);
    --color-text-primary: var(--color-neutral-900);
    --focus-ring-width: 3px;
  }
  
  .btn {
    border-width: 2px;
  }
  
  .input,
  .textarea,
  .select {
    border-width: 2px;
  }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### ARIA & Semantic Patterns
```css
/* ARIA State Indicators */
[aria-expanded="false"] .expandable-content {
  display: none;
}

[aria-expanded="true"] .expandable-content {
  display: block;
}

[aria-hidden="true"] {
  display: none !important;
}

/* Live Region Styles */
.live-region {
  position: absolute;
  left: -10000px;
  width: 1px;
  height: 1px;
  overflow: hidden;
}

/* Error Message Styling */
.error-message {
  color: var(--color-error-600);
  font-size: var(--font-size-sm);
  margin-top: var(--space-1);
}

[aria-invalid="true"] {
  border-color: var(--color-error-500);
}
```

---

## 7. Dark Mode Implementation

### Theme Toggle
```css
/* Theme Toggle Button */
.theme-toggle {
  position: relative;
  width: 48px;
  height: 24px;
  background: var(--color-neutral-300);
  border-radius: var(--radius-full);
  border: none;
  cursor: pointer;
  transition: background-color var(--duration-200) var(--ease-out);
}

.theme-toggle[data-theme="dark"] {
  background: var(--color-primary-600);
}

.theme-toggle-indicator {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: var(--color-surface-primary);
  border-radius: var(--radius-full);
  transition: transform var(--duration-200) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
}

.theme-toggle[data-theme="dark"] .theme-toggle-indicator {
  transform: translateX(24px);
}

/* System Preference Detection */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* Apply dark theme variables automatically */
  }
}

/* Theme Transition */
.theme-transition * {
  transition: background-color var(--duration-300) var(--ease-out),
              border-color var(--duration-300) var(--ease-out),
              color var(--duration-300) var(--ease-out);
}
```

### Dark Mode Specific Adjustments
```css
[data-theme="dark"] {
  /* Enhanced contrast for better readability */
  --color-text-primary: #F8FAFC;
  --color-text-secondary: #CBD5E1;
  --color-text-tertiary: #94A3B8;
  
  /* Adjusted surface colors for depth */
  --color-surface-primary: #0F172A;
  --color-surface-secondary: #1E293B;
  --color-surface-tertiary: #334155;
  --color-surface-elevated: #1E293B;
  
  /* Dark mode specific shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.5);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
}

/* Dark mode image filters */
[data-theme="dark"] img {
  opacity: 0.9;
  filter: brightness(0.9);
}

/* Dark mode code blocks */
[data-theme="dark"] .code {
  background: var(--color-neutral-800);
  color: var(--color-primary-300);
}
```

---

## 8. Implementation Guidelines

### CSS Custom Properties Usage
```css
/* Use CSS custom properties for all design tokens */
.component {
  /* ✅ Good - Uses design token */
  color: var(--color-text-primary);
  padding: var(--space-4);
  
  /* ❌ Bad - Hard-coded values */
  color: #333333;
  padding: 16px;
}

/* Component variants should extend base styles */
.btn-large {
  /* Extends .btn base class */
  padding: var(--space-4) var(--space-6);
  font-size: var(--font-size-lg);
}
```

### Performance Considerations
```css
/* Use transform and opacity for animations */
.animated-element {
  /* ✅ Good - GPU accelerated */
  transform: translateX(0);
  opacity: 1;
  transition: transform var(--duration-300) var(--ease-out);
  
  /* ❌ Bad - Forces layout recalculation */
  left: 0;
  transition: left var(--duration-300) var(--ease-out);
}

/* Use will-change for heavy animations */
.heavy-animation {
  will-change: transform, opacity;
}

.heavy-animation.animation-complete {
  will-change: auto;
}
```

### Component Composition Patterns
```css
/* Base + Modifier Pattern */
.card { /* Base styles */ }
.card--elevated { /* Modifier */ }
.card--interactive { /* Modifier */ }

/* BEM Methodology */
.milestone-card { /* Block */ }
.milestone-card__header { /* Element */ }
.milestone-card__header--completed { /* Modifier */ }

/* Utility Classes */
.text-center { text-align: center; }
.mb-4 { margin-bottom: var(--space-4); }
.sr-only { /* Screen reader only */ }
```

### JavaScript Integration
```javascript
// Theme switching
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
}

// System preference detection
function initializeTheme() {
  const savedTheme = localStorage.getItem('theme');
  const systemPreference = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const theme = savedTheme || systemPreference;
  
  document.documentElement.setAttribute('data-theme', theme);
}

// Animation state management
function addAnimationClass(element, className, duration = 300) {
  element.classList.add(className);
  
  setTimeout(() => {
    element.classList.remove(className);
  }, duration);
}

// Accessibility helpers
function announceToScreenReader(message) {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', 'polite');
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}
```

---

## 9. Quality Assurance Checklist

### Design Token Compliance
- [ ] All colors use CSS custom properties
- [ ] Typography follows established scale
- [ ] Spacing uses consistent scale values
- [ ] Border radius uses defined values
- [ ] Shadows follow established patterns

### Accessibility Requirements
- [ ] WCAG 2.1 AA contrast ratios met (4.5:1 minimum)
- [ ] Keyboard navigation fully functional
- [ ] Screen reader markup complete
- [ ] Focus indicators clearly visible
- [ ] Touch targets minimum 44px

### Responsive Design
- [ ] Mobile-first implementation
- [ ] Breakpoints correctly implemented
- [ ] Typography scales appropriately
- [ ] Touch interactions optimized
- [ ] Horizontal scrolling eliminated

### Performance Optimization
- [ ] CSS custom properties used efficiently
- [ ] Animations use transform/opacity
- [ ] Critical CSS inlined
- [ ] Unused styles removed
- [ ] Asset optimization completed

### Dark Mode Support
- [ ] All components work in both themes
- [ ] Color contrast maintained in dark mode
- [ ] Images and media adjusted appropriately
- [ ] Theme toggle functionality working
- [ ] System preference detection active

This comprehensive design system ensures consistency, accessibility, and performance across the entire ProLaunch.AI application while providing clear implementation guidelines for the development team.