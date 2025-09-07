/**
 * Security middleware for Next.js applications
 * Provides runtime security enforcement and monitoring
 */
import { NextRequest, NextResponse } from 'next/server'
import { SecurityUtils } from '../../utils/security'

interface SecurityConfig {
  enableCSRFProtection: boolean
  enableRateLimiting: boolean
  enableXSSProtection: boolean
  enableSQLInjectionProtection: boolean
  allowedOrigins: string[]
  blockedUserAgents: RegExp[]
  maxRequestSize: number
  sessionTimeout: number
}

interface SecurityMetrics {
  totalRequests: number
  blockedRequests: number
  xssAttempts: number
  sqlInjectionAttempts: number
  csrfFailures: number
  rateLimitHits: number
  lastReset: number
}

export class SecurityMiddleware {
  private config: SecurityConfig
  private metrics: SecurityMetrics
  private requestCounts: Map<string, { count: number; timestamp: number }> = new Map()
  private blockedIPs: Set<string> = new Set()

  constructor(config: Partial<SecurityConfig> = {}) {
    this.config = {
      enableCSRFProtection: true,
      enableRateLimiting: true,
      enableXSSProtection: true,
      enableSQLInjectionProtection: true,
      allowedOrigins: ['localhost:3000', 'localhost:3001'],
      blockedUserAgents: [
        /bot/i,
        /crawler/i,
        /spider/i,
        /scraper/i
      ],
      maxRequestSize: 1024 * 1024, // 1MB
      sessionTimeout: 30 * 60 * 1000, // 30 minutes
      ...config
    }

    this.metrics = {
      totalRequests: 0,
      blockedRequests: 0,
      xssAttempts: 0,
      sqlInjectionAttempts: 0,
      csrfFailures: 0,
      rateLimitHits: 0,
      lastReset: Date.now()
    }

    // Reset metrics every hour
    setInterval(() => this.resetMetrics(), 3600000)
  }

