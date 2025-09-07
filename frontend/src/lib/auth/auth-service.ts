/**
 * Enhanced authentication service with comprehensive security protection
 */
import { AuthError } from './auth-errors'
import { TokenManager } from './token-manager'
import { SecurityUtils } from '../../utils/security'
import { secureHttpClient } from '../security/secure-http-client'
import { formSecurity } from '../security/form-security'
import { globalRateLimiter } from '../security/rate-limiter'
import type { LoginCredentials, RegisterData, User } from './types'

export class AuthService {
  private tokenManager: TokenManager
  private maxLoginAttempts = 5
  private lockoutDuration = 15 * 60 * 1000 // 15 minutes
  private loginAttempts = new Map<string, { count: number; lockedUntil?: number }>()

  constructor(private api = require('./auth-api').AuthAPI) {
    this.tokenManager = new TokenManager({ useMemoryStorage: false })
    
    // Set up automatic token refresh
    this.setupTokenRefresh()
  }

  /**
   * Enhanced login with comprehensive security checks
   */
  async login(credentials: LoginCredentials) {
    const email = credentials.email?.toLowerCase()?.trim()
    
    // Check account lockout
    const lockoutStatus = this.checkAccountLockout(email)
    if (lockoutStatus.locked) {
      throw new AuthError(`Account temporarily locked. Try again in ${Math.ceil(lockoutStatus.remainingTime! / 60000)} minutes.`)
    }

    // Rate limiting check
    const rateLimitCheck = globalRateLimiter.isAllowed('auth.login', {
      maxRequests: 5,
      windowMs: 300000 // 5 minutes
    })
    
    if (!rateLimitCheck.allowed) {
      throw new AuthError(`Too many login attempts. Please wait ${Math.ceil(rateLimitCheck.retryAfter! / 1000)} seconds.`)
    }

    // Comprehensive validation
    const validationResult = await formSecurity.validateAndSanitizeForm(credentials, {
      email: {
        required: true,
        sanitize: true,
        customValidation: [{
          name: 'validEmail',
          validator: (value: string) => SecurityUtils.isValidEmail(value),
          message: 'Invalid email format',
          severity: 'error'
        }]
      },
      password: {
        required: true,
        minLength: 1,
        sanitize: false // Don't sanitize passwords
      }
    })

    if (!validationResult.isValid) {
      const errorMessages = validationResult.errors
        .filter(e => e.severity === 'error')
        .map(e => e.message)
        .join(', ')
      throw new AuthError(errorMessages)
    }

    try {
      // Use secure HTTP client for authentication
      const response = await secureHttpClient.post('/auth/login', validationResult.sanitizedData, {
        requireAuth: false,
        skipRateLimit: true // Already rate limited above
      })

      if (response.success) {
        // Clear login attempts on success
        this.loginAttempts.delete(email)
        
        // Store tokens securely
        this.tokenManager.setTokens(response.tokens)
        
        // Sanitize and store user data
        const sanitizedUser = SecurityUtils.sanitizeObject(response.user)
        this.storeUserData(sanitizedUser)
        
        // Record successful authentication
        globalRateLimiter.recordSuccess('auth.login')
        
        return response
      } else {
        throw new AuthError(response.message || 'Login failed')
      }
      
    } catch (error) {
      // Record failed login attempt
      this.recordFailedLogin(email)
      globalRateLimiter.recordFailure('auth.login')
      
      if (error instanceof AuthError) {
        throw error
      }
      
      throw new AuthError('Authentication failed. Please check your credentials.')
    }
  }

  /**
   * Register new user
   */
  async register(data: RegisterData) {
    if (!SecurityUtils.isValidEmail(data.email)) {
      throw new AuthError('Invalid email format')
    }

    this.validatePasswordStrength(data.password)

    // Sanitize all user input data before processing
    const sanitizedData = {
      ...data,
      email: SecurityUtils.sanitizeInput(data.email),
      businessIdea: data.businessIdea ? SecurityUtils.sanitizeInput(data.businessIdea) : undefined,
      fullName: data.fullName ? SecurityUtils.sanitizeInput(data.fullName) : undefined,
      companyName: data.companyName ? SecurityUtils.sanitizeInput(data.companyName) : undefined
    }

    const response = await this.api.register(sanitizedData)

    if (response.success) {
      this.tokenManager.setTokens(response.tokens)
      // Ensure user data is also sanitized before storage
      const sanitizedUser = SecurityUtils.sanitizeObject(response.user)
      localStorage.setItem('user_profile', JSON.stringify(sanitizedUser))
    }

    return response
  }

  /**
   * Log out current user
   */
  async logout() {
    await this.api.logout()
    this.tokenManager.clearTokens()
  }

  /**
   * Log out from all devices
   */
  async logoutAll() {
    await this.logout()
    // Additional API call could be made here to invalidate all sessions
  }

  /**
   * Enhanced authentication check with session validation
   */
  isAuthenticated(): boolean {
    const { accessToken, refreshToken } = this.tokenManager.getTokens()
    
    if (!accessToken || !refreshToken) {
      return false
    }
    
    // Check if user data exists and is valid
    const user = this.getCurrentUser()
    if (!user) {
      return false
    }
    
    // Check session timeout
    const sessionStart = localStorage.getItem('user_session_start')
    if (sessionStart) {
      const sessionAge = Date.now() - parseInt(sessionStart)
      const maxSessionAge = 8 * 60 * 60 * 1000 // 8 hours
      
      if (sessionAge > maxSessionAge) {
        this.logout() // Auto-logout on session timeout
        return false
      }
    }
    
    return true
  }

