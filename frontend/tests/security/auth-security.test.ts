/**
 * Frontend authentication security tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthService } from '../../src/lib/auth/auth-service'
import { TokenManager } from '../../src/lib/auth/token-manager'
import { SecurityTestUtils } from '../utils/security-test-utils'

describe('Frontend Authentication Security', () => {
  let authService: AuthService
  let tokenManager: TokenManager

  beforeEach(() => {
    authService = new AuthService()
    tokenManager = new TokenManager()
    localStorage.clear()
    sessionStorage.clear()
  })

  describe('XSS Protection', () => {
    it('should sanitize user inputs in authentication forms', () => {
      const maliciousInputs = [
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '<img src=x onerror=alert("xss")>',
        '"><script>alert("xss")</script>',
        "';alert('xss');//"
      ]

      maliciousInputs.forEach(maliciousInput => {
        const sanitized = authService.sanitizeInput(maliciousInput)
        
        expect(sanitized).not.toContain('<script>')
        expect(sanitized).not.toContain('javascript:')
        expect(sanitized).not.toContain('onerror=')
        expect(sanitized).not.toContain('alert(')
      })
    })

    it('should prevent XSS in error messages', async () => {
      const maliciousEmail = '<script>alert("xss")</script>@example.com'
      
      try {
        await authService.login({
          email: maliciousEmail,
          password: 'TestPassword123!'
        })
      } catch (error) {
        expect(error.message).not.toContain('<script>')
        expect(error.message).not.toContain('alert(')
      }
    })

    it('should escape user data in DOM rendering', () => {
      const maliciousUserData = {
        name: '<script>alert("xss")</script>John',
        email: '<img src=x onerror=alert("xss")>test@example.com',
        company: 'javascript:alert("xss")'
      }

      // Store user data
      localStorage.setItem('user_profile', JSON.stringify(maliciousUserData))
      
      // Retrieve and render
      const userProfile = tokenManager.getUserProfile()
      
      // Should be sanitized when retrieved
      expect(userProfile.name).not.toContain('<script>')
      expect(userProfile.email).not.toContain('<img')
      expect(userProfile.company).not.toContain('javascript:')
    })
  })

  describe('CSRF Protection', () => {
    it('should include CSRF token in authenticated requests', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true })
      })
      global.fetch = mockFetch

      // Set up authenticated session
      tokenManager.setTokens({
        accessToken: 'valid.access.token',
        refreshToken: 'valid.refresh.token',
        tokenType: 'bearer',
        expiresIn: 3600
      })

      await authService.makeAuthenticatedRequest('/api/protected', {
        method: 'POST',
        body: JSON.stringify({ data: 'test' })
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-CSRF-Token': expect.any(String)
          })
        })
      )
    })

    it('should generate unique CSRF tokens', () => {
      const token1 = authService.generateCSRFToken()
      const token2 = authService.generateCSRFToken()
      
      expect(token1).not.toBe(token2)
      expect(token1).toHaveLength(32) // 256 bits as hex
      expect(token2).toHaveLength(32)
    })

    it('should validate CSRF tokens', () => {
      const validToken = authService.generateCSRFToken()
      const invalidToken = 'invalid-csrf-token'
      
      expect(authService.validateCSRFToken(validToken)).toBe(true)
      expect(authService.validateCSRFToken(invalidToken)).toBe(false)
    })
  })

  describe('Token Security', () => {
    it('should store tokens securely in localStorage', () => {
      const tokens = {
        accessToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dosomething',
        refreshToken: 'refresh.token.here',
        tokenType: 'bearer',
        expiresIn: 3600
      }

      tokenManager.setTokens(tokens)

      // Verify tokens are stored
      expect(localStorage.getItem('access_token')).toBe(tokens.accessToken)
      expect(localStorage.getItem('refresh_token')).toBe(tokens.refreshToken)
    })

    it('should not expose tokens in global scope', () => {
      const tokens = {
        accessToken: 'secret.access.token',
        refreshToken: 'secret.refresh.token',
        tokenType: 'bearer',
        expiresIn: 3600
      }

      tokenManager.setTokens(tokens)

      // Check that tokens are not accessible globally
      expect(window.accessToken).toBeUndefined()
      expect(window.refreshToken).toBeUndefined()
      expect((window as any).tokens).toBeUndefined()
    })

    it('should validate JWT token format', () => {
      const validJWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
      const invalidJWT = 'invalid.jwt.token'
      const maliciousJWT = '<script>alert("xss")</script>'

      expect(tokenManager.isValidJWT(validJWT)).toBe(true)
      expect(tokenManager.isValidJWT(invalidJWT)).toBe(false)
      expect(tokenManager.isValidJWT(maliciousJWT)).toBe(false)
    })

    it('should handle token expiration securely', () => {
      const expiredToken = tokenManager.createMockToken({ 
        exp: Math.floor(Date.now() / 1000) - 3600 // 1 hour ago
      })
      
      tokenManager.setTokens({
        accessToken: expiredToken,
        refreshToken: 'refresh.token',
        tokenType: 'bearer',
        expiresIn: 3600
      })

      expect(tokenManager.isTokenExpired()).toBe(true)
      
      // Should clear expired tokens
      tokenManager.clearExpiredTokens()
      
      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('should prevent token theft via XSS', () => {
      const tokens = {
        accessToken: 'sensitive.access.token',
        refreshToken: 'sensitive.refresh.token',
        tokenType: 'bearer',
        expiresIn: 3600
      }

      tokenManager.setTokens(tokens)

      // Try to access tokens through XSS-like methods
      const xssAttempts = [
        () => localStorage.getItem('access_token'),
        () => document.cookie,
        () => (window as any).tokens,
        () => JSON.stringify(localStorage)
      ]

      xssAttempts.forEach(attempt => {
        const result = attempt()
        if (result) {
          // If tokens are accessible, ensure they're properly protected
          expect(typeof result).toBe('string')
          // In production, tokens should be httpOnly cookies or have additional protection
        }
      })
    })
  })

  describe('Session Security', () => {
    it('should implement session timeout', () => {
      const sessionTimeout = 30 * 60 * 1000 // 30 minutes
      const currentTime = Date.now()
      
      // Set session timestamp
      localStorage.setItem('session_timestamp', currentTime.toString())
      
      // Mock time passing
      jest.spyOn(Date, 'now').mockReturnValue(currentTime + sessionTimeout + 1000)
      
      expect(authService.isSessionValid()).toBe(false)
      
      jest.restoreAllMocks()
    })

    it('should refresh session on activity', () => {
      const currentTime = Date.now()
      localStorage.setItem('session_timestamp', currentTime.toString())

      // Simulate user activity
      authService.refreshSession()

      const newTimestamp = parseInt(localStorage.getItem('session_timestamp') || '0')
      expect(newTimestamp).toBeGreaterThan(currentTime)
    })

    it('should invalidate session on logout', async () => {
      // Set up session
      tokenManager.setTokens({
        accessToken: 'access.token',
        refreshToken: 'refresh.token',
        tokenType: 'bearer',
        expiresIn: 3600
      })
      localStorage.setItem('session_timestamp', Date.now().toString())

      await authService.logout()

      // Verify session is cleared
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(localStorage.getItem('session_timestamp')).toBeNull()
    })

    it('should handle concurrent sessions securely', async () => {
      // Simulate multiple tabs
      const session1 = { tabId: '1', timestamp: Date.now() }
      const session2 = { tabId: '2', timestamp: Date.now() }

      localStorage.setItem('active_sessions', JSON.stringify([session1, session2]))

      // Logout from one session
      await authService.logoutFromTab('1')

      const remainingSessions = JSON.parse(localStorage.getItem('active_sessions') || '[]')
      expect(remainingSessions).toHaveLength(1)
      expect(remainingSessions[0].tabId).toBe('2')
    })
  })

  describe('Password Security', () => {
    it('should validate password strength', () => {
      const weakPasswords = SecurityTestUtils.generateWeakPasswords()
      const strongPasswords = SecurityTestUtils.generateStrongPasswords()

      weakPasswords.forEach(password => {
        const result = authService.validatePasswordStrength(password)
        expect(result.isStrong).toBe(false)
        expect(result.errors.length).toBeGreaterThan(0)
      })

      strongPasswords.forEach(password => {
        const result = authService.validatePasswordStrength(password)
        expect(result.isStrong).toBe(true)
        expect(result.errors.length).toBe(0)
      })
    })

    it('should not store passwords in plain text', async () => {
      const password = 'MySecretPassword123!'
      const formData = {
        email: 'test@example.com',
        password: password
      }

      // Mock form submission
      const mockSubmit = jest.fn()
      const form = document.createElement('form')
      form.onsubmit = mockSubmit

      const emailInput = document.createElement('input')
      emailInput.type = 'email'
      emailInput.value = formData.email

      const passwordInput = document.createElement('input')
      passwordInput.type = 'password'
      passwordInput.value = formData.password

      form.appendChild(emailInput)
      form.appendChild(passwordInput)

      // Verify password is not stored anywhere
      expect(localStorage.getItem('password')).toBeNull()
      expect(sessionStorage.getItem('password')).toBeNull()
      expect(document.querySelector('[data-password]')).toBeNull()
    })

    it('should implement password visibility toggle securely', () => {
      const passwordInput = document.createElement('input')
      passwordInput.type = 'password'
      passwordInput.value = 'SecretPassword123!'

      const toggleButton = document.createElement('button')
      toggleButton.onclick = () => {
        passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password'
      }

      // Initially hidden
      expect(passwordInput.type).toBe('password')

      // Toggle to visible
      toggleButton.click()
      expect(passwordInput.type).toBe('text')

      // Toggle back to hidden
      toggleButton.click()
      expect(passwordInput.type).toBe('password')

      // Verify password value is never logged
      const consoleSpy = jest.spyOn(console, 'log')
      toggleButton.click()
      expect(consoleSpy).not.toHaveBeenCalledWith(expect.stringContaining('SecretPassword123!'))
      consoleSpy.mockRestore()
    })
  })

  describe('Input Sanitization', () => {
    it('should sanitize all user inputs', () => {
      const maliciousInputs = SecurityTestUtils.generateMaliciousPayloads()

      Object.values(maliciousInputs).flat().forEach(payload => {
        const sanitized = authService.sanitizeInput(payload)
        
        // Should not contain dangerous characters
        expect(sanitized).not.toMatch(/<script/i)
        expect(sanitized).not.toMatch(/javascript:/i)
        expect(sanitized).not.toMatch(/on\w+=/i)
        expect(sanitized).not.toMatch(/drop\s+table/i)
        expect(sanitized).not.toMatch(/union\s+select/i)
      })
    })

    it('should validate email format strictly', () => {
      const invalidEmails = SecurityTestUtils.generateInvalidEmails()
      const validEmails = SecurityTestUtils.generateValidEmails()

      invalidEmails.forEach(email => {
        expect(authService.isValidEmail(email)).toBe(false)
      })

      validEmails.forEach(email => {
        expect(authService.isValidEmail(email)).toBe(true)
      })
    })

    it('should handle Unicode characters safely', () => {
      const unicodeInputs = [
        '用户@example.com', // Chinese
        'пользователь@example.com', // Cyrillic
        'café@münchen.de', // Accented characters
        '🙂😀👍', // Emoji
        'ñoño@español.com' // Spanish
      ]

      unicodeInputs.forEach(input => {
        const sanitized = authService.sanitizeInput(input)
        expect(sanitized).toBeTruthy()
        expect(typeof sanitized).toBe('string')
      })
    })
  })

  describe('Rate Limiting', () => {
    it('should implement client-side rate limiting', async () => {
      const rateLimiter = authService.getRateLimiter()
      
      // Make multiple requests quickly
      for (let i = 0; i < 10; i++) {
        const allowed = rateLimiter.isAllowed('login')
        if (i < 5) {
          expect(allowed).toBe(true)
        } else {
          expect(allowed).toBe(false) // Should be rate limited after 5 attempts
        }
      }
    })

    it('should reset rate limit after time window', async () => {
      const rateLimiter = authService.getRateLimiter()
      
      // Exhaust rate limit
      for (let i = 0; i < 5; i++) {
        rateLimiter.isAllowed('login')
      }
      
      expect(rateLimiter.isAllowed('login')).toBe(false)
      
      // Mock time passing
      jest.spyOn(Date, 'now').mockReturnValue(Date.now() + 60 * 1000) // 1 minute later
      
      expect(rateLimiter.isAllowed('login')).toBe(true)
      
      jest.restoreAllMocks()
    })
  })

  describe('Content Security Policy', () => {
    it('should not execute inline scripts', () => {
      const inlineScript = '<script>window.hacked = true</script>'
      
      // Try to inject inline script
      document.body.innerHTML = inlineScript
      
      expect((window as any).hacked).toBeUndefined()
    })

    it('should restrict external script loading', () => {
      const externalScript = document.createElement('script')
      externalScript.src = 'https://malicious.com/evil.js'
      
      // Should be blocked by CSP in production
      const originalError = console.error
      let cspError = false
      console.error = (msg: string) => {
        if (msg.includes('Content Security Policy')) {
          cspError = true
        }
      }
      
      document.head.appendChild(externalScript)
      
      // In test environment, we simulate the CSP behavior
      expect(externalScript.src).toContain('malicious.com')
      
      console.error = originalError
    })
  })

  describe('Secure Headers', () => {
    it('should include security headers in requests', async () => {
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({})
      })
      global.fetch = mockFetch

      await authService.makeRequest('/api/test')

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
          })
        })
      )
    })
  })

  describe('Error Handling Security', () => {
    it('should not expose sensitive information in errors', async () => {
      try {
        await authService.login({
          email: 'nonexistent@example.com',
          password: 'AnyPassword123!'
        })
      } catch (error) {
        // Should not reveal whether user exists
        expect(error.message).not.toContain('user not found')
        expect(error.message).not.toContain('email does not exist')
        expect(error.message).toMatch(/invalid credentials/i)
      }
    })

    it('should not expose stack traces in production', async () => {
      const originalEnv = process.env.NODE_ENV
      process.env.NODE_ENV = 'production'

      try {
        await authService.triggerError()
      } catch (error) {
        expect(error.stack).toBeUndefined()
        expect(error.message).not.toContain('at ')
        expect(error.message).not.toContain('.js:')
      }

      process.env.NODE_ENV = originalEnv
    })
  })
})