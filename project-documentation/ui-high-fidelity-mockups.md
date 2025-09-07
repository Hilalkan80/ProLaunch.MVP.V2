# ProLaunch.AI High-Fidelity Screen Mockups

## Overview
This document provides detailed high-fidelity mockups for key screens in the ProLaunch.AI application, showing exact visual specifications, content, and interactive elements.

---

## 1. Landing Page - Desktop (1280px)

### Header Section
```css
/* Header Implementation */
.landing-header {
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border-primary);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-8);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
}

.nav-links {
  display: flex;
  gap: var(--space-6);
  align-items: center;
}

.nav-link {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  transition: color var(--duration-200) var(--ease-out);
}

.nav-link:hover {
  color: var(--color-primary-600);
}
```

### Hero Section
```css
/* Hero Section Layout */
.hero-section {
  background: linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%);
  padding: var(--space-20) 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 var(--space-8);
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-6);
}

.hero-title {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
  margin-bottom: var(--space-6);
}

.hero-subtitle {
  font-size: var(--font-size-xl);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  margin-bottom: var(--space-8);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-cta {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  align-items: center;
  margin-bottom: var(--space-12);
}
```

### Chat Widget Integration
```css
/* Floating Chat Widget */
.chat-widget {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  width: 400px;
  height: 500px;
  background: var(--color-surface-elevated);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 
              0 10px 10px -5px rgba(0, 0, 0, 0.04);
  z-index: 1000;
  transition: all var(--duration-300) var(--ease-out);
  overflow: hidden;
}

.chat-widget.minimized {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-full);
}

.chat-header {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  color: var(--color-text-inverse);
  padding: var(--space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.chat-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: #22C55E;
  animation: pulse 2s infinite;
}
```

### Social Proof Section
```css
/* Social Proof Layout */
.social-proof {
  padding: var(--space-16) 0;
  background: var(--color-surface-primary);
}

.proof-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-8);
  text-align: center;
}

.proof-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-8);
  margin-bottom: var(--space-12);
}

.stat-item {
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
}

.stat-number {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  margin-bottom: var(--space-2);
}

.stat-label {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.testimonial-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-6);
  margin-top: var(--space-12);
}

.testimonial-card {
  background: var(--color-surface-elevated);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  text-align: left;
}

.testimonial-quote {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  line-height: var(--line-height-relaxed);
  margin-bottom: var(--space-4);
}

.testimonial-author {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.author-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--color-primary-100);
}

.author-info {
  flex: 1;
}

.author-name {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.author-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}
```

---

## 2. Chat Interface - Desktop

### Main Chat Layout
```css
/* Chat Interface Container */
.chat-interface {
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100vh;
  background: var(--color-surface-primary);
}

.chat-sidebar {
  background: var(--color-surface-secondary);
  border-right: 1px solid var(--color-border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.progress-overview {
  padding: var(--space-4);
}

.overall-progress {
  margin-bottom: var(--space-6);
}

.progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.progress-percentage {
  color: var(--color-primary-600);
  font-weight: var(--font-weight-bold);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-neutral-200);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-500), var(--color-primary-400));
  border-radius: var(--radius-full);
  width: 78%;
  position: relative;
}

.milestone-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.milestone-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-200) var(--ease-out);
}

.milestone-item:hover {
  background: var(--color-surface-tertiary);
}

.milestone-item.active {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
}

.milestone-status {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
}

.status-completed {
  background: var(--color-success-500);
  color: var(--color-text-inverse);
}

.status-in-progress {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  animation: pulse 2s infinite;
}

.status-locked {
  background: var(--color-neutral-300);
  color: var(--color-neutral-600);
}

.milestone-info {
  flex: 1;
  min-width: 0;
}

.milestone-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--space-1);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.milestone-subtitle {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

### Chat Messages Area
```css
/* Chat Main Content */
.chat-main {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.chat-header {
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-elevated);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.chat-subtitle {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--space-1);
}

