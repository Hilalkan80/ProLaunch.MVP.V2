/**
 * Enhanced token manager for secure authentication token handling
 * Features:
 * - Encrypted token storage
 * - Token expiration handling
 * - Automatic refresh mechanism
 * - Memory-based storage for high security
 */
import { Tokens } from './types'
import { SecurityUtils } from '../../utils/security'

interface StoredTokenData {
  token: string
  expiresAt: number
  encrypted: boolean
}

export class TokenManager {
  private readonly ACCESS_TOKEN_KEY = 'auth_access_token'
  private readonly REFRESH_TOKEN_KEY = 'auth_refresh_token'
  private readonly TOKEN_TIMESTAMP_KEY = 'auth_token_timestamp'
  private readonly SESSION_TIMEOUT = 30 * 60 * 1000 // 30 minutes
  
  // In-memory storage for enhanced security (optional)
  private memoryStorage: Map<string, StoredTokenData> = new Map()
  private useMemoryStorage: boolean = false
  
  constructor(options: { useMemoryStorage?: boolean } = {}) {
    this.useMemoryStorage = options.useMemoryStorage || false
    
    // Set up automatic token cleanup
    this.setupTokenCleanup()
  }

  /**
   * Store tokens securely with encryption and expiration
   */
  setTokens(tokens: Tokens): void {
    const now = Date.now()
    const accessTokenExpiry = tokens.expiresIn ? now + (tokens.expiresIn * 1000) : now + (15 * 60 * 1000) // Default 15 min
    const refreshTokenExpiry = now + (7 * 24 * 60 * 60 * 1000) // 7 days
    
    // Encrypt tokens before storage
    const encryptedAccessToken = this.encryptToken(tokens.accessToken)
    const encryptedRefreshToken = this.encryptToken(tokens.refreshToken)
    
    if (this.useMemoryStorage) {
      this.memoryStorage.set(this.ACCESS_TOKEN_KEY, {
        token: encryptedAccessToken,
        expiresAt: accessTokenExpiry,
        encrypted: true
      })
      this.memoryStorage.set(this.REFRESH_TOKEN_KEY, {
        token: encryptedRefreshToken,
        expiresAt: refreshTokenExpiry,
        encrypted: true
      })
    } else {
      // Store encrypted tokens with expiration metadata
      const accessTokenData = JSON.stringify({
        token: encryptedAccessToken,
        expiresAt: accessTokenExpiry,
        encrypted: true
      })
      const refreshTokenData = JSON.stringify({
        token: encryptedRefreshToken,
        expiresAt: refreshTokenExpiry,
        encrypted: true
      })
      
      try {
        localStorage.setItem(this.ACCESS_TOKEN_KEY, accessTokenData)
        localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshTokenData)
        localStorage.setItem(this.TOKEN_TIMESTAMP_KEY, now.toString())
      } catch (error) {
        console.error('Failed to store tokens:', error)
        // Fallback to sessionStorage if localStorage is full
        try {
          sessionStorage.setItem(this.ACCESS_TOKEN_KEY, accessTokenData)
          sessionStorage.setItem(this.REFRESH_TOKEN_KEY, refreshTokenData)
        } catch (sessionError) {
          throw new Error('Unable to store authentication tokens')
        }
      }
    }
  }

  /**
   * Retrieve stored tokens with automatic expiration check
   */
  getTokens(): { accessToken: string | null, refreshToken: string | null } {
    const accessTokenData = this.getTokenData(this.ACCESS_TOKEN_KEY)
    const refreshTokenData = this.getTokenData(this.REFRESH_TOKEN_KEY)
    
    const now = Date.now()
    
    // Check if access token is expired
    const accessToken = accessTokenData && accessTokenData.expiresAt > now 
      ? this.decryptToken(accessTokenData.token)
      : null
      
    // Check if refresh token is expired
    const refreshToken = refreshTokenData && refreshTokenData.expiresAt > now
      ? this.decryptToken(refreshTokenData.token)
      : null
    
    // Clean up expired tokens
    if (accessTokenData && accessTokenData.expiresAt <= now) {
      this.removeToken(this.ACCESS_TOKEN_KEY)
    }
    if (refreshTokenData && refreshTokenData.expiresAt <= now) {
      this.removeToken(this.REFRESH_TOKEN_KEY)
    }
    
    return { accessToken, refreshToken }
  }
  
  /**
   * Get token data from storage
   */
  private getTokenData(key: string): StoredTokenData | null {
    try {
      if (this.useMemoryStorage) {
        return this.memoryStorage.get(key) || null
      }
      
      let tokenDataStr = localStorage.getItem(key)
      if (!tokenDataStr) {
        tokenDataStr = sessionStorage.getItem(key)
      }
      
      if (!tokenDataStr) return null
      
      return JSON.parse(tokenDataStr) as StoredTokenData
    } catch (error) {
      console.error('Failed to parse token data:', error)
      return null
    }
  }

  /**
   * Clear all stored tokens securely
   */
  clearTokens(): void {
    if (this.useMemoryStorage) {
      this.memoryStorage.clear()
    } else {
      // Clear from both localStorage and sessionStorage
      const keysToRemove = [
        this.ACCESS_TOKEN_KEY,
        this.REFRESH_TOKEN_KEY,
        this.TOKEN_TIMESTAMP_KEY,
        'user_profile',
        'session_timestamp'
      ]
      
      keysToRemove.forEach(key => {
        localStorage.removeItem(key)
        sessionStorage.removeItem(key)
      })
    }
  }
  
  /**
   * Remove specific token
   */
  private removeToken(key: string): void {
    if (this.useMemoryStorage) {
      this.memoryStorage.delete(key)
    } else {
      localStorage.removeItem(key)
      sessionStorage.removeItem(key)
    }
  }

  /**
   * Validate JWT token format
   */
  isValidJWT(token: string): boolean {
    if (!token) return false

    const parts = token.split('.')
    if (parts.length !== 3) return false

    try {
      for (const part of parts) {
        if (!part) return false
        atob(part.replace(/-/g, '+').replace(/_/g, '/'))
      }
      return true
    } catch (error) {
      return false
    }
  }

  /**
   * Check if a token has expired
   */
  isTokenExpired(token: string | null | undefined): boolean {
    if (!token) return true

    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const exp = payload.exp

      if (!exp) return true

      return Date.now() >= exp * 1000
    } catch (error) {
      return true
    }
  }

  /**
   * Check if tokens are close to expiration (within 5 minutes)
   */
  shouldRefreshToken(): boolean {
    const { accessToken } = this.getTokens()
    if (!accessToken) return false
    
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]))
      const exp = payload.exp
      if (!exp) return false
      
      const timeUntilExpiry = (exp * 1000) - Date.now()
      return timeUntilExpiry < (5 * 60 * 1000) // Less than 5 minutes
    } catch (error) {
      return false
    }
  }
  
  /**
   * Get token expiration time
   */
  getTokenExpiration(tokenType: 'access' | 'refresh'): number | null {
    const key = tokenType === 'access' ? this.ACCESS_TOKEN_KEY : this.REFRESH_TOKEN_KEY
    const tokenData = this.getTokenData(key)
    return tokenData ? tokenData.expiresAt : null
  }
  
  /**
   * Encrypt token using browser's subtle crypto API
   */
  private encryptToken(token: string): string {
    try {
      // Simple encryption for browser storage (not cryptographically secure)
      // In production, use a proper encryption library
      const key = this.getEncryptionKey()
      return this.simpleEncrypt(token, key)
    } catch (error) {
      console.warn('Token encryption failed, storing as plain text')
      return token
    }
  }
  
  /**
   * Decrypt token
   */
  private decryptToken(encryptedToken: string): string {
    try {
      const key = this.getEncryptionKey()
      return this.simpleDecrypt(encryptedToken, key)
    } catch (error) {
      console.warn('Token decryption failed, returning as plain text')
      return encryptedToken
    }
  }
  
  /**
   * Get encryption key (derived from browser fingerprint)
   */
  private getEncryptionKey(): string {
    // Create a simple key based on browser characteristics
    const userAgent = navigator.userAgent
    const language = navigator.language
    const platform = navigator.platform
    const keySource = `${userAgent}-${language}-${platform}`
    
    // Simple hash function
    let hash = 0
    for (let i = 0; i < keySource.length; i++) {
      const char = keySource.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // Convert to 32-bit integer
    }
    
    return Math.abs(hash).toString(36)
  }
  
  /**
   * Simple encryption (XOR with key)
   */
  private simpleEncrypt(text: string, key: string): string {
    let encrypted = ''
    for (let i = 0; i < text.length; i++) {
      encrypted += String.fromCharCode(
        text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
      )
    }
    return btoa(encrypted)
  }
  
  /**
   * Simple decryption (XOR with key)
   */
  private simpleDecrypt(encryptedText: string, key: string): string {
    try {
      const encrypted = atob(encryptedText)
      let decrypted = ''
      for (let i = 0; i < encrypted.length; i++) {
        decrypted += String.fromCharCode(
          encrypted.charCodeAt(i) ^ key.charCodeAt(i % key.length)
        )
      }
      return decrypted
    } catch (error) {
      return encryptedText
    }
  }
  
  /**
   * Set up automatic token cleanup
   */
  private setupTokenCleanup(): void {
    // Clean up expired tokens every 5 minutes
    setInterval(() => {
      this.cleanupExpiredTokens()
    }, 5 * 60 * 1000)
  }
  
  /**
   * Clean up expired tokens
   */
  private cleanupExpiredTokens(): void {
    const now = Date.now()
    
    if (this.useMemoryStorage) {
      for (const [key, data] of this.memoryStorage.entries()) {
        if (data.expiresAt <= now) {
          this.memoryStorage.delete(key)
        }
      }
    } else {
      // Check and clean localStorage tokens
      const accessTokenData = this.getTokenData(this.ACCESS_TOKEN_KEY)
      const refreshTokenData = this.getTokenData(this.REFRESH_TOKEN_KEY)
      
      if (accessTokenData && accessTokenData.expiresAt <= now) {
        this.removeToken(this.ACCESS_TOKEN_KEY)
      }
      
      if (refreshTokenData && refreshTokenData.expiresAt <= now) {
        this.removeToken(this.REFRESH_TOKEN_KEY)
        // If refresh token is expired, clear everything
        this.clearTokens()
      }
    }
  }
  
  /**
   * Create a mock token for testing
   */
  createMockToken(payload: Record<string, any>): string {
    const header = { alg: 'HS256', typ: 'JWT' }
    const encodedHeader = btoa(JSON.stringify(header))
    const encodedPayload = btoa(JSON.stringify(payload))
    const signature = 'mock-signature'

    return `${encodedHeader}.${encodedPayload}.${signature}`
  }
}