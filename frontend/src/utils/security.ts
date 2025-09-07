/**
 * Enhanced security utilities for comprehensive input protection
 * Features:
 * - XSS prevention and sanitization
 * - SQL injection protection
 * - CSRF token generation
 * - Content Security Policy helpers
 * - Input validation and encoding
 */

/**
 * Comprehensive XSS sanitization utility
 * Removes HTML tags, JavaScript code, and dangerous attributes
 */
export class SecurityUtils {
  
  /**
   * Sanitize user input to prevent XSS attacks
   * Uses a comprehensive approach to remove all potentially dangerous content
   */
  static sanitizeInput(input: string): string {
    if (!input || typeof input !== 'string') {
      return ''
    }

    // First decode any HTML entities to handle encoded attacks
    let sanitized = this.decodeHtmlEntities(input)

    // Remove all script tags and their contents (case insensitive)
    sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gmi, '')
    
    // Remove other dangerous tags with their contents
    const dangerousTags = ['script', 'iframe', 'object', 'embed', 'form', 'meta', 'link', 'style']
    dangerousTags.forEach(tag => {
      const regex = new RegExp(`<${tag}\\b[^<]*(?:(?!<\\/${tag}>)<[^<]*)*<\\/${tag}>`, 'gmi')
      sanitized = sanitized.replace(regex, '')
    })
    
    // Remove self-closing dangerous tags
    sanitized = sanitized.replace(/<(iframe|embed|object|img|input|meta|link)[^>]*>/gi, '')
    
    // Remove all remaining HTML tags completely
    sanitized = sanitized.replace(/<[^>]*>/g, '')
    
    // Remove javascript: protocol (case insensitive, with optional whitespace)
    sanitized = sanitized.replace(/javascript\s*:/gi, '')
    
    // Remove vbscript: protocol
    sanitized = sanitized.replace(/vbscript\s*:/gi, '')
    
    // Remove data: protocol (can be used for XSS)
    sanitized = sanitized.replace(/data\s*:/gi, '')
    
    // Remove event handlers (onclick, onload, etc.) - more comprehensive
    sanitized = sanitized.replace(/on[a-zA-Z]+\s*=\s*[^>]*/gi, '')
    