.chat-actions {
  display: flex;
  gap: var(--space-2);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Enhanced Message Styling */
.message {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.message-user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-primary-100);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
}

.message-user .message-avatar {
  background: var(--color-success-100);
  color: var(--color-success-700);
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.message-bubble {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  word-wrap: break-word;
  position: relative;
}

.message-user .message-bubble {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
  border-bottom-right-radius: var(--radius-sm);
}

.message-ai .message-bubble {
  background: var(--color-surface-elevated);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-primary);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.message-timestamp {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  align-self: flex-end;
  margin-top: var(--space-1);
}

/* Interactive Message Cards */
.message-card {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-top: var(--space-2);
  box-shadow: var(--shadow-sm);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.card-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.card-badge {
  background: var(--color-primary-50);
  color: var(--color-primary-700);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.card-content {
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  margin-bottom: var(--space-3);
}

.card-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}
```

### Chat Input Area
```css
/* Enhanced Chat Input */
.chat-input-area {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border-primary);
  background: var(--color-surface-elevated);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface-primary);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-xl);
  transition: all var(--duration-200) var(--ease-out);
}

.input-wrapper:focus-within {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 4px var(--color-primary-50);
}

.chat-textarea {
  flex: 1;
  min-height: 24px;
  max-height: 120px;
  resize: none;
  border: none;
  outline: none;
  background: transparent;
  font-family: var(--font-family-primary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-normal);
  color: var(--color-text-primary);
}

.chat-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.input-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.action-button {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--duration-200) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-button:hover {
  background: var(--color-surface-secondary);
  color: var(--color-primary-500);
}

.send-button {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
}

.send-button:hover {
  background: var(--color-primary-600);
  transform: scale(1.1);
}

.send-button:disabled {
  background: var(--color-neutral-300);
  color: var(--color-neutral-500);
  cursor: not-allowed;
  transform: none;
}

/* Quick Actions */
.quick-actions {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}

.quick-action {
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-border-primary);
  color: var(--color-text-secondary);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: all var(--duration-200) var(--ease-out);
}

.quick-action:hover {
  background: var(--color-primary-50);
  border-color: var(--color-primary-200);
  color: var(--color-primary-700);
}
```

---

## 3. M0 Feasibility Report - Desktop

### Report Header
```css
/* Feasibility Report Layout */
.report-container {
  max-width: 1024px;
  margin: 0 auto;
  padding: var(--space-8);
  background: var(--color-surface-primary);
}

.report-header {
  text-align: center;
  padding-bottom: var(--space-8);
  border-bottom: 1px solid var(--color-border-primary);
  margin-bottom: var(--space-8);
}

.report-title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.report-subtitle {
  font-size: var(--font-size-xl);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
}

.report-meta {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.report-actions {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
}
```

### Viability Score Section
```css
/* Viability Score Display */
.viability-section {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: var(--space-8);
  margin-bottom: var(--space-12);
  padding: var(--space-8);
  background: linear-gradient(135deg, var(--color-primary-50), var(--color-success-50));
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-primary-100);
}

.score-display {
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.score-circle {
  width: 200px;
  height: 200px;
  border-radius: var(--radius-full);
  background: conic-gradient(var(--color-primary-500) 78%, var(--color-neutral-200) 78%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: var(--space-4);
}

.score-circle::before {
  content: '';
  width: 160px;
  height: 160px;
  border-radius: var(--radius-full);
  background: var(--color-surface-primary);
  position: absolute;
}

.score-number {
  font-size: var(--font-size-5xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  position: relative;
  z-index: 1;
}

.score-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--letter-spacing-wider);
  margin-top: var(--space-1);
}

.score-status {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-success-600);
  margin-top: var(--space-2);
}

.key-insights {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.insights-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.insights-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.insight-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: rgba(255, 255, 255, 0.8);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.insight-icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}

.insight-positive {
  background: var(--color-success-100);
  color: var(--color-success-700);
}

.insight-warning {
  background: var(--color-warning-100);
  color: var(--color-warning-700);
}

