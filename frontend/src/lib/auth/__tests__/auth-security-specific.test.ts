/**
 * Specific security tests for AuthService XSS protection
 */

import { AuthService } from '../auth-service'
import { SecurityUtils } from '../../../utils/security'
import { SecurityTestUtils } from '../../../../tests/utils/security-test-utils'

// Mock the API
jest.mock('../auth-api')

describe('AuthService XSS Protection', () => {
  let authService: AuthService

  beforeEach(() => {
    authService = new AuthService()
    localStorage.clear()
  })

  describe('Input Sanitization', () => {
    it('should sanitize XSS payloads in registration data', async () => {
      const xssPayloads = SecurityTestUtils.generateXSSPayloads()
      
      for (const payload of xssPayloads) {
        const registrationData = {
          email: 'test@example.com',
          password: 'StrongPassword123!',
          businessIdea: `${payload}Business idea`,
          fullName: `${payload}John Doe`
        }

        const result = await authService.register(registrationData)
        
        // Verify XSS content is removed
        expect(result.user.businessIdea).toBe('Business idea')
        expect(result.user.fullName).toBe('John Doe')
        expect(result.user.businessIdea).not.toContain('<script>')
        expect(result.user.businessIdea).not.toContain('javascript:')
        expect(result.user.businessIdea).not.toContain('alert')
      }
    })

    it('should handle the specific test case from the failing test', async () => {
      const registrationData = {
        email: 'test@example.com',
        password: 'StrongPassword123!',
        businessIdea: '<script>alert("xss")</script>Business idea',
        fullName: '<img src=x onerror=alert(1)>John Doe'
      }

      const result = await authService.register(registrationData)

      // This is the exact test case that was failing
      expect(result.user.businessIdea).toBe('Business idea')
      expect(result.user.fullName).toBe('John Doe')
    })

    it('should preserve legitimate content while removing XSS', async () => {
      const testCases = [
        {
          input: 'Hello <script>alert("xss")</script> World',
          expected: 'Hello  World'
        },
        {
          input: 'My business idea <img src=x onerror=alert(1)> is great',
          expected: 'My business idea  is great'
        },
        {
          input: 'javascript:alert("xss") Company Name',
          expected: ' Company Name'
        },
        {
          input: 'Normal text without any XSS',
          expected: 'Normal text without any XSS'
        }
      ]

      for (const testCase of testCases) {
        const sanitized = authService.sanitizeInput(testCase.input)
        expect(sanitized.trim()).toBe(testCase.expected.trim())
      }
    })

    it('should sanitize email addresses', async () => {
      const maliciousEmails = [
        '<script>alert("xss")</script>@example.com',
        'javascript:alert("xss")@example.com',
        'test@<script>alert("xss")</script>.com'
      ]

      for (const email of maliciousEmails) {
        const credentials = {
          email,
          password: 'TestPassword123!'
        }

        // Should either sanitize or reject the email
        try {
          await authService.login(credentials)
        } catch (error) {
          // Expected to fail validation
          expect(error.message).toMatch(/invalid.*email.*format/i)
        }
      }
    })
  })

  describe('SecurityUtils Integration', () => {
    it('should use SecurityUtils.sanitizeInput method', () => {
      const xssInput = '<script>alert("xss")</script>Test content'
      const sanitized = authService.sanitizeInput(xssInput)
      
      expect(sanitized).toBe('Test content')
      expect(sanitized).not.toContain('<script>')
      expect(sanitized).not.toContain('alert')
    })

    it('should validate email format using SecurityUtils', () => {
      const validEmails = SecurityTestUtils.generateValidEmails()
      const invalidEmails = SecurityTestUtils.generateInvalidEmails()

      validEmails.forEach(email => {
        expect(SecurityUtils.isValidEmail(email)).toBe(true)
      })

      invalidEmails.forEach(email => {
        expect(SecurityUtils.isValidEmail(email)).toBe(false)
      })
    })
  })

  describe('Comprehensive XSS Attack Scenarios', () => {
    it('should protect against all known XSS attack vectors', async () => {
      const maliciousPayloads = SecurityTestUtils.generateMaliciousPayloads()
      
      for (const xssPayload of maliciousPayloads.xss) {
        const registrationData = {
          email: 'test@example.com',
          password: 'StrongPassword123!',
          businessIdea: `${xssPayload}Legitimate business content`,
          fullName: `${xssPayload}John Doe`,
          companyName: `${xssPayload}Company Inc`
        }

        const result = await authService.register(registrationData)

        // Verify all XSS attempts are neutralized
        expect(SecurityTestUtils.isProperlysanitized(
          registrationData.businessIdea, 
          result.user.businessIdea
        )).toBe(true)
        
        expect(SecurityTestUtils.isProperlysanitized(
          registrationData.fullName, 
          result.user.fullName
        )).toBe(true)
        
        if (result.user.companyName) {
          expect(SecurityTestUtils.isProperlysanitized(
            registrationData.companyName, 
            result.user.companyName
          )).toBe(true)
        }
      }
    })

    it('should handle nested and complex XSS attacks', async () => {
      const complexXSSAttacks = [
        '<div><script>alert("nested")</script></div>',
        '"><script>alert("attribute-break")</script>',
        '<img src="x" onerror="alert(\'event-handler\')">',
        '<svg onload="alert(\'svg-xss\')">',
        'javascript:void(alert("protocol"))',
        '<iframe src="javascript:alert(\'iframe\')"></iframe>',
        '<object data="javascript:alert(\'object\')"></object>'
      ]

      for (const attack of complexXSSAttacks) {
        const registrationData = {
          email: 'test@example.com',
          password: 'StrongPassword123!',
          businessIdea: `${attack}Business content`
        }

        const result = await authService.register(registrationData)
        
        // Should contain only the legitimate content
        expect(result.user.businessIdea).toBe('Business content')
        expect(result.user.businessIdea).not.toMatch(/<[^>]*>/g)
        expect(result.user.businessIdea).not.toMatch(/javascript:/gi)
        expect(result.user.businessIdea).not.toMatch(/alert/gi)
      }
    })
  })

  describe('Edge Cases and Boundary Testing', () => {
    it('should handle empty and null inputs gracefully', async () => {
      const edgeCases = [
        { businessIdea: '', expected: '' },
        { businessIdea: null, expected: undefined },
        { businessIdea: undefined, expected: undefined },
        { businessIdea: '   ', expected: '' },
        { businessIdea: '<script></script>', expected: '' }
      ]

      for (const testCase of edgeCases) {
        const registrationData = {
          email: 'test@example.com',
          password: 'StrongPassword123!',
          businessIdea: testCase.businessIdea
        }

        const result = await authService.register(registrationData)
        
        if (testCase.expected === undefined) {
          expect(result.user.businessIdea).toBeUndefined()
        } else {
          expect(result.user.businessIdea).toBe(testCase.expected)
        }
      }
    })

    it('should handle very long XSS payloads', async () => {
      const longXSSPayload = '<script>alert("xss")</script>'.repeat(100)
      const registrationData = {
        email: 'test@example.com',
        password: 'StrongPassword123!',
        businessIdea: `${longXSSPayload}Legitimate content`
      }

      const result = await authService.register(registrationData)
      
      expect(result.user.businessIdea).toBe('Legitimate content')
      expect(result.user.businessIdea).not.toContain('<script>')
    })

    it('should handle Unicode and international characters safely', async () => {
      const unicodeTests = [
        'Café <script>alert("xss")</script> Business',
        '北京 <script>alert("xss")</script> 公司',
        'مقهى <script>alert("xss")</script> الأعمال',
        '🚀 <script>alert("xss")</script> Startup'
      ]

      for (const test of unicodeTests) {
        const sanitized = authService.sanitizeInput(test)
        expect(sanitized).not.toContain('<script>')
        expect(sanitized).not.toContain('alert')
        expect(sanitized.length).toBeGreaterThan(0) // Should preserve legitimate content
      }
    })
  })

  describe('Performance and Security Under Load', () => {
    it('should maintain security even with multiple rapid sanitization calls', async () => {
      const xssPayload = '<script>alert("xss")</script>Test'
      const promises = []

      // Simulate rapid concurrent sanitization requests
      for (let i = 0; i < 100; i++) {
        promises.push(
          authService.register({
            email: `test${i}@example.com`,
            password: 'StrongPassword123!',
            businessIdea: `${xssPayload}${i}`
          })
        )
      }

      const results = await Promise.all(promises)
      
      // Verify all results are properly sanitized
      results.forEach((result, index) => {
        expect(result.user.businessIdea).toBe(`Test${index}`)
        expect(result.user.businessIdea).not.toContain('<script>')
        expect(result.user.businessIdea).not.toContain('alert')
      })
    })
  })
})