    // Remove expression() CSS attacks
    sanitized = sanitized.replace(/expression\s*\([^)]*\)/gi, '')
    
    // Remove common XSS functions and keywords
    sanitized = sanitized.replace(/\balert\s*\(/gi, '')
    sanitized = sanitized.replace(/\bconfirm\s*\(/gi, '')
    sanitized = sanitized.replace(/\bprompt\s*\(/gi, '')
    sanitized = sanitized.replace(/\beval\s*\(/gi, '')
    sanitized = sanitized.replace(/\bdocument\./gi, '')
    sanitized = sanitized.replace(/\bwindow\./gi, '')
    
    // Remove any remaining angle brackets to prevent tag reconstruction
    sanitized = sanitized.replace(/[<>]/g, '')
    
    // Remove quotes that could be used to break out of attributes
    sanitized = sanitized.replace(/['"]/g, '')
    
    // Remove null characters
    sanitized = sanitized.replace(/\0/g, '')
    
    // Don't normalize whitespace to preserve spacing in tests
    // Just trim leading/trailing whitespace
    sanitized = sanitized.trim()
    
    return sanitized
  }

  /**
   * Decode HTML entities to catch encoded attacks
   */
  private static decodeHtmlEntities(input: string): string {
    const map = {
      '&amp;': '&',
      '&lt;': '<',
      '&gt;': '>',
      '&quot;': '"',
      '&#x27;': "'",
      '&#x2F;': '/',
      '&#x60;': '`',
      '&#x3D;': '=',
      '&#39;': "'",
      '&#34;': '"',
      '&#47;': '/',
      '&#96;': '`',
      '&#61;': '='
    }
    
    return input.replace(/&[#\w]+;/g, (entity) => {
      return map[entity as keyof typeof map] || entity
    })
  }

  /**
   * Validate email format with strict security rules
   */
  static isValidEmail(email: string): boolean {
    if (!email || typeof email !== 'string') {
      return false
    }

    // Check for basic XSS patterns in email
    if (this.containsXSSPatterns(email)) {
      return false
    }

    // Length checks
    if (email.length > 254) return false
    if (email.length < 3) return false

    // Must contain exactly one @
    const atSigns = email.split('@').length - 1
    if (atSigns !== 1) return false

    const [localPart, domain] = email.split('@')
    
    // Local part validation
    if (!localPart || localPart.length > 64 || localPart.startsWith('.') || localPart.endsWith('.')) {
      return false
    }

    // Domain validation
    if (!domain || domain.length > 253 || domain.startsWith('-') || domain.endsWith('-')) {
      return false
    }

    // RFC 5322 compliant email regex (simplified but secure)
    const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/
    
    return emailRegex.test(email)
  }

  /**
   * Check if input contains common XSS patterns
   */
  private static containsXSSPatterns(input: string): boolean {
    const xssPatterns = [
      /<script/i,
      /javascript:/i,
      /on\w+\s*=/i,
      /<iframe/i,
      /<object/i,
      /<embed/i,
      /<form/i,
      /expression\s*\(/i,
      /vbscript:/i,
      /data:/i,
      /<img/i,
      /<svg/i,
      /alert\s*\(/i,
      /eval\s*\(/i
    ]

    return xssPatterns.some(pattern => pattern.test(input))
  }

  /**
   * Sanitize object properties recursively
   */
  static sanitizeObject<T extends Record<string, any>>(obj: T): T {
    const sanitized = {} as T

    for (const [key, value] of Object.entries(obj)) {
      const sanitizedKey = this.sanitizeInput(key)
      
      if (typeof value === 'string') {
        sanitized[sanitizedKey as keyof T] = this.sanitizeInput(value) as T[keyof T]
      } else if (value && typeof value === 'object') {
        sanitized[sanitizedKey as keyof T] = this.sanitizeObject(value) as T[keyof T]
      } else {
        sanitized[sanitizedKey as keyof T] = value
      }
    }

    return sanitized
  }

  /**
   * Generate secure random token for CSRF protection
   */
  static generateSecureToken(length: number = 32): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let result = ''
    
    // Use crypto.getRandomValues if available (browser environment)
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
      const randomValues = new Uint8Array(length)
      crypto.getRandomValues(randomValues)
      
      for (let i = 0; i < length; i++) {
        result += chars[randomValues[i] % chars.length]
      }
    } else {
      // Fallback to Math.random (less secure, but better than nothing)
      for (let i = 0; i < length; i++) {
        result += chars[Math.floor(Math.random() * chars.length)]
      }
    }
    
    return result
  }

  /**
   * Advanced SQL injection pattern detection
   */
  static containsSQLInjection(input: string): boolean {
    if (!input || typeof input !== 'string') {
      return false
    }

    const sqlPatterns = [
      // Classic SQL injection patterns
      /('|(\-\-)|(;)|(\|)|(\*)|(%))/i,
      // SQL keywords
      /(\b(select|insert|update|delete|drop|create|alter|exec|execute|union|join)\b)/gi,
      // SQL functions
      /(\b(count|sum|avg|min|max|substring|concat)\s*\()/gi,
      // Comments
      /((\/\*(.|[\r\n])*?\*\/)|(--.*[\r\n]))/gi,
      // Hexadecimal values
      /0x[0-9a-f]+/gi,
      // SQL operators
      /(\bor\b|\band\b)\s+\w+\s*(=|<|>|!=|<>|like)/gi
    ]

    return sqlPatterns.some(pattern => pattern.test(input))
  }

  /**
   * Sanitize input to prevent SQL injection
   */
  static sanitizeSQLInput(input: string): string {
    if (!input || typeof input !== 'string') {
      return ''
    }

    // Remove SQL injection patterns
    let sanitized = input
      .replace(/('|(\-\-)|(;)|(\|))/g, '') // Remove quotes, comments, semicolons
      .replace(/(\b(select|insert|update|delete|drop|create|alter|exec|execute|union|join)\b)/gi, '') // Remove SQL keywords
      .replace(/(\b(or|and)\b)\s+\w+\s*(=|<|>|!=|<>|like)/gi, '') // Remove SQL conditions
      .replace(/0x[0-9a-f]+/gi, '') // Remove hex values
      .trim()

    return sanitized
  }

  /**
   * Validate and sanitize URL to prevent open redirect attacks
   */
  static sanitizeURL(url: string, allowedDomains: string[] = []): string | null {
    if (!url || typeof url !== 'string') {
      return null
    }

    try {
      const parsedUrl = new URL(url)
      
      // Only allow HTTP and HTTPS protocols
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
        return null
      }

      // Check allowed domains if specified
      if (allowedDomains.length > 0) {
        const isAllowed = allowedDomains.some(domain => 
          parsedUrl.hostname === domain || 
          parsedUrl.hostname.endsWith(`.${domain}`)
        )
        
        if (!isAllowed) {
          return null
        }
      }

      return parsedUrl.toString()
    } catch (error) {
      return null
    }
  }

  /**
   * Advanced XSS pattern detection
   */
  static detectAdvancedXSS(input: string): { isXSS: boolean; patterns: string[] } {
    if (!input || typeof input !== 'string') {
      return { isXSS: false, patterns: [] }
    }

    const detectedPatterns: string[] = []
    const xssPatterns = [
      { name: 'script-tag', pattern: /<script[^>]*>.*?<\/script>/gi },
      { name: 'javascript-protocol', pattern: /javascript\s*:/gi },
      { name: 'event-handlers', pattern: /on\w+\s*=/gi },
      { name: 'data-protocol', pattern: /data\s*:[^;]*;/gi },
      { name: 'svg-xss', pattern: /<svg[^>]*>.*?<\/svg>/gi },
      { name: 'iframe-xss', pattern: /<iframe[^>]*>.*?<\/iframe>/gi },
      { name: 'object-xss', pattern: /<object[^>]*>.*?<\/object>/gi },
      { name: 'embed-xss', pattern: /<embed[^>]*>/gi },
      { name: 'form-xss', pattern: /<form[^>]*>.*?<\/form>/gi },
      { name: 'input-xss', pattern: /<input[^>]*>/gi },
      { name: 'style-expression', pattern: /style\s*=.*?expression\s*\(/gi },
      { name: 'vbscript-protocol', pattern: /vbscript\s*:/gi },
      { name: 'base64-payload', pattern: /data:text\/html;base64,/gi }
    ]

    xssPatterns.forEach(({ name, pattern }) => {
      if (pattern.test(input)) {
        detectedPatterns.push(name)
      }
    })

    return {
      isXSS: detectedPatterns.length > 0,
      patterns: detectedPatterns
    }
  }

  /**
   * Content Security Policy (CSP) nonce generator
   */
  static generateCSPNonce(): string {
    const array = new Uint8Array(16)
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
      crypto.getRandomValues(array)
    } else {
      for (let i = 0; i < array.length; i++) {
        array[i] = Math.floor(Math.random() * 256)
      }
    }
    return btoa(String.fromCharCode.apply(null, Array.from(array)))
  }

  /**
   * Validate file upload security
   */
  static validateFileUpload(file: File, options: {
    maxSize?: number
    allowedTypes?: string[]
    allowedExtensions?: string[]
  } = {}): { isValid: boolean; errors: string[] } {
    const errors: string[] = []
    const { maxSize = 5 * 1024 * 1024, allowedTypes = [], allowedExtensions = [] } = options

    // Check file size
    if (file.size > maxSize) {
      errors.push(`File size exceeds ${maxSize} bytes`)
    }

    // Check MIME type
    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
      errors.push(`File type ${file.type} not allowed`)
    }

    // Check file extension
    if (allowedExtensions.length > 0) {
      const extension = file.name.split('.').pop()?.toLowerCase()
      if (!extension || !allowedExtensions.includes(extension)) {
        errors.push(`File extension .${extension} not allowed`)
      }
    }

    // Check for executable file patterns
    const dangerousExtensions = ['exe', 'scr', 'bat', 'cmd', 'com', 'pif', 'vbs', 'js', 'jar', 'php']
    const extension = file.name.split('.').pop()?.toLowerCase()
    if (extension && dangerousExtensions.includes(extension)) {
      errors.push(`Potentially dangerous file extension: .${extension}`)
    }

    // Check filename for path traversal
    if (file.name.includes('..') || file.name.includes('/') || file.name.includes('\\')) {
      errors.push('Filename contains path traversal characters')
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  }

  /**
   * Secure password validation
   */
  static validatePassword(password: string): {
    isValid: boolean
    score: number
    errors: string[]
    suggestions: string[]
  } {
    const errors: string[] = []
    const suggestions: string[] = []
    let score = 0

    if (!password) {
      errors.push('Password is required')
      return { isValid: false, score: 0, errors, suggestions }
    }

    // Length check
    if (password.length < 8) {
      errors.push('Password must be at least 8 characters long')
    } else if (password.length >= 12) {
      score += 2
    } else {
      score += 1
      suggestions.push('Consider using a longer password (12+ characters)')
    }

    // Character variety checks
    if (/[a-z]/.test(password)) score += 1
    else suggestions.push('Add lowercase letters')

    if (/[A-Z]/.test(password)) score += 1
    else suggestions.push('Add uppercase letters')

    if (/\d/.test(password)) score += 1
    else suggestions.push('Add numbers')

    if (/[^a-zA-Z\d]/.test(password)) score += 2
    else suggestions.push('Add special characters')

    // Common patterns check
    const commonPatterns = [
      /123456/,
      /password/i,
      /qwerty/i,
      /(.)\1{2,}/, // Repeated characters
      /^[a-zA-Z]+$/, // Only letters
      /^\d+$/ // Only numbers
    ]

    commonPatterns.forEach(pattern => {
      if (pattern.test(password)) {
        score -= 1
        suggestions.push('Avoid common patterns and repetitive characters')
      }
    })

    return {
      isValid: errors.length === 0 && score >= 4,
      score: Math.max(0, Math.min(10, score)),
      errors,
      suggestions: [...new Set(suggestions)] // Remove duplicates
    }
  }

  /**
   * Encode for different contexts to prevent injection
   */
  static contextualEncode(input: string, context: 'html' | 'attribute' | 'javascript' | 'css' | 'url'): string {
    if (!input || typeof input !== 'string') {
      return ''
    }

    switch (context) {
      case 'html':
        return this.escapeHtml(input)
      case 'attribute':
        return input.replace(/["`'<>&]/g, (char) => {
          const map: Record<string, string> = {
            '"': '&quot;',
            "'": '&#x27;',
            '`': '&#x60;',
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;'
          }
          return map[char] || char
        })
      case 'javascript':
        return input.replace(/[\\'"\r\n\t\b\f]/g, (char) => {
          const map: Record<string, string> = {
            '\\': '\\\\',
            "'": "\\'",
            '"': '\\"',
            '\r': '\\r',
            '\n': '\\n',
            '\t': '\\t',
            '\b': '\\b',
            '\f': '\\f'
          }
          return map[char] || char
        })
      case 'css':
        return input.replace(/[\\"'<>&\r\n\t\f]/g, (char) => {
          return `\\${char.charCodeAt(0).toString(16)} `
        })
      case 'url':
        return encodeURIComponent(input)
      default:
        return this.escapeHtml(input)
    }
  }

  /**
   * Escape HTML to prevent injection
   */
  static escapeHtml(input: string): string {
    if (!input || typeof input !== 'string') {
      return ''
    }

    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;',
      '`': '&#x60;',
      '=': '&#x3D;'
    }

    return input.replace(/[&<>"'`=/]/g, (char) => map[char as keyof typeof map])
  }
}