.insight-text {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  line-height: var(--line-height-normal);
}
```

### Market Analysis Section
```css
/* Market Analysis Layout */
.market-section {
  margin-bottom: var(--space-12);
}

.section-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.section-icon {
  width: 32px;
  height: 32px;
  background: var(--color-primary-100);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-lg);
  color: var(--color-primary-600);
}

.market-overview {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin-bottom: var(--space-6);
}

.market-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-6);
  margin-bottom: var(--space-6);
}

.stat-item {
  text-align: center;
  padding: var(--space-4);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
}

.stat-number {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  margin-bottom: var(--space-2);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stat-source {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-1);
}

.source-link {
  color: var(--color-primary-600);
  text-decoration: none;
}

.source-link:hover {
  text-decoration: underline;
}

/* Competitor Analysis */
.competitor-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
}

.competitors-list {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.competitor-item {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-secondary);
  margin-bottom: var(--space-4);
}

.competitor-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.competitor-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.competitor-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.rating-stars {
  color: var(--color-warning-500);
  font-size: var(--font-size-sm);
}

.pricing-analysis {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.price-range {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--color-surface-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-3);
}

.price-tier {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.price-value {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
}

.recommended-price {
  background: linear-gradient(135deg, var(--color-success-50), var(--color-primary-50));
  border: 2px solid var(--color-primary-200);
  color: var(--color-primary-700);
}

.recommended-price .price-tier {
  color: var(--color-primary-700);
  font-weight: var(--font-weight-bold);
}

.recommended-price .price-value {
  color: var(--color-primary-600);
  font-weight: var(--font-weight-bold);
}
```

### Next Steps Section
```css
/* Next Steps Action Items */
.next-steps {
  background: var(--color-surface-elevated);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  margin-bottom: var(--space-12);
}

.steps-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  text-align: center;
  margin-bottom: var(--space-8);
}

.steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.step-item {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  transition: all var(--duration-200) var(--ease-out);
}

.step-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.step-number {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background: var(--color-primary-100);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
}

.step-description {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
}

.step-action {
  flex-shrink: 0;
}

.step-button {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  border: none;
  cursor: pointer;
  transition: all var(--duration-200) var(--ease-out);
}

.step-button.primary {
  background: var(--color-primary-500);
  color: var(--color-text-inverse);
}

.step-button.primary:hover {
  background: var(--color-primary-600);
  transform: scale(1.05);
}

.step-button.secondary {
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-primary);
}

.step-button.secondary:hover {
  background: var(--color-surface-tertiary);
  color: var(--color-text-primary);
}

.step-button.locked {
  background: var(--color-neutral-100);
  color: var(--color-neutral-500);
  cursor: not-allowed;
}
```

### Upgrade CTA Section
```css
/* Upgrade Call-to-Action */
.upgrade-cta {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  color: var(--color-text-inverse);
  border-radius: var(--radius-xl);
  padding: var(--space-10);
  text-align: center;
  position: relative;
  overflow: hidden;
  margin-bottom: var(--space-8);
}

.upgrade-cta::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="1"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
}

.upgrade-content {
  position: relative;
  z-index: 1;
}

.upgrade-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-4);
}

.upgrade-description {
  font-size: var(--font-size-lg);
  opacity: 0.9;
  margin-bottom: var(--space-8);
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.upgrade-features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  max-width: 800px;
  margin: 0 auto var(--space-8);
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-base);
  color: rgba(255, 255, 255, 0.9);
}

.feature-icon {
  width: 20px;
  height: 20px;
  color: var(--color-success-300);
  flex-shrink: 0;
}

.upgrade-pricing {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-2);
}

.upgrade-guarantee {
  font-size: var(--font-size-sm);
  opacity: 0.8;
  margin-bottom: var(--space-6);
}

.upgrade-button {
  background: var(--color-surface-primary);
  color: var(--color-primary-600);
  padding: var(--space-4) var(--space-8);
  border-radius: var(--radius-xl);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  border: none;
  cursor: pointer;
  transition: all var(--duration-300) var(--ease-out);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.upgrade-button:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}
