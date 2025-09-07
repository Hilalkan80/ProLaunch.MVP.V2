# Manual Accessibility Testing Procedures for M0 Components

This document provides comprehensive manual testing procedures to complement automated accessibility testing. These procedures ensure WCAG 2.1 AA compliance and optimal user experience for users with disabilities.

## Table of Contents

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Keyboard Navigation Testing](#keyboard-navigation-testing)
3. [Screen Reader Testing](#screen-reader-testing)
4. [Visual and Color Testing](#visual-and-color-testing)
5. [Cognitive and Motor Accessibility](#cognitive-and-motor-accessibility)
6. [Mobile Accessibility Testing](#mobile-accessibility-testing)
7. [Cross-Browser Testing](#cross-browser-testing)
8. [Reporting and Documentation](#reporting-and-documentation)

## Pre-Testing Setup

### Required Tools

1. **Screen Readers:**
   - NVDA (Windows) - Free
   - JAWS (Windows) - Commercial
   - VoiceOver (macOS) - Built-in
   - TalkBack (Android) - Built-in
   - VoiceOver (iOS) - Built-in

2. **Browser Extensions:**
   - axe DevTools (Chrome/Firefox)
   - WAVE Web Accessibility Evaluator
   - Lighthouse (Chrome DevTools)
   - Accessibility Insights for Web (Microsoft)

3. **Testing Devices:**
   - Desktop/laptop with keyboard
   - Mobile device (iOS/Android)
   - Tablet device

4. **Browser Settings:**
   - High contrast mode
   - Reduced motion settings
   - Zoom functionality (up to 200%)

### Environment Preparation

```bash
# Install testing dependencies
npm install --save-dev @axe-core/react jest-axe axe-core

# Run accessibility tests
npm run test:accessibility

# Start development server
npm run dev
```

## Keyboard Navigation Testing

### 1. Tab Order and Focus Management

**Test Steps:**
1. Load the component in browser
2. Use only Tab/Shift+Tab keys to navigate
3. Document focus order and any issues

**Success Criteria:**
- [ ] All interactive elements are reachable via keyboard
- [ ] Tab order follows logical sequence (left-to-right, top-to-bottom)
- [ ] Focus indicators are visible and have sufficient contrast
- [ ] No elements receive focus that shouldn't (decorative elements)
- [ ] Focus doesn't get trapped unless intended (modals, dropdowns)

**Test Cases for M0 Components:**

#### ProductIdeaForm
```
Expected Tab Order:
1. Product idea textarea
2. Suggestion chips (if interactive)
3. Clear button (when enabled)
4. Submit button (when enabled)
```

**Manual Test:**
```
1. Navigate to ProductIdeaForm
2. Press Tab - should focus on textarea
3. Type some text
4. Press Tab - should move to next interactive element
5. Continue tabbing through all elements
6. Use Shift+Tab to reverse navigation
```

#### ProcessingView
```
Expected Tab Order:
1. Cancel button (primary action)
2. Any other interactive elements
```

#### FeasibilityReport
```
Expected Tab Order:
1. Expandable sections (if any)
2. Action buttons (Start Next Step, Upgrade, etc.)
3. Share/Export buttons (if present)
```

### 2. Keyboard Shortcuts and Interactions

**Test Steps:**
1. Test Enter key on buttons and links
2. Test Space key on buttons
3. Test Escape key for dismissing modals/overlays
4. Test arrow keys in custom components

**Success Criteria:**
- [ ] Enter key activates buttons and links
- [ ] Space key activates buttons
- [ ] Escape key dismisses modals and returns focus appropriately
- [ ] Arrow keys work for navigation where expected

### 3. Focus Trapping (for modals and overlays)

**Test Steps:**
1. Open any modal or overlay component
2. Tab through all elements
3. Verify focus stays within modal
4. Test Escape key to close

**Success Criteria:**
- [ ] Focus moves to modal when opened
- [ ] Tab cycles within modal only
- [ ] Shift+Tab cycles in reverse within modal
- [ ] Escape closes modal and returns focus to trigger

## Screen Reader Testing

### 1. Content Structure and Navigation

**Test with NVDA (Windows):**
```
1. Start NVDA
2. Navigate to component
3. Use heading navigation (H key)
4. Use landmark navigation (D key)
5. Use form navigation (F key)
6. Use button navigation (B key)
```

**Success Criteria:**
- [ ] Page title is announced correctly
- [ ] Headings create logical hierarchy (H1 > H2 > H3)
- [ ] Landmarks (main, nav, form) are properly identified
- [ ] Form fields have clear labels
- [ ] Buttons have descriptive names

**Test with VoiceOver (macOS):**
```
1. Enable VoiceOver (Cmd+F5)
2. Navigate with VO+Right Arrow
3. Use rotor to navigate by headings (VO+U)
4. Test form navigation (VO+Cmd+J)
```

### 2. Dynamic Content Announcements

**Test Steps:**
1. Interact with components that change content
2. Monitor screen reader announcements
3. Verify appropriate use of aria-live regions

**M0 Component Test Cases:**

#### ProductIdeaForm Validation
```
Test Scenario: Invalid input submission
Expected Behavior:
- Error message announced via aria-live="assertive" or role="alert"
- Field marked with aria-invalid="true"
- Error associated with field via aria-describedby
```

#### ProcessingView Updates
```
Test Scenario: Processing progress updates
Expected Behavior:
- Progress changes announced via aria-live="polite"
- Current step changes clearly announced
- Time updates announced appropriately
```

#### FeasibilityReport Generation
```
Test Scenario: Report appears after processing
Expected Behavior:
- Report appearance announced
- Focus moves to report heading
- Report structure is navigable
```

### 3. Form Testing with Screen Readers

**Test Steps:**
1. Navigate to form fields
2. Verify labels are announced
3. Test error states
4. Test required field indicators

**Success Criteria:**
- [ ] Field labels are clear and descriptive
- [ ] Required fields are identified
- [ ] Field types are announced correctly
- [ ] Instructions and help text are associated
- [ ] Error messages are announced immediately

## Visual and Color Testing

### 1. Color Contrast Testing

**Manual Tools:**
- Browser DevTools contrast ratio checker
- WebAIM Contrast Checker
- Colour Contrast Analyser (desktop app)

**Test Steps:**
1. Check all text/background combinations
2. Test hover and focus states
3. Verify information isn't conveyed by color alone

**Success Criteria:**
- [ ] Normal text: 4.5:1 contrast ratio minimum
- [ ] Large text (18pt+): 3:1 contrast ratio minimum  
- [ ] Non-text elements: 3:1 contrast ratio minimum
- [ ] Focus indicators: 3:1 contrast ratio minimum

**M0 Component Test Cases:**

#### Color Usage Validation
```
Elements to Test:
- Button text on button backgrounds
- Error messages on backgrounds
- Success states (green indicators)
- Progress indicators
- Link colors
- Placeholder text
- Disabled states
```

### 2. High Contrast Mode Testing

**Windows High Contrast:**
1. Settings > Ease of Access > High Contrast
2. Enable high contrast mode
3. Test all components

**Success Criteria:**
- [ ] All content remains visible
- [ ] Focus indicators are visible
- [ ] Borders and outlines appear
- [ ] Custom styles respect system colors

### 3. Zoom and Magnification Testing

**Test Steps:**
1. Zoom browser to 200% (Ctrl/Cmd + '+')
2. Test functionality at various zoom levels
3. Test horizontal scrolling behavior

**Success Criteria:**
- [ ] Content remains usable at 200% zoom
- [ ] No horizontal scrolling in responsive breakpoints
- [ ] Touch targets remain adequate size
- [ ] Content doesn't overlap

## Cognitive and Motor Accessibility

### 1. Motion and Animation Testing

**Test Steps:**
1. Enable "Reduce Motion" in OS settings
2. Test component animations
3. Verify essential animations remain functional

**Success Criteria:**
- [ ] Animations respect prefers-reduced-motion
- [ ] Essential motion (loading indicators) still functions
- [ ] No automatically playing videos/animations
- [ ] Parallax and decorative animations are disabled

### 2. Timing and Session Testing

**Test Steps:**
1. Test processing timeouts
2. Verify warning before session expires
3. Test ability to extend sessions

**Success Criteria:**
- [ ] No unexpected time limits
- [ ] Users can extend time limits
- [ ] Warnings provided before timeout
- [ ] Essential functions don't depend on timing

### 3. Error Prevention and Recovery

**Test Steps:**
1. Attempt invalid inputs
2. Test error recovery flows
3. Verify confirmation for destructive actions

**Success Criteria:**
- [ ] Clear error messages with recovery instructions
- [ ] Confirmation required for destructive actions
- [ ] Form data preserved during errors
- [ ] Multiple ways to correct errors

## Mobile Accessibility Testing

### 1. Touch Target Testing

**Test Steps:**
1. Test on actual mobile device
2. Verify touch target sizes
3. Test spacing between targets

**Success Criteria:**
- [ ] Touch targets minimum 44px × 44px
- [ ] Adequate spacing between targets
- [ ] Touch targets don't overlap
- [ ] Gestures have alternatives

### 2. Screen Reader Testing (Mobile)

**iOS VoiceOver:**
```
1. Settings > Accessibility > VoiceOver > On
2. Navigate with swipe gestures
3. Test double-tap to activate
4. Test rotor functionality
```

**Android TalkBack:**
```
1. Settings > Accessibility > TalkBack > On
2. Navigate with explore by touch
3. Test double-tap to activate
4. Test reading controls
```

### 3. Orientation and Viewport Testing

**Test Steps:**
1. Test portrait and landscape orientations
2. Test different viewport sizes
3. Verify content reflow

**Success Criteria:**
- [ ] Content works in both orientations
- [ ] No loss of functionality in landscape
- [ ] Viewport meta tag configured correctly
- [ ] Content reflows appropriately

## Cross-Browser Testing

### Browser/Screen Reader Combinations

**Recommended Test Matrix:**
- Chrome + NVDA (Windows)
- Firefox + NVDA (Windows)  
- Edge + NVDA (Windows)
- Safari + VoiceOver (macOS)
- Chrome + VoiceOver (macOS)

**Test Steps:**
1. Test core functionality in each combination
2. Document any browser-specific issues
3. Verify ARIA support consistency

## Testing Checklists

### Quick Pre-Release Checklist

**Keyboard Navigation (5 minutes):**
- [ ] Tab through entire component
- [ ] Enter/Space activate buttons
- [ ] Escape dismisses overlays
- [ ] Focus indicators visible

**Screen Reader (10 minutes):**
- [ ] Content structure makes sense
- [ ] Form fields are labeled
- [ ] Dynamic content announces
- [ ] Error messages are clear

**Visual (5 minutes):**
- [ ] Color contrast passes
- [ ] Works at 200% zoom
- [ ] High contrast mode functional
- [ ] Motion respects preferences

### Comprehensive Release Checklist

**WCAG 2.1 Level AA Compliance:**
- [ ] 1.1.1 Non-text Content
- [ ] 1.3.1 Info and Relationships  
- [ ] 1.3.2 Meaningful Sequence
- [ ] 1.4.3 Contrast (Minimum)
- [ ] 1.4.4 Resize text
- [ ] 2.1.1 Keyboard
- [ ] 2.1.2 No Keyboard Trap
- [ ] 2.4.1 Bypass Blocks
- [ ] 2.4.2 Page Titled
- [ ] 2.4.3 Focus Order
- [ ] 2.4.6 Headings and Labels
- [ ] 2.4.7 Focus Visible
- [ ] 3.1.1 Language of Page
- [ ] 3.2.1 On Focus
- [ ] 3.2.2 On Input
- [ ] 3.3.1 Error Identification
- [ ] 3.3.2 Labels or Instructions
- [ ] 4.1.1 Parsing
- [ ] 4.1.2 Name, Role, Value

## Reporting Template

### Accessibility Test Report

**Component:** [Component Name]
**Date:** [Test Date]
**Tester:** [Tester Name]
**Tools Used:** [List of tools]

#### Summary
- **Overall Status:** Pass/Fail/Needs Review
- **WCAG Level:** A/AA/AAA
- **Critical Issues:** [Number]
- **Non-Critical Issues:** [Number]

#### Detailed Findings

**Issue #1**
- **Severity:** Critical/High/Medium/Low
- **WCAG Criterion:** [Reference]
- **Description:** [What was found]
- **Steps to Reproduce:** [Detailed steps]
- **Expected Behavior:** [What should happen]
- **Actual Behavior:** [What actually happens]
- **Recommendation:** [How to fix]

#### Test Results by Category

**Keyboard Navigation:** Pass/Fail
- Focus management: [Results]
- Tab order: [Results]
- Keyboard shortcuts: [Results]

**Screen Reader:** Pass/Fail
- Content structure: [Results]
- Announcements: [Results]
- Form interaction: [Results]

**Visual Accessibility:** Pass/Fail
- Color contrast: [Results]
- High contrast mode: [Results]
- Zoom functionality: [Results]

**Mobile Accessibility:** Pass/Fail
- Touch targets: [Results]
- Screen reader: [Results]
- Responsive design: [Results]

#### Recommendations
1. [Priority 1 fixes]
2. [Priority 2 improvements]
3. [Future enhancements]

---

## Quick Reference Commands

### Screen Reader Commands

**NVDA:**
- Start/Stop: Insert + Q
- Browse mode: Insert + Space
- Navigate headings: H / Shift + H
- Navigate links: K / Shift + K
- Navigate buttons: B / Shift + B

**VoiceOver:**
- Start/Stop: Cmd + F5
- Navigate: VO + Left/Right Arrow
- Rotor: VO + U
- Web rotor: VO + Cmd + U

### Browser DevTools

**Chrome Accessibility:**
1. DevTools > Elements > Accessibility tab
2. DevTools > Lighthouse > Accessibility audit
3. DevTools > Rendering > Emulate vision deficiencies

**Firefox Accessibility:**
1. DevTools > Accessibility tab
2. about:devtools-toolbox?type=tab&id=[tabId]

This manual testing guide should be used in conjunction with automated testing to ensure comprehensive accessibility coverage for all M0 components.