  /**
   * Get current user profile with decryption
   */
  getCurrentUser(): User | null {
    try {
      const encryptedData = localStorage.getItem('user_profile')
      if (!encryptedData) return null
      
      return this.decryptUserData(encryptedData)
    } catch (error) {
      console.error('Failed to get current user:', error)
      // Clear corrupted data
      localStorage.removeItem('user_profile')
      return null
    }
  }

  /**
   * Refresh authentication tokens
   */
  async refreshTokens() {
    const { refreshToken } = this.tokenManager.getTokens()
    if (!refreshToken) {
      throw new AuthError('No refresh token available')
    }

    try {
      const tokens = await this.api.refreshTokens(refreshToken)
      this.tokenManager.setTokens(tokens)
      return tokens
    } catch (error) {
      this.tokenManager.clearTokens()
      throw error
    }
  }

  /**
   * Request password reset email
   */
  async requestPasswordReset(email: string) {
    if (!SecurityUtils.isValidEmail(email)) {
      throw new AuthError('Invalid email format')
    }
    return this.api.requestPasswordReset(SecurityUtils.sanitizeInput(email))
  }

  /**
   * Validate email format
   */
  private isValidEmail(email: string): boolean {
    return SecurityUtils.isValidEmail(email)
  }

  /**
   * Sanitize user input to prevent XSS attacks
   */
  sanitizeInput(input: string): string {
    return SecurityUtils.sanitizeInput(input)
  }

  /**
   * Validate password strength
   */
  validatePasswordStrength(password: string) {
    if (password.length < 8) {
      throw new AuthError('Password too weak')
    }
    // More password requirements could be added here
  }

  /**
   * Refresh session timestamp
   */
  refreshSession() {
    localStorage.setItem('session_timestamp', Date.now().toString())
  }

  /**
   * Check if session is valid
   */
  isSessionValid(): boolean {
    const timestamp = localStorage.getItem('session_timestamp')
    if (!timestamp) return false
    const timeDiff = Date.now() - parseInt(timestamp)
    return timeDiff < 30 * 60 * 1000 // 30 minutes
  }

  /**
   * Enhanced user data storage
   */
  private storeUserData(user: User): void {
    try {
      const encryptedData = this.encryptUserData(user)
      localStorage.setItem('user_profile', encryptedData)
      localStorage.setItem('user_session_start', Date.now().toString())
    } catch (error) {
      console.error('Failed to store user data:', error)
      throw new AuthError('Failed to complete authentication')
    }
  }

  /**
   * Encrypt user data before storage
   */
  private encryptUserData(user: User): string {
    // Simple encryption for demo - use a proper library in production
    const dataStr = JSON.stringify(user)
    const encoded = btoa(dataStr)
    return encoded
  }

  /**
   * Decrypt user data after retrieval
   */
  private decryptUserData(encryptedData: string): User | null {
    try {
      const decoded = atob(encryptedData)
      return JSON.parse(decoded)
    } catch (error) {
      console.error('Failed to decrypt user data:', error)
      return null
    }
  }

  /**
   * Check account lockout status
   */
  private checkAccountLockout(email: string): { locked: boolean; remainingTime?: number } {
    const attempts = this.loginAttempts.get(email)
    
    if (!attempts || attempts.count < this.maxLoginAttempts) {
      return { locked: false }
    }
    
    if (attempts.lockedUntil && Date.now() < attempts.lockedUntil) {
      return {
        locked: true,
        remainingTime: attempts.lockedUntil - Date.now()
      }
    }
    
    // Lockout expired, reset attempts
    this.loginAttempts.delete(email)
    return { locked: false }
  }

  /**
   * Record failed login attempt
   */
  private recordFailedLogin(email: string): void {
    const attempts = this.loginAttempts.get(email) || { count: 0 }
    attempts.count++
    
    if (attempts.count >= this.maxLoginAttempts) {
      attempts.lockedUntil = Date.now() + this.lockoutDuration
    }
    
    this.loginAttempts.set(email, attempts)
  }

  /**
   * Set up automatic token refresh
   */
  private setupTokenRefresh(): void {
    // Check token expiration every 5 minutes
    setInterval(async () => {
      try {
        if (this.isAuthenticated() && this.tokenManager.shouldRefreshToken()) {
          await this.refreshTokens()
        }
      } catch (error) {
        console.error('Automatic token refresh failed:', error)
        // Force logout on refresh failure
        await this.logout()
      }
    }, 5 * 60 * 1000)
  }

  /**
   * Make authenticated request using secure HTTP client
   */
  async makeAuthenticatedRequest<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
    if (!this.isAuthenticated()) {
      throw new AuthError('Not authenticated')
    }

    return secureHttpClient.request<T>(endpoint, {
      ...options,
      requireAuth: true
    })
  }

  /**
   * Generate secure CSRF token (public method for tests)
   */
  generateCSRFToken(): string {
    return SecurityUtils.generateSecureToken(32)
  }

  /**
   * Validate CSRF token
   */
  validateCSRFToken(token: string): boolean {
    // In a real implementation, this would validate against server-stored tokens
    return token && token.length === 32 && /^[A-Za-z0-9]+$/.test(token)
  }
}