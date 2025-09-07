# ProLaunch.AI High-Fidelity Mockups

## Landing Page

### Header Section
```css
.header {
  height: 80px;
  background: white;
  border-bottom: 1px solid var(--neutral-200);
  padding: 0 var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  height: 32px;
}

.nav-links {
  display: flex;
  gap: var(--space-8);
}

.sign-up-btn {
  background: var(--primary-500);
  color: white;
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-full);
  font-weight: 500;
}
```

### Hero Section
```css
.hero {
  padding: var(--space-20) var(--space-6);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-12);
  max-width: var(--container-xl);
  margin: 0 auto;
}

.hero-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  justify-content: center;
}

.hero-title {
  font-size: var(--text-5xl);
  font-weight: 700;
  line-height: var(--leading-tight);
  letter-spacing: -0.02em;
  color: var(--neutral-900);
}

.hero-subtitle {
  font-size: var(--text-xl);
  color: var(--neutral-600);
  line-height: var(--leading-relaxed);
}

.chat-widget {
  background: white;
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-xl);
  padding: var(--space-6);
  height: 480px;
  display: flex;
  flex-direction: column;
}
```

## Chat Interface

### Layout Structure
```css
.chat-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
}

.sidebar {
  background: white;
  border-right: 1px solid var(--neutral-200);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.chat-main {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
}

.chat-input-container {
  border-top: 1px solid var(--neutral-200);
  padding: var(--space-4) var(--space-6);
}
```

### Message Components
```css
.message {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary-100);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  flex: 1;
  background: var(--neutral-100);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
}

.message-user .message-content {
  background: var(--primary-500);
  color: white;
}
```

## M0 Feasibility Report

### Report Header
```css
.report-header {
  padding: var(--space-8);
  background: white;
  border-bottom: 1px solid var(--neutral-200);
}

.viability-score {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 8px solid var(--primary-500);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-4xl);
  font-weight: 700;
}
```

### Report Sections
```css
.report-section {
  padding: var(--space-8);
  border-bottom: 1px solid var(--neutral-200);
}

.section-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-6);
}

.insight-card {
  background: var(--neutral-50);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.citation {
  font-size: var(--text-sm);
  color: var(--neutral-500);
  margin-top: var(--space-2);
}
```

## Mobile Responsive Styles

### Mobile Header
```css
@media (max-width: 768px) {
  .header {
    padding: var(--space-4);
  }

  .nav-links {
    display: none;
  }

  .mobile-menu-btn {
    display: block;
  }
}
```

### Mobile Chat
```css
@media (max-width: 1024px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 200ms ease;
    z-index: 50;
  }

  .sidebar.open {
    transform: translateX(0);
  }
}
```

### Mobile Report
```css
@media (max-width: 768px) {
  .section-grid {
    grid-template-columns: 1fr;
  }

  .report-header {
    padding: var(--space-4);
  }

  .score-circle {
    width: 80px;
    height: 80px;
    border-width: 6px;
    font-size: var(--text-2xl);
  }
}
```

## Dark Mode Styles

### Dark Theme Colors
```css
[data-theme="dark"] {
  --page-background: var(--neutral-900);
  --card-background: var(--neutral-800);
  --border-color: var(--neutral-700);
  --text-primary: var(--neutral-100);
  --text-secondary: var(--neutral-400);
}
```

### Dark Components
```css
[data-theme="dark"] .header {
  background: var(--card-background);
  border-color: var(--border-color);
}

[data-theme="dark"] .chat-message {
  background: var(--card-background);
}

[data-theme="dark"] .insight-card {
  background: var(--card-background);
  border: 1px solid var(--border-color);
}
```