  /**
   * Main middleware handler
   */
  async handle(request: NextRequest): Promise<NextResponse | null> {
    this.metrics.totalRequests++
    
    const clientIP = this.getClientIP(request)
    const userAgent = request.headers.get('user-agent') || ''
    
    try {
      // Check if IP is blocked
      if (this.blockedIPs.has(clientIP)) {
        this.metrics.blockedRequests++
        return this.createErrorResponse('IP blocked', 403)
      }

      // Check user agent
      if (this.isBlockedUserAgent(userAgent)) {
        this.blockIP(clientIP, 'Blocked user agent')
        this.metrics.blockedRequests++
        return this.createErrorResponse('Access denied', 403)
      }

      // Rate limiting
      if (this.config.enableRateLimiting && !this.checkRateLimit(clientIP)) {
        this.metrics.rateLimitHits++
        return this.createErrorResponse('Rate limit exceeded', 429)
      }

      // CORS validation
      const corsResult = this.validateCORS(request)
      if (!corsResult.allowed) {
        this.metrics.blockedRequests++
        return this.createErrorResponse('CORS policy violation', 403)
      }

      // Request size validation
      if (!this.validateRequestSize(request)) {
        this.metrics.blockedRequests++
        return this.createErrorResponse('Request too large', 413)
      }

      // XSS protection
      if (this.config.enableXSSProtection) {
        const xssResult = await this.checkForXSS(request)
        if (xssResult.detected) {
          this.metrics.xssAttempts++
          this.blockIP(clientIP, `XSS attempt: ${xssResult.patterns.join(', ')}`)
          return this.createErrorResponse('Malicious content detected', 400)
        }
      }

      // SQL injection protection
      if (this.config.enableSQLInjectionProtection) {
        const sqlResult = await this.checkForSQLInjection(request)
        if (sqlResult.detected) {
          this.metrics.sqlInjectionAttempts++
          this.blockIP(clientIP, `SQL injection attempt: ${sqlResult.patterns.join(', ')}`)
          return this.createErrorResponse('Malicious content detected', 400)
        }
      }

      // CSRF protection for state-changing methods
      if (this.config.enableCSRFProtection && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method)) {
        const csrfResult = this.validateCSRF(request)
        if (!csrfResult.valid) {
          this.metrics.csrfFailures++
          return this.createErrorResponse('CSRF token validation failed', 403)
        }
      }

      // Add security headers to response
      return this.addSecurityHeaders(request)

    } catch (error) {
      console.error('Security middleware error:', error)
      return this.createErrorResponse('Internal security error', 500)
    }
  }

  /**
   * Get client IP address
   */
  private getClientIP(request: NextRequest): string {
    const forwarded = request.headers.get('x-forwarded-for')
    const realIP = request.headers.get('x-real-ip')
    
    if (forwarded) {
      return forwarded.split(',')[0].trim()
    }
    
    if (realIP) {
      return realIP
    }
    
    return request.ip || 'unknown'
  }

  /**
   * Check if user agent is blocked
   */
  private isBlockedUserAgent(userAgent: string): boolean {
    return this.config.blockedUserAgents.some(pattern => pattern.test(userAgent))
  }

  /**
   * Rate limiting check
   */
  private checkRateLimit(clientIP: string): boolean {
    const now = Date.now()
    const windowMs = 60000 // 1 minute
    const maxRequests = 100
    
    const record = this.requestCounts.get(clientIP)
    
    if (!record || (now - record.timestamp) > windowMs) {
      this.requestCounts.set(clientIP, { count: 1, timestamp: now })
      return true
    }
    
    if (record.count >= maxRequests) {
      return false
    }
    
    record.count++
    return true
  }

  /**
   * Validate CORS policy
   */
  private validateCORS(request: NextRequest): { allowed: boolean; origin?: string } {
    const origin = request.headers.get('origin')
    
    if (!origin) {
      // Same-origin requests don't have Origin header
      return { allowed: true }
    }
    
    const originHostname = new URL(origin).hostname
    const isAllowed = this.config.allowedOrigins.some(allowed => {
      return originHostname === allowed || originHostname.endsWith(`.${allowed}`)
    })
    
    return { allowed: isAllowed, origin }
  }

  /**
   * Validate request size
   */
  private validateRequestSize(request: NextRequest): boolean {
    const contentLength = request.headers.get('content-length')
    
    if (contentLength) {
      const size = parseInt(contentLength, 10)
      return size <= this.config.maxRequestSize
    }
    
    return true
  }

  /**
   * Check for XSS patterns in request
   */
  private async checkForXSS(request: NextRequest): Promise<{ detected: boolean; patterns: string[] }> {
    const patterns: string[] = []
    
    // Check URL parameters
    const url = new URL(request.url)
    for (const [key, value] of url.searchParams.entries()) {
      const xssResult = SecurityUtils.detectAdvancedXSS(`${key}=${value}`)
      if (xssResult.isXSS) {
        patterns.push(...xssResult.patterns)
      }
    }
    
    // Check headers
    const suspiciousHeaders = ['user-agent', 'referer', 'x-forwarded-for']
    for (const headerName of suspiciousHeaders) {
      const headerValue = request.headers.get(headerName)
      if (headerValue) {
        const xssResult = SecurityUtils.detectAdvancedXSS(headerValue)
        if (xssResult.isXSS) {
          patterns.push(...xssResult.patterns)
        }
      }
    }
    
    // Check request body for POST/PUT requests
    if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
      try {
        const body = await request.text()
        if (body) {
          const xssResult = SecurityUtils.detectAdvancedXSS(body)
          if (xssResult.isXSS) {
            patterns.push(...xssResult.patterns)
          }
        }
      } catch (error) {
        // Body already consumed or invalid, skip check
      }
    }
    
    return {
      detected: patterns.length > 0,
      patterns: [...new Set(patterns)] // Remove duplicates
    }
  }

  /**
   * Check for SQL injection patterns in request
   */
  private async checkForSQLInjection(request: NextRequest): Promise<{ detected: boolean; patterns: string[] }> {
    const patterns: string[] = []
    
    // Check URL parameters
    const url = new URL(request.url)
    for (const [key, value] of url.searchParams.entries()) {
      if (SecurityUtils.containsSQLInjection(`${key}=${value}`)) {
        patterns.push('url-params')
      }
    }
    
    // Check request body for POST/PUT requests
    if (['POST', 'PUT', 'PATCH'].includes(request.method)) {
      try {
        const body = await request.text()
        if (body && SecurityUtils.containsSQLInjection(body)) {
          patterns.push('request-body')
        }
      } catch (error) {
        // Body already consumed or invalid, skip check
      }
    }
    
    return {
      detected: patterns.length > 0,
      patterns: [...new Set(patterns)]
    }
  }

  /**
   * Validate CSRF token
   */
  private validateCSRF(request: NextRequest): { valid: boolean; reason?: string } {
    const token = request.headers.get('x-csrf-token')
    
    if (!token) {
      return { valid: false, reason: 'Missing CSRF token' }
    }
    
    // Basic token format validation
    if (token.length !== 32 || !/^[A-Za-z0-9]+$/.test(token)) {
      return { valid: false, reason: 'Invalid CSRF token format' }
    }
    
    // In production, this should validate against server-stored tokens
    return { valid: true }
  }

  /**
   * Add security headers to response
   */
  private addSecurityHeaders(request: NextRequest): NextResponse {
    const response = NextResponse.next()
    
    // Generate CSP nonce
    const nonce = SecurityUtils.generateCSPNonce()
    
    // Set security headers
    response.headers.set('X-Content-Type-Options', 'nosniff')
    response.headers.set('X-Frame-Options', 'DENY')
    response.headers.set('X-XSS-Protection', '1; mode=block')
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.set('X-Request-ID', SecurityUtils.generateSecureToken(16))
    
    // Set CSP nonce for scripts
    response.headers.set('CSP-Nonce', nonce)
    
    return response
  }

  /**
   * Block IP address temporarily
   */
  private blockIP(ip: string, reason: string): void {
    this.blockedIPs.add(ip)
    console.warn(`IP ${ip} blocked: ${reason}`)
    
    // Unblock after 1 hour
    setTimeout(() => {
      this.blockedIPs.delete(ip)
      console.info(`IP ${ip} unblocked`)
    }, 3600000)
  }

  /**
   * Create error response
   */
  private createErrorResponse(message: string, status: number): NextResponse {
    return new NextResponse(
      JSON.stringify({
        error: message,
        timestamp: new Date().toISOString(),
        requestId: SecurityUtils.generateSecureToken(16)
      }),
      {
        status,
        headers: {
          'Content-Type': 'application/json',
          'X-Content-Type-Options': 'nosniff'
        }
      }
    )
  }

  /**
   * Reset metrics
   */
  private resetMetrics(): void {
    this.metrics = {
      totalRequests: 0,
      blockedRequests: 0,
      xssAttempts: 0,
      sqlInjectionAttempts: 0,
      csrfFailures: 0,
      rateLimitHits: 0,
      lastReset: Date.now()
    }
  }

  /**
   * Get current security metrics
   */
  getMetrics(): SecurityMetrics {
    return { ...this.metrics }
  }

  /**
   * Get blocked IPs list
   */
  getBlockedIPs(): string[] {
    return Array.from(this.blockedIPs)
  }

  /**
   * Manually unblock IP
   */
  unblockIP(ip: string): boolean {
    return this.blockedIPs.delete(ip)
  }
}

// Export default instance
export const securityMiddleware = new SecurityMiddleware()