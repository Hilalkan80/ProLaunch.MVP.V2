# ProLaunch Authentication Components

This project contains a comprehensive set of authentication UI components built with Next.js, TypeScript, and modern React best practices. The components follow the ProLaunch design system and are fully accessible.

## Features

### 🔐 Authentication Forms
- **Sign In Form** - Email/password authentication with remember me option
- **Sign Up Form** - User registration with password strength indicator
- **Forgot Password Form** - Password reset with email confirmation flow

### ✅ Form Validation
- **Zod Schema Validation** - Comprehensive validation with detailed error messages
- **Password Requirements** - Minimum 8 characters, uppercase, lowercase, number, special character
- **Email Validation** - RFC-compliant email format validation
- **Real-time Feedback** - Validation on blur with immediate error display

### 🎨 Design System Integration
- **CSS Custom Properties** - Full integration with ProLaunch design tokens
- **Responsive Design** - Mobile-first approach with breakpoint-based layouts
- **Dark Mode Support** - Automatic theme switching with system preference detection
- **Consistent Typography** - Inter font family with fluid responsive scales

### ♿ Accessibility Features
- **WCAG 2.1 AA Compliant** - Meets accessibility standards
- **Keyboard Navigation** - Full keyboard support with visible focus indicators
- **Screen Reader Support** - Semantic markup with ARIA attributes
- **Error Announcements** - Live regions for dynamic content updates
- **Touch Targets** - Minimum 44px touch targets for mobile devices

### 🔧 Technical Features
- **TypeScript** - Full type safety with comprehensive interfaces
- **React Hook Form** - Efficient form handling with minimal re-renders
- **Error Boundaries** - Graceful error handling and user feedback
- **Loading States** - Visual feedback during form submission
- **Password Visibility** - Toggle password visibility with accessibility support

## Quick Start

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

### Usage Examples

#### Sign In Form

```tsx
import { SignInForm } from '@/components/auth';

function SignInPage() {
  const handleSignIn = async (data) => {
    try {
      const response = await authApi.signIn(data);
      // Handle success
    } catch (error) {
      // Handle error
    }
  };

  return (
    <SignInForm
      onSubmit={handleSignIn}
      isLoading={isLoading}
      error={error}
    />
  );
}
```

#### Sign Up Form

```tsx
import { SignUpForm } from '@/components/auth';

function SignUpPage() {
  const handleSignUp = async (data) => {
    try {
      const response = await authApi.signUp(data);
      // Handle success
    } catch (error) {
      // Handle error
    }
  };

  return (
    <SignUpForm
      onSubmit={handleSignUp}
      isLoading={isLoading}
      error={error}
    />
  );
}
```

#### Forgot Password Form

```tsx
import { ForgotPasswordForm } from '@/components/auth';

function ForgotPasswordPage() {
  const handleForgotPassword = async (data) => {
    try {
      const response = await authApi.forgotPassword(data.email);
      // Handle success
    } catch (error) {
      // Handle error
    }
  };

  return (
    <ForgotPasswordForm
      onSubmit={handleForgotPassword}
      isLoading={isLoading}
      error={error}
      success={emailSent}
    />
  );
}
```

## Component API

### SignInForm Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `onSubmit` | `(data: SignInFormData) => Promise<void>` | ✅ | Form submission handler |
| `isLoading` | `boolean` | ❌ | Loading state indicator |
| `error` | `string` | ❌ | Error message to display |
| `className` | `string` | ❌ | Additional CSS classes |

### SignUpForm Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `onSubmit` | `(data: SignUpFormData) => Promise<void>` | ✅ | Form submission handler |
| `isLoading` | `boolean` | ❌ | Loading state indicator |
| `error` | `string` | ❌ | Error message to display |
| `className` | `string` | ❌ | Additional CSS classes |

### ForgotPasswordForm Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `onSubmit` | `(data: ForgotPasswordFormData) => Promise<void>` | ✅ | Form submission handler |
| `isLoading` | `boolean` | ❌ | Loading state indicator |
| `error` | `string` | ❌ | Error message to display |
| `success` | `boolean` | ❌ | Success state for email sent confirmation |
| `className` | `string` | ❌ | Additional CSS classes |

## Form Validation Schemas

### Password Requirements

The password validation includes:
- Minimum 8 characters
- Maximum 128 characters  
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

### Email Validation

- RFC-compliant email format
- Maximum 254 characters
- Required field validation

## Shared UI Components

### Button Component

```tsx
import { Button } from '@/components/ui';

<Button 
  variant="primary" // 'primary' | 'secondary' | 'ghost' | 'danger'
  size="base" // 'sm' | 'base' | 'lg'
  isLoading={false}
  isDisabled={false}
  leftIcon={<Icon />}
  rightIcon={<Icon />}
>
  Button Text
</Button>
```

### Input Component

```tsx
import { Input } from '@/components/ui';

<Input
  label="Email address"
  type="email"
  placeholder="Enter your email"
  isRequired={true}
  isInvalid={hasError}
  error="Error message"
  helpText="Helper text"
  leftIcon={<Icon />}
  rightIcon={<Icon />}
/>
```

### Alert Component

```tsx
import { Alert } from '@/components/ui';

<Alert 
  variant="error" // 'success' | 'error' | 'warning' | 'info'
  title="Alert Title"
>
  Alert message content
</Alert>
```

## Validation Packages Used