```

---

## 4. Mobile Responsive Adaptations

### Mobile Chat Interface (375px)
```css
/* Mobile Chat Layout */
@media (max-width: 768px) {
  .chat-interface {
    grid-template-columns: 1fr;
    position: relative;
  }
  
  .chat-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform var(--duration-300) var(--ease-out);
  }
  
  .sidebar-open .chat-sidebar {
    transform: translateX(0);
  }
  
  .sidebar-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 999;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-300) var(--ease-out);
  }
  
  .sidebar-open .sidebar-backdrop {
    opacity: 1;
    pointer-events: auto;
  }
  
  .mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4);
    border-bottom: 1px solid var(--color-border-primary);
    background: var(--color-surface-elevated);
  }
  
  .mobile-menu-button {
    width: 44px;
    height: 44px;
    border: none;
    background: transparent;
    color: var(--color-text-primary);
    cursor: pointer;
    border-radius: var(--radius-lg);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .mobile-menu-button:hover {
    background: var(--color-surface-secondary);
  }
  
  .messages-container {
    padding: var(--space-4);
    height: calc(100vh - 140px);
  }
  
  .message-content {
    max-width: 85%;
  }
  
  .chat-input-area {
    padding: var(--space-4);
    position: sticky;
    bottom: 0;
  }
  
  .input-wrapper {
    padding: var(--space-2);
  }
  
  .quick-actions {
    overflow-x: auto;
    padding-bottom: var(--space-2);
  }
  
  .quick-action {
    white-space: nowrap;
    flex-shrink: 0;
  }
}

/* Mobile Report Layout */
@media (max-width: 768px) {
  .report-container {
    padding: var(--space-4);
  }
  
  .report-title {
    font-size: var(--font-size-3xl);
  }
  
  .viability-section {
    grid-template-columns: 1fr;
    gap: var(--space-6);
    padding: var(--space-6);
  }
  
  .score-circle {
    width: 160px;
    height: 160px;
  }
  
  .score-circle::before {
    width: 120px;
    height: 120px;
  }
  
  .score-number {
    font-size: var(--font-size-4xl);
  }
  
  .market-stats {
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }
  
  .competitor-section {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }
  
  .upgrade-features {
    grid-template-columns: 1fr;
    gap: var(--space-3);
  }
  
  .upgrade-button {
    width: 100%;
    padding: var(--space-4);
  }
}
```

### Touch Interactions
```css
/* Touch-Optimized Interactions */
@media (hover: none) and (pointer: coarse) {
  .hover-lift:hover {
    transform: none;
  }
  
  .btn:hover {
    transform: none;
    box-shadow: none;
  }
  
  /* Tap feedback for touch devices */
  .btn:active {
    transform: scale(0.98);
    transition: transform var(--duration-100) var(--ease-out);
  }
  
  .card:active {
    transform: scale(0.99);
    transition: transform var(--duration-100) var(--ease-out);
  }
  
  /* Larger touch targets */
  .message-card {
    padding: var(--space-5);
  }
  
  .chat-input {
    min-height: 48px;
    font-size: 16px; /* Prevents zoom on iOS */
  }
  
  .action-button {
    width: 44px;
    height: 44px;
  }
  
  /* Improved mobile scrolling */
  .messages-container {
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }
}

/* Dark Mode Mobile Adjustments */
[data-theme="dark"] {
  .mobile-header {
    background: var(--color-surface-secondary);
    border-bottom-color: var(--color-border-primary);
  }
  
  .chat-input-area {
    background: var(--color-surface-secondary);
    border-top-color: var(--color-border-primary);
  }
  
  .sidebar-backdrop {
    background: rgba(0, 0, 0, 0.8);
  }
}
```

This comprehensive set of high-fidelity mockups provides pixel-perfect specifications for implementing the ProLaunch.AI interface across all device sizes, ensuring consistency and optimal user experience.