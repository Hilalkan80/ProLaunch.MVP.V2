/**
 * Comprehensive form security and validation system
 * Protects against XSS, CSRF, and input injection attacks
 */
import { SecurityUtils } from '../../utils/security'

export interface ValidationRule {
  name: string
  validator: (value: any) => boolean | Promise<boolean>
  message: string
  severity: 'error' | 'warning' | 'info'
}

export interface FieldConfig {
  required?: boolean
  minLength?: number
  maxLength?: number
  pattern?: RegExp
  sanitize?: boolean
  allowHTML?: boolean
  customValidation?: ValidationRule[]
  contextualEncoding?: 'html' | 'attribute' | 'javascript' | 'css' | 'url'
}

export interface ValidationResult {
  isValid: boolean
  errors: Array<{
    field: string
    message: string
    severity: 'error' | 'warning' | 'info'
  }>
  sanitizedData: Record<string, any>
  warnings: string[]
}

export class FormSecurity {
  private readonly commonXSSVectors = [
    '<script',
    'javascript:',
    'onload=',
    'onerror=',
    'onclick=',
    'data:text/html',
    'vbscript:',
    '<iframe',
    '<object',
    '<embed'
  ]

  /**
   * Comprehensive form validation and sanitization
   */
  async validateAndSanitizeForm(
    formData: Record<string, any>,
    fieldConfigs: Record<string, FieldConfig> = {}
  ): Promise<ValidationResult> {
    const errors: Array<{ field: string; message: string; severity: 'error' | 'warning' | 'info' }> = []
    const warnings: string[] = []
    const sanitizedData: Record<string, any> = {}

    for (const [fieldName, value] of Object.entries(formData)) {
      const config = fieldConfigs[fieldName] || {}
      const fieldResult = await this.validateAndSanitizeField(fieldName, value, config)

      errors.push(...fieldResult.errors)
      warnings.push(...fieldResult.warnings)
      sanitizedData[fieldName] = fieldResult.sanitizedValue
    }

    return {
      isValid: errors.filter(e => e.severity === 'error').length === 0,
      errors,
      sanitizedData,
      warnings
    }
  }

  /**
   * Validate and sanitize individual field
   */
  private async validateAndSanitizeField(
    fieldName: string,
    value: any,
    config: FieldConfig
  ): Promise<{
    sanitizedValue: any
    errors: Array<{ field: string; message: string; severity: 'error' | 'warning' | 'info' }>
    warnings: string[]
  }> {
    const errors: Array<{ field: string; message: string; severity: 'error' | 'warning' | 'info' }> = []
    const warnings: string[] = []
    let sanitizedValue = value

    // Handle null/undefined values
    if (value === null || value === undefined) {
      if (config.required) {
        errors.push({
          field: fieldName,
          message: `${fieldName} is required`,
          severity: 'error'
        })
      }
      return { sanitizedValue: '', errors, warnings }
    }

    // Convert to string for validation
    const stringValue = String(value)

    // Required field validation
    if (config.required && (!stringValue || stringValue.trim() === '')) {
      errors.push({
        field: fieldName,
        message: `${fieldName} is required`,
        severity: 'error'
      })
      return { sanitizedValue: '', errors, warnings }
    }

    // Length validation
    if (config.minLength && stringValue.length < config.minLength) {
      errors.push({
        field: fieldName,
        message: `${fieldName} must be at least ${config.minLength} characters long`,
        severity: 'error'
      })
    }

    if (config.maxLength && stringValue.length > config.maxLength) {
      errors.push({
        field: fieldName,
        message: `${fieldName} must be no more than ${config.maxLength} characters long`,
        severity: 'error'
      })
      // Truncate if too long
      sanitizedValue = stringValue.substring(0, config.maxLength)
    }

    // Pattern validation
    if (config.pattern && !config.pattern.test(stringValue)) {
      errors.push({
        field: fieldName,
        message: `${fieldName} format is invalid`,
        severity: 'error'
      })
    }

    // XSS Detection
    const xssResult = SecurityUtils.detectAdvancedXSS(stringValue)
    if (xssResult.isXSS) {
      errors.push({
        field: fieldName,
        message: `${fieldName} contains potentially malicious content`,
        severity: 'error'
      })
      warnings.push(`XSS patterns detected in ${fieldName}: ${xssResult.patterns.join(', ')}`)
    }

    // SQL Injection Detection
    if (SecurityUtils.containsSQLInjection(stringValue)) {
      errors.push({
        field: fieldName,
        message: `${fieldName} contains potentially harmful SQL patterns`,
        severity: 'error'
      })
      warnings.push(`SQL injection patterns detected in ${fieldName}`)
    }

    // Sanitization
    if (config.sanitize !== false) {
      if (config.allowHTML) {
        // Allow safe HTML tags only
        sanitizedValue = this.sanitizeHTML(stringValue)
      } else {
        // Full sanitization
        sanitizedValue = SecurityUtils.sanitizeInput(stringValue)
      }

      // Apply contextual encoding
      if (config.contextualEncoding) {
        sanitizedValue = SecurityUtils.contextualEncode(sanitizedValue, config.contextualEncoding)
      }
    }

    // Custom validation rules
    if (config.customValidation) {
      for (const rule of config.customValidation) {
        const isValid = await rule.validator(sanitizedValue)
        if (!isValid) {
          errors.push({
            field: fieldName,
            message: rule.message,
            severity: rule.severity
          })
        }
      }
    }

    return { sanitizedValue, errors, warnings }
  }

