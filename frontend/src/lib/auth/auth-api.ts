/**
 * Auth API client
 */

import { AuthError } from './auth-errors'
import type { LoginCredentials, RegisterData, AuthResponse, User } from './types'

export const AuthAPI = {
  /**
   * Authenticate user with email and password
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      // Simulated API call
      if (credentials.email === 'test@example.com' && credentials.password === 'TestPassword123!') {
        return {
          success: true,
          user: {
            id: '123',
            email: 'test@example.com',
            fullName: 'Test User'
          },
          tokens: {
            accessToken: 'mock.access.token',
            refreshToken: 'mock.refresh.token'
          }
        }
      }

      if (credentials.email === 'locked@example.com') {
        throw new AuthError('Account is locked')
      }

      if (credentials.email === 'ratelimited@example.com') {
        throw new AuthError('Too many requests')
      }

      if (credentials.email === 'network@error.com') {
        throw new AuthError('Network error')
      }

      throw new AuthError('Invalid credentials')
    } catch (error) {
      throw new AuthError(error.message)
    }
  },

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      if (data.email === 'existing@example.com') {
        throw new AuthError('Email already exists')
      }

      // Simulated API call
      return {
        success: true,
        user: {
          id: '123',
          ...data
        } as User,
        tokens: {
          accessToken: 'mock.access.token',
          refreshToken: 'mock.refresh.token'
        }
      }
    } catch (error) {
      throw new AuthError(error.message)
    }
  },

  /**
   * Logout user
   */
  async logout(): Promise<{ success: boolean }> {
    // Simulated API call
    return { success: true }
  },

  /**
   * Refresh access token using refresh token
   */
  async refreshTokens(refreshToken: string): Promise<{ accessToken: string, refreshToken: string }> {
    try {
      if (refreshToken === 'invalid.token') {
        throw new AuthError('Invalid refresh token')
      }

      if (refreshToken === 'expired.token') {
        throw new AuthError('Token expired')
      }

      // Simulated API call
      return {
        accessToken: 'new.access.token',
        refreshToken: 'new.refresh.token'
      }
    } catch (error) {
      throw new AuthError(error.message)
    }
  },

  /**
   * Request password reset email
   */
  async requestPasswordReset(email: string): Promise<{ success: boolean }> {
    try {
      if (!email.includes('@')) {
        throw new AuthError('Invalid email format')
      }
      // Simulated API call
      return { success: true }
    } catch (error) {
      throw new AuthError(error.message)
    }
  }
}