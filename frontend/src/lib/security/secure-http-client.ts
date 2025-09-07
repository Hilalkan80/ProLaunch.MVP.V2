/**
 * Secure HTTP client with rate limiting, retry logic, and security headers
 */
import { globalRateLimiter, RateLimiter } from './rate-limiter'
import { TokenManager } from '../auth/token-manager'
import { SecurityUtils } from '../../utils/security'

interface RequestConfig extends RequestInit {
  timeout?: number
  retries?: number
  retryDelay?: number
  skipRateLimit?: boolean
  requireAuth?: boolean
  rateLimitConfig?: {
    maxRequests?: number
    windowMs?: number
  }
}

interface RequestMetrics {
  startTime: number
  endTime?: number
  duration?: number
  retryCount: number
  rateLimited: boolean
  success: boolean
}

export class SecureHttpClient {
  private tokenManager: TokenManager
  private rateLimiter: RateLimiter
  private baseURL: string
  private defaultTimeout: number = 30000 // 30 seconds
  private requestMetrics: Map<string, RequestMetrics> = new Map()

  constructor(baseURL: string = '', tokenManager?: TokenManager) {
    this.baseURL = baseURL
    this.tokenManager = tokenManager || new TokenManager()
    this.rateLimiter = globalRateLimiter
  }

  /**
   * Make secure HTTP request with all protections
   */
  async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<T> {
    const url = this.buildURL(endpoint)
    const requestId = this.generateRequestId()
    
    // Initialize metrics
    const metrics: RequestMetrics = {
      startTime: Date.now(),
      retryCount: 0,
      rateLimited: false,
      success: false
    }
    this.requestMetrics.set(requestId, metrics)

    try {
      // Check rate limiting
      if (!config.skipRateLimit) {
        const rateLimitCheck = this.rateLimiter.isAllowed(endpoint, config.rateLimitConfig)
        if (!rateLimitCheck.allowed) {
          metrics.rateLimited = true
          throw new Error(`Rate limited: ${rateLimitCheck.reason}. Retry after ${rateLimitCheck.retryAfter}ms`)
        }
      }

      const response = await this.makeRequestWithRetry(url, config, metrics)
      const data = await this.processResponse<T>(response)
      
      metrics.success = true
      metrics.endTime = Date.now()
      metrics.duration = metrics.endTime - metrics.startTime
      
      // Record successful request
      this.rateLimiter.recordSuccess(endpoint)
      
      return data
    } catch (error) {
      metrics.endTime = Date.now()
      metrics.duration = metrics.endTime - metrics.startTime
      
      // Record failed request
      if (!config.skipRateLimit) {
        this.rateLimiter.recordFailure(endpoint)
      }
      
      throw this.enhanceError(error, endpoint, metrics)
    }
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' })
  }

