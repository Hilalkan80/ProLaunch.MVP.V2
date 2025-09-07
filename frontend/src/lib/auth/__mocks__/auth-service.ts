/**
 * Mock Auth Service with proper XSS sanitization
 */
import { SecurityUtils } from '../../../utils/security'

export class AuthService {
  private isLoggedIn = false
  private storage = new Map()
  private user = {
    id: '123',
    email: 'test@example.com'
  }

  async login({ email, password }) {
    if (email === 'test@example.com' && password === 'TestPassword123!') {
      this.isLoggedIn = true
      this.storage.set('user_profile', JSON.stringify(this.user))
      this.storage.set('access_token', 'mock.access.token')
      this.storage.set('refresh_token', 'mock.refresh.token')
      return {
        success: true,
        user: this.user,
        tokens: {
          accessToken: 'mock.access.token',
          refreshToken: 'mock.refresh.token'
        }
      }
    }

    if (email === 'locked@example.com') {
      throw new Error('Account is locked')
    }

    if (email === 'ratelimited@example.com') {
      throw new Error('Too many requests')
    }

    if (email === 'network@error.com') {
      throw new Error('Network error')
    }

    if (email === 'server@error.com') {
      throw new Error('Server error')
    }

    throw new Error('Invalid credentials')
  }

  async logout() {
    this.isLoggedIn = false
    this.storage.delete('access_token')
    this.storage.delete('refresh_token')
    this.storage.delete('user_profile')
    return { success: true }
  }

  isAuthenticated() {
    const accessToken = this.storage.get('access_token')
    const userProfile = this.storage.get('user_profile')
    return Boolean(accessToken && userProfile)
  }

  getCurrentUser() {
    return {
      id: '123',
      email: 'test@example.com'
    }
  }

  validatePasswordStrength(password) {
    if (password.length < 8) {
      throw new Error('Password too weak')
    }
  }

  refreshSession() {
    this.storage.set('session_timestamp', Date.now().toString())
  }

  isSessionValid() {
    const timestamp = this.storage.get('session_timestamp')
    if (!timestamp) return false
    const timeDiff = Date.now() - parseInt(timestamp)
    return timeDiff < 30 * 60 * 1000 // 30 minutes
  }

  async makeAuthenticatedRequest(url, options) {
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-CSRF-Token': this.generateCSRFToken()
      }
    })
  }

  /**
   * Register new user with proper XSS sanitization
   */
  async register(data) {
    if (data.email === 'existing@example.com') {
      throw new Error('Email already exists')
    }

    const user = {
      id: '123',
      email: data.email
    }

    // Use proper sanitization instead of simple regex
    if (data.businessIdea) {
      user['businessIdea'] = SecurityUtils.sanitizeInput(data.businessIdea)
    }

    if (data.fullName) {
      user['fullName'] = SecurityUtils.sanitizeInput(data.fullName)
    }

    if (data.companyName) {
      user['companyName'] = SecurityUtils.sanitizeInput(data.companyName)
    }

    this.isLoggedIn = true

    return {
      success: true,
      user,
      tokens: {
        accessToken: 'mock.access.token',
        refreshToken: 'mock.refresh.token'
      }
    }
  }

  /**
   * Sanitize user input (for test compatibility)
   */
  sanitizeInput(input: string): string {
    return SecurityUtils.sanitizeInput(input)
  }

  /**
   * Generate secure CSRF token
   */
  generateCSRFToken(): string {
    return SecurityUtils.generateSecureToken(32)
  }

  /**
   * Validate CSRF token
   */
  validateCSRFToken(token: string): boolean {
    return token && token.length === 32 && /^[A-Za-z0-9]+$/.test(token)
  }

  async refreshTokens() {
    const refreshToken = this.storage.get('refresh_token')
    if (refreshToken === 'invalid.token') {
      throw new Error('Invalid refresh token')
    }

    if (refreshToken === 'expired.token') {
      throw new Error('Token expired')
    }

    this.storage.set('access_token', 'new.access.token')
    this.storage.set('refresh_token', 'new.refresh.token')

    return {
      accessToken: 'new.access.token',
      refreshToken: 'new.refresh.token'
    }
  }

  async requestPasswordReset(email) {
    if (!SecurityUtils.isValidEmail(email)) {
      throw new Error('Invalid email format')
    }
    return { success: true }
  }

  async logoutAll() {
    await this.logout()
    // Additional API call could be made here to invalidate all sessions
  }
}
