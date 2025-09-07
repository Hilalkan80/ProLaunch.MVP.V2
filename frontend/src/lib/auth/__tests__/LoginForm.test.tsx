import React from 'react'
import { screen, fireEvent, waitFor, within } from '@testing-library/react'
import { render } from '../../components/auth/__tests__/setup'
import { LoginForm } from '../../components/auth/LoginForm'

// Mock the auth service
jest.mock('../../lib/auth/auth-service')

describe('LoginForm', () => {
  const defaultProps = {
    onSuccess: jest.fn(),
    onError: jest.fn(),
    redirectTo: '/dashboard'
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('rendering', () => {
    it('should render login form with all required fields', () => {
      render(<LoginForm {...defaultProps} />)

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/password input/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    })

    it('should render remember me checkbox', () => {
      render(<LoginForm {...defaultProps} />)

      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
    })

    it('should render forgot password link', () => {
      render(<LoginForm {...defaultProps} />)

      expect(screen.getByText(/forgot password/i)).toBeInTheDocument()
    })

    it('should render sign up link', () => {
      render(<LoginForm {...defaultProps} />)

      expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
      expect(screen.getByText(/sign up/i)).toBeInTheDocument()
    })
  })

  describe('form validation', () => {
    it('should show validation error for empty email', async () => {
      render(<LoginForm {...defaultProps} />)

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })
    })

    it('should show validation error for invalid email format', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      })

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/invalid email format/i)).toBeInTheDocument()
      })
    })

    it('should show validation error for empty password', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      })

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('should not show validation errors for valid input', () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'ValidPassword123!' } })

      expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/password is required/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/invalid email format/i)).not.toBeInTheDocument()
    })
  })

  describe('form submission', () => {
    it('should submit form with valid credentials', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(defaultProps.onSuccess).toHaveBeenCalled()
      })
    })

    it('should show loading state during submission', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/signing in/i)).toBeInTheDocument()
        expect(submitButton).toBeDisabled()
      })
    })

    it('should handle login failure', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'WrongPassword' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
      })
      expect(defaultProps.onError).toHaveBeenCalled()
    })

    it('should handle account lockout', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'locked@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'AnyPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/account is locked/i)).toBeInTheDocument()
      })
    })

    it('should handle rate limiting', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'ratelimited@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'AnyPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/too many requests/i)).toBeInTheDocument()
      })
    })
  })

  describe('accessibility', () => {
    it('should have proper form labels', () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)

      expect(emailInput).toHaveAttribute('type', 'email')
      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(emailInput).toBeRequired()
      expect(passwordInput).toBeRequired()
    })

    it('should have proper ARIA attributes', () => {
      render(<LoginForm {...defaultProps} />)

      const form = screen.getByRole('form')
      expect(form).toHaveAttribute('aria-label', 'Login form')

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      expect(submitButton).toHaveAttribute('type', 'submit')
    })

    it('should announce errors to screen readers', async () => {
      render(<LoginForm {...defaultProps} />)

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        const errorMessage = screen.getByText(/email is required/i)
        expect(errorMessage).toHaveAttribute('role', 'alert')
      })
    })

    it('should support keyboard navigation', () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const rememberMeCheckbox = screen.getByLabelText(/remember me/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // Test tab order
      emailInput.focus()
      expect(emailInput).toHaveFocus()

      fireEvent.keyDown(emailInput, { key: 'Tab' })
      expect(passwordInput).toHaveFocus()

      fireEvent.keyDown(passwordInput, { key: 'Tab' })
      expect(rememberMeCheckbox).toHaveFocus()

      fireEvent.keyDown(rememberMeCheckbox, { key: 'Tab' })
      expect(submitButton).toHaveFocus()
    })
  })

  describe('security', () => {
    it('should not log sensitive data', async () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation()
      render(<LoginForm {...defaultProps} />)

      const passwordInput = screen.getByLabelText(/password input/i)
      fireEvent.change(passwordInput, { target: { value: 'SecretPassword123!' } })

      expect(consoleSpy).not.toHaveBeenCalledWith(
        expect.stringContaining('SecretPassword123!')
      )

      consoleSpy.mockRestore()
    })

    it('should have autocomplete attributes', () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)

      expect(emailInput).toHaveAttribute('autoComplete', 'email')
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
    })

    it('should prevent form submission on Enter in disabled state', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      // Start submission to get loading state
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      // Try to submit again with Enter key
      await waitFor(() => {
        fireEvent.keyPress(passwordInput, { key: 'Enter', code: 13 })
      })

      // Should not call onSuccess twice
      await waitFor(() => {
        expect(defaultProps.onSuccess).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('user experience', () => {
    it('should focus first invalid field on submission', async () => {
      render(<LoginForm {...defaultProps} />)

      const passwordInput = screen.getByLabelText(/password input/i)
      await waitFor(() => {
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        const emailInput = screen.getByLabelText(/email/i)
        expect(emailInput).toHaveFocus()
      })
    })

    it('should clear error messages when user starts typing', async () => {
      render(<LoginForm {...defaultProps} />)

      // First submit to get error
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })

      // Start typing in email field
      const emailInput = screen.getByLabelText(/email/i)
      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test' } })
      })

      // Error should be cleared
      expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument()
    })

    it('should show password visibility toggle', () => {
      render(<LoginForm {...defaultProps} />)

      const passwordToggle = screen.getByLabelText(/show password/i)
      expect(passwordToggle).toBeInTheDocument()
    })

    it('should toggle password visibility', async () => {
      render(<LoginForm {...defaultProps} />)

      const passwordInput = screen.getByLabelText(/password input/i)
      const passwordToggle = screen.getByLabelText(/show password/i)

      expect(passwordInput).toHaveAttribute('type', 'password')

      await waitFor(() => {
        fireEvent.click(passwordToggle)
      })

      expect(passwordInput).toHaveAttribute('type', 'text')
      expect(screen.getByLabelText(/hide password/i)).toBeInTheDocument()

      await waitFor(() => {
        fireEvent.click(passwordToggle)
      })

      expect(passwordInput).toHaveAttribute('type', 'password')
    })

    it('should remember form data when remember me is checked', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const rememberMeCheckbox = screen.getByLabelText(/remember me/i)

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.click(rememberMeCheckbox)
      })

      const localStorage = window.localStorage
      expect(localStorage.getItem('remembered_email')).toBe('test@example.com')
    })
  })

  describe('error handling', () => {
    it('should display network error message', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'network@error.com' } })
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/network error/i)).toBeInTheDocument()
      })
    })

    it('should allow retry after error', async () => {
      render(<LoginForm {...defaultProps} />)

      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password input/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      // First attempt fails
      await waitFor(() => {
        fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
        fireEvent.change(passwordInput, { target: { value: 'WrongPassword' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
      })

      // Clear password and try again
      await waitFor(() => {
        fireEvent.change(passwordInput, { target: { value: 'TestPassword123!' } })
      })

      await waitFor(() => {
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(defaultProps.onSuccess).toHaveBeenCalled()
      })
    })
  })
})