  /**
   * POST request with input sanitization
   */
  async post<T = any>(
    endpoint: string, 
    data?: any, 
    config: RequestConfig = {}
  ): Promise<T> {
    const sanitizedData = data ? this.sanitizeRequestData(data) : undefined
    
    return this.request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: sanitizedData ? JSON.stringify(sanitizedData) : undefined,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers
      }
    })
  }

  /**
   * PUT request with input sanitization
   */
  async put<T = any>(
    endpoint: string, 
    data?: any, 
    config: RequestConfig = {}
  ): Promise<T> {
    const sanitizedData = data ? this.sanitizeRequestData(data) : undefined
    
    return this.request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: sanitizedData ? JSON.stringify(sanitizedData) : undefined,
      headers: {
        'Content-Type': 'application/json',
        ...config.headers
      }
    })
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' })
  }

  /**
   * Make request with retry logic
   */
  private async makeRequestWithRetry(
    url: string,
    config: RequestConfig,
    metrics: RequestMetrics
  ): Promise<Response> {
    const maxRetries = config.retries || 3
    const retryDelay = config.retryDelay || 1000
    
    let lastError: Error

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        // Add delay between retries (exponential backoff)
        if (attempt > 0) {
          const delay = retryDelay * Math.pow(2, attempt - 1)
          await new Promise(resolve => setTimeout(resolve, delay))
          metrics.retryCount++
        }

        const response = await this.makeRequest(url, config)
        
        // Only retry on network errors or 5xx status codes
        if (response.ok || response.status < 500) {
          return response
        }
        
        lastError = new Error(`HTTP ${response.status}: ${response.statusText}`)
      } catch (error) {
        lastError = error as Error
        
        // Don't retry on authentication or client errors
        if (error instanceof Error && (
          error.message.includes('401') || 
          error.message.includes('403') || 
          error.message.includes('400')
        )) {
          break
        }
      }
    }

    throw lastError
  }

  /**
   * Make the actual HTTP request
   */
  private async makeRequest(url: string, config: RequestConfig): Promise<Response> {
    const controller = new AbortController()
    const timeout = config.timeout || this.defaultTimeout
    
    // Set up timeout
    const timeoutId = setTimeout(() => controller.abort(), timeout)
    
    try {
      const headers = await this.buildHeaders(config)
      
      const response = await fetch(url, {
        ...config,
        headers,
        signal: controller.signal
      })
      
      return response
    } finally {
      clearTimeout(timeoutId)
    }
  }

  /**
   * Build secure request headers
   */
  private async buildHeaders(config: RequestConfig): Promise<HeadersInit> {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'Cache-Control': 'no-cache',
      ...config.headers as Record<string, string>
    }

    // Add authentication header if required
    if (config.requireAuth !== false) {
      const { accessToken } = this.tokenManager.getTokens()
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
      }
    }

    // Add CSRF protection
    headers['X-CSRF-Token'] = SecurityUtils.generateSecureToken(32)
    
    // Add security headers
    headers['X-Content-Type-Options'] = 'nosniff'
    headers['X-Frame-Options'] = 'DENY'
    headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    return headers
  }

  /**
   * Process and validate response
   */
  private async processResponse<T>(response: Response): Promise<T> {
    // Check for authentication issues
    if (response.status === 401) {
      // Try to refresh token
      try {
        await this.tokenManager.refreshTokens()
        throw new Error('Token refreshed, please retry request')
      } catch (refreshError) {
        // Refresh failed, clear tokens
        this.tokenManager.clearTokens()
        throw new Error('Authentication expired')
      }
    }

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    const contentType = response.headers.get('content-type')
    
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json()
      // Sanitize response data to prevent XSS
      return this.sanitizeResponseData(data)
    }
    
    return response.text() as unknown as T
  }

  /**
   * Sanitize request data before sending
   */
  private sanitizeRequestData(data: any): any {
    if (typeof data === 'string') {
      return SecurityUtils.sanitizeInput(data)
    }
    
    if (typeof data === 'object' && data !== null) {
      return SecurityUtils.sanitizeObject(data)
    }
    
    return data
  }

  /**
   * Sanitize response data to prevent XSS
   */
  private sanitizeResponseData(data: any): any {
    if (typeof data === 'string') {
      return SecurityUtils.sanitizeInput(data)
    }
    
    if (Array.isArray(data)) {
      return data.map(item => this.sanitizeResponseData(item))
    }
    
    if (typeof data === 'object' && data !== null) {
      const sanitized: any = {}
      for (const [key, value] of Object.entries(data)) {
        sanitized[SecurityUtils.sanitizeInput(key)] = this.sanitizeResponseData(value)
      }
      return sanitized
    }
    
    return data
  }

  /**
   * Build full URL
   */
  private buildURL(endpoint: string): string {
    if (endpoint.startsWith('http')) {
      return endpoint
    }
    
    const base = this.baseURL.endsWith('/') ? this.baseURL.slice(0, -1) : this.baseURL
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    
    return `${base}${path}`
  }

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Enhance error with additional context
   */
  private enhanceError(error: any, endpoint: string, metrics: RequestMetrics): Error {
    const enhancedError = new Error(error.message || 'Request failed')
    
    // Add additional error properties
    Object.assign(enhancedError, {
      endpoint,
      duration: metrics.duration,
      retryCount: metrics.retryCount,
      rateLimited: metrics.rateLimited,
      timestamp: metrics.startTime,
      originalError: error
    })
    
    return enhancedError
  }

  /**
   * Get request metrics
   */
  getMetrics(): Array<RequestMetrics & { requestId: string }> {
    return Array.from(this.requestMetrics.entries()).map(([requestId, metrics]) => ({
      requestId,
      ...metrics
    }))
  }

  /**
   * Clear old metrics
   */
  clearOldMetrics(olderThanMs: number = 3600000): void {
    const cutoff = Date.now() - olderThanMs
    
    for (const [requestId, metrics] of this.requestMetrics.entries()) {
      if (metrics.startTime < cutoff) {
        this.requestMetrics.delete(requestId)
      }
    }
  }
}

// Global secure HTTP client instance
export const secureHttpClient = new SecureHttpClient()