  /**
   * Sanitize HTML while preserving safe tags
   */
  private sanitizeHTML(input: string): string {
    const safeTags = ['p', 'br', 'strong', 'em', 'u', 'b', 'i']
    const safeAttributes = ['class', 'id']
    
    // Simple HTML sanitization - in production use DOMPurify
    let sanitized = input
    
    // Remove dangerous tags
    const dangerousTags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'style', 'link', 'meta']
    dangerousTags.forEach(tag => {
      const regex = new RegExp(`<${tag}[^>]*>.*?</${tag}>`, 'gi')
      sanitized = sanitized.replace(regex, '')
      sanitized = sanitized.replace(new RegExp(`<${tag}[^>]*>`, 'gi'), '')
    })
    
    // Remove event handlers
    sanitized = sanitized.replace(/on\w+\s*=\s*[^>]*/gi, '')
    
    // Remove javascript: and data: protocols
    sanitized = sanitized.replace(/(javascript|data|vbscript):/gi, '')
    
    return sanitized
  }

  /**
   * Generate CSRF token for forms
   */
  generateCSRFToken(): string {
    return SecurityUtils.generateSecureToken(32)
  }

  /**
   * Validate CSRF token
   */
  validateCSRFToken(token: string, expectedToken?: string): boolean {
    if (!token || typeof token !== 'string') {
      return false
    }
    
    // Basic format validation
    if (token.length !== 32 || !/^[A-Za-z0-9]+$/.test(token)) {
      return false
    }
    
    // In a real application, this would validate against server-stored tokens
    if (expectedToken) {
      return token === expectedToken
    }
    
    return true
  }

  /**
   * Rate limiting for form submissions
   */
  private submissionTimestamps: Map<string, number[]> = new Map()

  isSubmissionAllowed(formId: string, maxSubmissions: number = 5, windowMs: number = 60000): boolean {
    const now = Date.now()
    const timestamps = this.submissionTimestamps.get(formId) || []
    
    // Filter out old timestamps
    const recentTimestamps = timestamps.filter(timestamp => now - timestamp < windowMs)
    
    // Check if under the limit
    if (recentTimestamps.length >= maxSubmissions) {
      return false
    }
    
    // Add current timestamp
    recentTimestamps.push(now)
    this.submissionTimestamps.set(formId, recentTimestamps)
    
    return true
  }

  /**
   * Create secure form configuration for common field types
   */
  static createFieldConfigs(): Record<string, FieldConfig> {
    return {
      email: {
        required: true,
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        maxLength: 254,
        sanitize: true,
        customValidation: [{
          name: 'validEmail',
          validator: (value: string) => SecurityUtils.isValidEmail(value),
          message: 'Please enter a valid email address',
          severity: 'error'
        }]
      },
      password: {
        required: true,
        minLength: 8,
        maxLength: 128,
        sanitize: false, // Don't sanitize passwords
        customValidation: [{
          name: 'strongPassword',
          validator: (value: string) => {
            const result = SecurityUtils.validatePassword(value)
            return result.isValid
          },
          message: 'Password must be at least 8 characters with mixed case, numbers, and special characters',
          severity: 'error'
        }]
      },
      name: {
        required: true,
        minLength: 1,
        maxLength: 100,
        pattern: /^[a-zA-Z\s'-]+$/,
        sanitize: true
      },
      phone: {
        pattern: /^[\+]?[1-9][\d]{0,15}$/,
        maxLength: 20,
        sanitize: true
      },
      url: {
        maxLength: 2048,
        sanitize: true,
        customValidation: [{
          name: 'validURL',
          validator: (value: string) => {
            if (!value) return true // Optional field
            return SecurityUtils.sanitizeURL(value) !== null
          },
          message: 'Please enter a valid URL',
          severity: 'error'
        }]
      },
      textarea: {
        maxLength: 5000,
        sanitize: true,
        allowHTML: false
      },
      richText: {
        maxLength: 10000,
        sanitize: true,
        allowHTML: true
      }
    }
  }

  /**
   * Create honeypot field for bot detection
   */
  static createHoneypot(): { fieldName: string; fieldValue: string } {
    const fieldNames = ['website', 'url', 'homepage', 'link', 'address']
    const randomName = fieldNames[Math.floor(Math.random() * fieldNames.length)] + '_' + Math.random().toString(36).substr(2, 5)
    
    return {
      fieldName: randomName,
      fieldValue: ''
    }
  }

  /**
   * Validate honeypot field (should be empty)
   */
  static validateHoneypot(fieldName: string, formData: Record<string, any>): boolean {
    const value = formData[fieldName]
    return !value || value === ''
  }
}

// Export default instance
export const formSecurity = new FormSecurity()