- **zod** (^3.22.4) - Schema validation with TypeScript inference
- **react-hook-form** (^7.47.0) - Efficient form handling
- **@hookform/resolvers** (^3.3.2) - Zod integration for react-hook-form

## Accessibility Features Implemented

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Logical tab order throughout forms
- Visible focus indicators with high contrast
- Skip links for screen readers

### Screen Reader Support
- Semantic HTML structure with proper headings
- Form labels associated with inputs using `htmlFor`
- Error messages announced via `aria-live` regions
- Loading states announced to screen readers
- Form validation errors linked to inputs via `aria-describedby`

### Visual Accessibility
- WCAG 2.1 AA color contrast ratios (4.5:1 minimum)
- Focus indicators with 2px outlines and proper color contrast
- Text scales properly up to 200% zoom
- Touch targets meet minimum 44px size requirement

### Error Handling
- Clear, descriptive error messages
- Errors announced immediately via `aria-live="polite"`
- Visual error indicators with color and iconography
- Form submission disabled until all errors are resolved

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## File Structure

```
frontend/src/
├── components/
│   ├── auth/                    # Authentication components
│   │   ├── SignInForm.tsx
│   │   ├── SignUpForm.tsx
│   │   ├── ForgotPasswordForm.tsx
│   │   └── index.ts
│   └── ui/                      # Shared UI components
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Alert.tsx
│       └── index.ts
├── lib/
│   └── validation/              # Validation schemas
│       └── auth-schemas.ts
├── pages/                       # Next.js pages
│   ├── auth/
│   │   ├── signin.tsx
│   │   ├── signup.tsx
│   │   └── forgot-password.tsx
│   ├── _app.tsx
│   ├── _document.tsx
│   └── index.tsx
├── styles/
│   └── globals.css              # Global styles with design system
└── types/
    └── auth.ts                  # TypeScript type definitions
```

## Development

### Running the Development Server

```bash
npm run dev
```

### Building for Production

```bash
npm run build
npm start
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

## Demo Pages

Visit these pages to see the components in action:

- **/** - Component showcase and navigation
- **/auth/signin** - Sign in form demonstration
- **/auth/signup** - Sign up form demonstration  
- **/auth/forgot-password** - Forgot password form demonstration

Each demo page includes test scenarios and instructions for exploring different validation states and error conditions.

## Testing

This project uses a comprehensive testing strategy with Jest for unit, integration, and security tests, plus Playwright for end-to-end testing.

### Test Types and Commands

#### Unit Tests
- **Purpose**: Test individual components and functions in isolation
- **Command**: `npm run test:unit`
- **Location**: `src/**/*.test.{ts,tsx}`
- **Environment**: jsdom with standard setup

#### Security Tests
- **Purpose**: Test for security vulnerabilities and validate secure coding practices
- **Command**: `npm run test:security`
- **Location**: `tests/security/**/*.test.{ts,tsx}`
- **Environment**: jsdom with security-focused mocks and utilities
- **Coverage Threshold**: 80% (branches, functions, lines, statements)

#### Integration Tests
- **Purpose**: Test component interactions and API integrations
- **Command**: `npm run test:integration`
- **Location**: `tests/integration/**/*.test.{ts,tsx}`
- **Environment**: jsdom with extended timeout (15s) and mock server utilities

#### Utility Tests
- **Purpose**: Test utility functions and helpers
- **Command**: `npm run test:utils`
- **Location**: `tests/utils/**/*.test.{ts,tsx}`
- **Environment**: Node.js for pure function testing

#### End-to-End Tests
- **Purpose**: Test complete user workflows across the application
- **Command**: `npm run test:e2e`
- **Location**: `tests/e2e/**/*.spec.ts`
- **Tool**: Playwright with multi-browser support

### Running Tests

```bash
# Run all Jest tests (unit, security, integration, utils)
npm run test:jest:all

# Run individual test suites
npm run test:unit
npm run test:security
npm run test:integration
npm run test:utils
npm run test:e2e

# Run with coverage
npm run test:coverage
npm run test:coverage:security
npm run test:coverage:integration

# Watch mode for development
npm run test:watch
npm run test:watch:security
npm run test:watch:integration

# E2E test variations
npm run test:e2e:ui        # With UI
npm run test:e2e:headed    # With browser head
npm run test:e2e:debug     # Debug mode
```

### Coverage Requirements

- **Global Coverage**: 70% minimum (branches, functions, lines, statements)
- **Authentication Code**: 85% minimum (`src/lib/auth/**`)
- **Security Tests**: 80% minimum (`tests/security/**`)

### Test Utilities

#### Security Testing
- `global.securityTestUtils.expectNoXSSVulnerability()`
- `global.securityTestUtils.expectSafeHTMLOutput()`
- `global.securityTestUtils.expectCSRFProtection()`
- `global.securityTestUtils.expectSecureHeaders()`

#### Integration Testing
- `global.integrationTestUtils.setupMockServer()`
- `global.integrationTestUtils.expectApiCall()`
- `global.integrationTestUtils.expectValidResponse()`
- `global.componentTestUtils.expectComponentRenders()`

## Contributing

When contributing to these components:

1. **Follow the Design System** - Use CSS custom properties for all styling
2. **Maintain Accessibility** - Test with keyboard navigation and screen readers
3. **Add Type Safety** - Include proper TypeScript interfaces
4. **Test Validation** - Verify all form validation scenarios
5. **Update Documentation** - Keep this README current with changes

## Support

For questions or issues with these authentication components, please refer to the project documentation or create an issue in the project repository.