/**
 * Comprehensive security test suite
 * Tests all security implementations against common vulnerabilities
 */
import { SecurityUtils } from '../../../utils/security'
import { RateLimiter } from '../rate-limiter'
import { SecureHttpClient } from '../secure-http-client'
import { FormSecurity } from '../form-security'
import { TokenManager } from '../../auth/token-manager'
import { AuthService } from '../../auth/auth-service'

// Mock fetch for testing
global.fetch = jest.fn()

describe('Security Comprehensive Test Suite', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
  })

  describe('XSS Protection Tests', () => {
    const xssPayloads = [
      '<script>alert("XSS")</script>',
      'javascript:alert("XSS")',
      '<img src=x onerror=alert("XSS")>',
      '<svg onload=alert("XSS")>',
      '<iframe src="javascript:alert(XSS)"></iframe>'
    ]

    test.each(xssPayloads)('should detect XSS in payload: %s', (payload) => {
      const result = SecurityUtils.detectAdvancedXSS(payload)
      expect(result.isXSS).toBe(true)
      expect(result.patterns.length).toBeGreaterThan(0)
    })

    test.each(xssPayloads)('should sanitize XSS payload: %s', (payload) => {
      const sanitized = SecurityUtils.sanitizeInput(payload)
      expect(sanitized).not.toContain('<script')
      expect(sanitized).not.toContain('javascript:')
      
      const recheck = SecurityUtils.detectAdvancedXSS(sanitized)
      expect(recheck.isXSS).toBe(false)
    })

    test('should preserve safe content during sanitization', () => {
      const safeInputs = [
        'Hello World',
        'user@example.com',
        '123-456-7890',
        'Safe content with numbers 123 and symbols !@#'
      ]

      safeInputs.forEach(input => {
        const sanitized = SecurityUtils.sanitizeInput(input)
        expect(sanitized.length).toBeGreaterThan(0)
        expect(SecurityUtils.detectAdvancedXSS(sanitized).isXSS).toBe(false)
      })
    })
  })

  describe('SQL Injection Protection Tests', () => {
    const sqlPayloads = [
      "' OR '1'='1",
      "'; DROP TABLE users; --",
      "' UNION SELECT * FROM users --",
      "admin'--"
    ]

    test.each(sqlPayloads)('should detect SQL injection in payload: %s', (payload) => {
      const result = SecurityUtils.containsSQLInjection(payload)
      expect(result).toBe(true)
    })

    test.each(sqlPayloads)('should sanitize SQL injection payload: %s', (payload) => {
      const sanitized = SecurityUtils.sanitizeSQLInput(payload)
      expect(sanitized).not.toContain("'")
      expect(sanitized).not.toContain(';')
      expect(SecurityUtils.containsSQLInjection(sanitized)).toBe(false)
    })
  })

  describe('Token Security Tests', () => {
    let tokenManager: TokenManager

    beforeEach(() => {
      tokenManager = new TokenManager()
    })

    test('should encrypt and decrypt tokens correctly', () => {
      const testTokens = {
        accessToken: 'test_access_token',
        refreshToken: 'test_refresh_token',
        expiresIn: 3600
      }

      tokenManager.setTokens(testTokens)
      const retrieved = tokenManager.getTokens()

      expect(retrieved.accessToken).toBe(testTokens.accessToken)
      expect(retrieved.refreshToken).toBe(testTokens.refreshToken)
    })

    test('should handle token expiration correctly', () => {
      const expiredToken = tokenManager.createMockToken({
        exp: Math.floor(Date.now() / 1000) - 3600 // Expired 1 hour ago
      })

      expect(tokenManager.isTokenExpired(expiredToken)).toBe(true)

      const validToken = tokenManager.createMockToken({
        exp: Math.floor(Date.now() / 1000) + 3600 // Expires in 1 hour
      })

      expect(tokenManager.isTokenExpired(validToken)).toBe(false)
    })

    test('should clear tokens securely', () => {
      const testTokens = {
        accessToken: 'test_access_token',
        refreshToken: 'test_refresh_token'
      }

      tokenManager.setTokens(testTokens)
      tokenManager.clearTokens()

      const retrieved = tokenManager.getTokens()
      expect(retrieved.accessToken).toBeNull()
      expect(retrieved.refreshToken).toBeNull()
    })
  })

  describe('Rate Limiting Tests', () => {
    let rateLimiter: RateLimiter

    beforeEach(() => {
      rateLimiter = new RateLimiter()
    })

    test('should allow requests within rate limit', () => {
      const config = { maxRequests: 5, windowMs: 60000 }
      const endpoint = 'test-endpoint'

      for (let i = 0; i < 5; i++) {
        const result = rateLimiter.isAllowed(endpoint, config)
        expect(result.allowed).toBe(true)
      }
    })

    test('should block requests exceeding rate limit', () => {
      const config = { maxRequests: 3, windowMs: 60000 }
      const endpoint = 'test-endpoint'

      // Use up the rate limit
      for (let i = 0; i < 3; i++) {
        rateLimiter.isAllowed(endpoint, config)
      }

      // Next request should be blocked
      const result = rateLimiter.isAllowed(endpoint, config)
      expect(result.allowed).toBe(false)
      expect(result.retryAfter).toBeGreaterThan(0)
    })
  })

  describe('Form Security Tests', () => {
    let formSecurity: FormSecurity

    beforeEach(() => {
      formSecurity = new FormSecurity()
    })

    test('should generate and validate CSRF tokens', () => {
      const token = formSecurity.generateCSRFToken()
      
      expect(token).toBeTruthy()
      expect(token.length).toBe(32)
      expect(/^[A-Za-z0-9]+$/.test(token)).toBe(true)
      
      expect(formSecurity.validateCSRFToken(token)).toBe(true)
      expect(formSecurity.validateCSRFToken('invalid')).toBe(false)
      expect(formSecurity.validateCSRFToken('')).toBe(false)
    })

    test('should create proper field configurations', () => {
      const configs = FormSecurity.createFieldConfigs()
      
      expect(configs.email).toBeDefined()
      expect(configs.password).toBeDefined()
      expect(configs.name).toBeDefined()
    })
  })

  describe('Password Validation Tests', () => {
    test('should validate password strength', () => {
      const passwords = [
        { password: '123456', shouldPass: false },
        { password: 'password', shouldPass: false },
        { password: 'Pass123!', shouldPass: true },
        { password: 'VeryStrongP@ssw0rd123', shouldPass: true },
        { password: 'weak', shouldPass: false }
      ]

      passwords.forEach(({ password, shouldPass }) => {
        const result = SecurityUtils.validatePassword(password)
        expect(result.isValid).toBe(shouldPass)
        expect(result.score).toBeGreaterThanOrEqual(0)
        expect(result.score).toBeLessThanOrEqual(10)
      })
    })
  })

  describe('URL Validation Tests', () => {
    test('should validate and sanitize URLs', () => {
      const validUrls = [
        'https://example.com',
        'http://localhost:3000'
      ]

      const invalidUrls = [
        'javascript:alert("xss")',
        'data:text/html,<script>alert(XSS)</script>',
        'ftp://malicious.com'
      ]

      validUrls.forEach(url => {
        const result = SecurityUtils.sanitizeURL(url)
        expect(result).toBeTruthy()
        expect(result).toBe(url)
      })

      invalidUrls.forEach(url => {
        const result = SecurityUtils.sanitizeURL(url)
        expect(result).toBeNull()
      })
    })
  })
})