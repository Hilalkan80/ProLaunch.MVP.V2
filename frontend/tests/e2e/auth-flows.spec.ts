/**
 * End-to-end authentication flow tests
 * These tests validate complete user journeys through the authentication system
 */

import { test, expect, Page } from '@playwright/test'

// Test data
const testUser = {
  email: 'test@example.com',
  password: 'TestPassword123!',
  fullName: 'John Doe',
  companyName: 'Test Company',
  businessIdea: 'A comprehensive authentication testing system that ensures security and usability'
}

const newUser = {
  email: 'newuser@example.com',
  password: 'NewUserPassword123!',
  fullName: 'Jane Smith',
  companyName: 'New User Company',
  businessIdea: 'A revolutionary new business idea that will change the world through innovative technology'
}

test.describe('Authentication Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/')
    
    // Clear any existing authentication state
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
  })

  test.describe('User Registration Flow', () => {
    test('should successfully register a new user', async ({ page }) => {
      // Navigate to registration page
      await page.click('text=Sign Up')
      await expect(page).toHaveURL('/register')

      // Fill registration form
      await page.fill('[data-testid="email-input"]', newUser.email)
      await page.fill('[data-testid="password-input"]', newUser.password)
      await page.fill('[data-testid="full-name-input"]', newUser.fullName)
      await page.fill('[data-testid="company-name-input"]', newUser.companyName)
      await page.fill('[data-testid="business-idea-input"]', newUser.businessIdea)
      
      // Select experience level
      await page.selectOption('[data-testid="experience-level-select"]', 'first-time')

      // Submit registration
      await page.click('[data-testid="register-button"]')

      // Should redirect to dashboard after successful registration
      await expect(page).toHaveURL('/dashboard')
      
      // Should display welcome message
      await expect(page.locator('[data-testid="welcome-message"]')).toContainText('Welcome, Jane')
      
      // Should display user's business idea
      await expect(page.locator('[data-testid="business-idea-display"]')).toContainText(newUser.businessIdea)
    })

    test('should validate required fields', async ({ page }) => {
      await page.goto('/register')

      // Try to submit without filling required fields
      await page.click('[data-testid="register-button"]')

      // Should show validation errors
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Email is required')
      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password is required')
      await expect(page.locator('[data-testid="business-idea-error"]')).toContainText('Business idea is required')
    })

    test('should validate password strength', async ({ page }) => {
      await page.goto('/register')

      await page.fill('[data-testid="email-input"]', newUser.email)
      await page.fill('[data-testid="password-input"]', 'weak')
      await page.fill('[data-testid="business-idea-input"]', newUser.businessIdea)
      
      await page.click('[data-testid="register-button"]')

      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password must be at least 8 characters')
    })

    test('should handle duplicate email registration', async ({ page }) => {
      await page.goto('/register')

      // Try to register with existing email
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', newUser.password)
      await page.fill('[data-testid="business-idea-input"]', newUser.businessIdea)
      
      await page.click('[data-testid="register-button"]')

      await expect(page.locator('[data-testid="error-message"]')).toContainText('Email already registered')
    })
  })

  test.describe('User Login Flow', () => {
    test('should successfully login with valid credentials', async ({ page }) => {
      await page.goto('/login')

      // Fill login form
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      
      // Submit login
      await page.click('[data-testid="login-button"]')

      // Should redirect to dashboard
      await expect(page).toHaveURL('/dashboard')
      
      // Should display user information
      await expect(page.locator('[data-testid="user-profile"]')).toContainText(testUser.email)
      
      // Should have authentication tokens stored
      const accessToken = await page.evaluate(() => localStorage.getItem('access_token'))
      const refreshToken = await page.evaluate(() => localStorage.getItem('refresh_token'))
      
      expect(accessToken).toBeTruthy()
      expect(refreshToken).toBeTruthy()
    })

    test('should fail login with invalid credentials', async ({ page }) => {
      await page.goto('/login')

      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', 'wrongpassword')
      
      await page.click('[data-testid="login-button"]')

      // Should show error message
      await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid credentials')
      
      // Should remain on login page
      await expect(page).toHaveURL('/login')
      
      // Should not have tokens
      const accessToken = await page.evaluate(() => localStorage.getItem('access_token'))
      expect(accessToken).toBeNull()
    })

    test('should handle account lockout after multiple failed attempts', async ({ page }) => {
      await page.goto('/login')

      // Make multiple failed login attempts
      for (let i = 0; i < 5; i++) {
        await page.fill('[data-testid="email-input"]', testUser.email)
        await page.fill('[data-testid="password-input"]', 'wrongpassword')
        await page.click('[data-testid="login-button"]')
        
        if (i < 4) {
          await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid credentials')
        }
      }

      // After 5 attempts, should show account locked message
      await expect(page.locator('[data-testid="error-message"]')).toContainText('Account is locked')
    })

    test('should remember user when "Remember Me" is checked', async ({ page }) => {
      await page.goto('/login')

      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.check('[data-testid="remember-me-checkbox"]')
      
      await page.click('[data-testid="login-button"]')
      
      // Should redirect to dashboard
      await expect(page).toHaveURL('/dashboard')
      
      // Simulate browser restart by reloading page
      await page.reload()
      
      // Should still be authenticated (tokens should persist)
      await expect(page).toHaveURL('/dashboard')
      
      // Check that remember me preference is stored
      const rememberedEmail = await page.evaluate(() => localStorage.getItem('remembered_email'))
      expect(rememberedEmail).toBe(testUser.email)
    })
  })

  test.describe('Password Reset Flow', () => {
    test('should request password reset successfully', async ({ page }) => {
      await page.goto('/login')
      
      // Click forgot password link
      await page.click('[data-testid="forgot-password-link"]')
      await expect(page).toHaveURL('/forgot-password')
      
      // Enter email
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.click('[data-testid="reset-password-button"]')
      
      // Should show success message
      await expect(page.locator('[data-testid="success-message"]')).toContainText('Password reset email sent')
    })

    test('should show success message even for non-existent email', async ({ page }) => {
      await page.goto('/forgot-password')
      
      await page.fill('[data-testid="email-input"]', 'nonexistent@example.com')
      await page.click('[data-testid="reset-password-button"]')
      
      // Should still show success message for security
      await expect(page.locator('[data-testid="success-message"]')).toContainText('Password reset email sent')
    })
  })

  test.describe('User Logout Flow', () => {
    test('should successfully logout user', async ({ page }) => {
      // First login
      await page.goto('/login')
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      await expect(page).toHaveURL('/dashboard')
      
      // Logout
      await page.click('[data-testid="logout-button"]')
      
      // Should redirect to login page
      await expect(page).toHaveURL('/login')
      
      // Should clear authentication tokens
      const accessToken = await page.evaluate(() => localStorage.getItem('access_token'))
      const refreshToken = await page.evaluate(() => localStorage.getItem('refresh_token'))
      
      expect(accessToken).toBeNull()
      expect(refreshToken).toBeNull()
    })

    test('should handle logout from all devices', async ({ page, context }) => {
      // Login in first tab
      await page.goto('/login')
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      // Open second tab and login
      const secondPage = await context.newPage()
      await secondPage.goto('/login')
      await secondPage.fill('[data-testid="email-input"]', testUser.email)
      await secondPage.fill('[data-testid="password-input"]', testUser.password)
      await secondPage.click('[data-testid="login-button"]')
      
      // Both should be on dashboard
      await expect(page).toHaveURL('/dashboard')
      await expect(secondPage).toHaveURL('/dashboard')
      
      // Logout from all devices in first tab
      await page.click('[data-testid="user-menu"]')
      await page.click('[data-testid="logout-all-devices-button"]')
      
      // Both tabs should be logged out
      await expect(page).toHaveURL('/login')
      
      // Second tab should also be redirected when it tries to make a request
      await secondPage.reload()
      await expect(secondPage).toHaveURL('/login')
    })
  })

  test.describe('Authentication State Persistence', () => {
    test('should maintain session across page reloads', async ({ page }) => {
      // Login
      await page.goto('/login')
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      await expect(page).toHaveURL('/dashboard')
      
      // Reload page
      await page.reload()
      
      // Should still be authenticated
      await expect(page).toHaveURL('/dashboard')
      await expect(page.locator('[data-testid="user-profile"]')).toContainText(testUser.email)
    })

    test('should redirect unauthenticated users to login', async ({ page }) => {
      // Try to access protected page without authentication
      await page.goto('/dashboard')
      
      // Should redirect to login
      await expect(page).toHaveURL('/login')
      
      // Should show message about needing to login
      await expect(page.locator('[data-testid="login-required-message"]')).toContainText('Please log in to continue')
    })

    test('should handle expired tokens gracefully', async ({ page }) => {
      // Login first
      await page.goto('/login')
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      await expect(page).toHaveURL('/dashboard')
      
      // Simulate expired token by setting invalid token
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'expired.token.here')
      })
      
      // Try to access protected resource
      await page.click('[data-testid="profile-link"]')
      
      // Should redirect to login due to expired token
      await expect(page).toHaveURL('/login')
      await expect(page.locator('[data-testid="error-message"]')).toContainText('Session expired')
    })
  })

  test.describe('Security Features', () => {
    test('should prevent XSS attacks in input fields', async ({ page }) => {
      await page.goto('/register')

      const maliciousScript = '<script>alert("XSS")</script>'
      
      await page.fill('[data-testid="business-idea-input"]', maliciousScript)
      await page.fill('[data-testid="full-name-input"]', maliciousScript)
      
      // Submit form (assuming other required fields are filled)
      await page.fill('[data-testid="email-input"]', 'xss@example.com')
      await page.fill('[data-testid="password-input"]', 'XSSPassword123!')
      await page.click('[data-testid="register-button"]')
      
      // Check that script is not executed
      const alertDialogs = []
      page.on('dialog', dialog => {
        alertDialogs.push(dialog.message())
        dialog.dismiss()
      })
      
      expect(alertDialogs).toHaveLength(0)
    })

    test('should validate CSRF protection', async ({ page }) => {
      // Login first
      await page.goto('/login')
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      // Check that CSRF token is included in requests
      const csrfToken = await page.evaluate(() => {
        const meta = document.querySelector('meta[name="csrf-token"]')
        return meta ? meta.getAttribute('content') : null
      })
      
      expect(csrfToken).toBeTruthy()
    })

    test('should enforce secure password requirements', async ({ page }) => {
      await page.goto('/register')

      const weakPasswords = [
        'password',
        '123456',
        'qwerty',
        'admin',
        'letmein'
      ]

      for (const weakPassword of weakPasswords) {
        await page.fill('[data-testid="password-input"]', weakPassword)
        await page.blur('[data-testid="password-input"]') // Trigger validation
        
        await expect(page.locator('[data-testid="password-strength-indicator"]')).toContainText('Weak')
      }

      // Test strong password
      await page.fill('[data-testid="password-input"]', 'StrongPassword123!')
      await page.blur('[data-testid="password-input"]')
      
      await expect(page.locator('[data-testid="password-strength-indicator"]')).toContainText('Strong')
    })
  })

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      await page.goto('/login')

      // Navigate through form using Tab key
      await page.keyboard.press('Tab') // Email field
      await expect(page.locator('[data-testid="email-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Password field
      await expect(page.locator('[data-testid="password-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Remember me checkbox
      await expect(page.locator('[data-testid="remember-me-checkbox"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Login button
      await expect(page.locator('[data-testid="login-button"]')).toBeFocused()
    })

    test('should have proper ARIA labels', async ({ page }) => {
      await page.goto('/login')

      // Check ARIA labels
      await expect(page.locator('[data-testid="email-input"]')).toHaveAttribute('aria-label', 'Email address')
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('aria-label', 'Password')
      await expect(page.locator('[data-testid="login-button"]')).toHaveAttribute('aria-label', 'Sign in to your account')
    })

    test('should announce errors to screen readers', async ({ page }) => {
      await page.goto('/login')

      // Submit form without filling fields
      await page.click('[data-testid="login-button"]')

      // Check that error has proper ARIA attributes
      await expect(page.locator('[data-testid="email-error"]')).toHaveAttribute('role', 'alert')
      await expect(page.locator('[data-testid="email-error"]')).toHaveAttribute('aria-live', 'polite')
    })
  })

  test.describe('Performance', () => {
    test('should load login page quickly', async ({ page }) => {
      const startTime = Date.now()
      
      await page.goto('/login')
      await page.waitForSelector('[data-testid="login-form"]')
      
      const loadTime = Date.now() - startTime
      expect(loadTime).toBeLessThan(3000) // Should load in under 3 seconds
    })

    test('should handle form submission efficiently', async ({ page }) => {
      await page.goto('/login')

      const startTime = Date.now()
      
      await page.fill('[data-testid="email-input"]', testUser.email)
      await page.fill('[data-testid="password-input"]', testUser.password)
      await page.click('[data-testid="login-button"]')
      
      await page.waitForURL('/dashboard')
      
      const authTime = Date.now() - startTime
      expect(authTime).toBeLessThan(5000) // Authentication should complete in under 5 seconds
    })
  })
})

test.describe('Mobile Authentication', () => {
  test.use({ 
    viewport: { width: 375, height: 667 } // iPhone SE dimensions
  })

  test('should work correctly on mobile devices', async ({ page }) => {
    await page.goto('/login')

    // Check mobile-responsive design
    const loginForm = page.locator('[data-testid="login-form"]')
    await expect(loginForm).toBeVisible()

    // Fill form on mobile
    await page.fill('[data-testid="email-input"]', testUser.email)
    await page.fill('[data-testid="password-input"]', testUser.password)
    
    // Submit
    await page.click('[data-testid="login-button"]')
    
    // Should work same as desktop
    await expect(page).toHaveURL('/dashboard')
  })

  test('should handle touch interactions', async ({ page }) => {
    await page.goto('/login')

    // Test touch on password visibility toggle
    const passwordToggle = page.locator('[data-testid="password-toggle"]')
    await passwordToggle.tap()

    const passwordInput = page.locator('[data-testid="password-input"]')
    await expect(passwordInput).toHaveAttribute('type', 'text')

    await passwordToggle.tap()
    await expect(passwordInput).toHaveAttribute('type', 'password')
  })
})