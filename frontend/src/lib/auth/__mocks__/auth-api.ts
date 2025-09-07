/**
 * Mock Auth API
 */
import { AuthError } from '../auth-errors'

export const AuthAPI = {
  login: jest.fn(async ({ email, password }) => {
    if (email === 'test@example.com' && password === 'TestPassword123!') {
      return {
        success: true,
        user: {
          id: '123',
          email: 'test@example.com'
        },
        tokens: {
          accessToken: 'mock.access.token',
          refreshToken: 'mock.refresh.token'
        }
      }
    }

    if (email === 'locked@example.com') {
      throw new AuthError('Account is locked')
    }

    if (email === 'ratelimited@example.com') {
      throw new AuthError('Too many requests')
    }

    if (email === 'network@error.com') {
      throw new AuthError('Network error')
    }

    throw new AuthError('Invalid credentials')
  }),

  register: jest.fn(async (data) => {
    if (data.email === 'existing@example.com') {
      throw new AuthError('Email already exists')
    }

    // Sanitize input
    const user = {
      id: '123',
      email: data.email
    }

    if (data.businessIdea) {
      user['businessIdea'] = data.businessIdea.replace(/<[^>]*>?/gm, '')
    }

    if (data.fullName) {
      user['fullName'] = data.fullName.replace(/<[^>]*>?/gm, '')
    }

    return {
      success: true,
      user,
      tokens: {
        accessToken: 'mock.access.token',
        refreshToken: 'mock.refresh.token'
      }
    }
  }),

  logout: jest.fn(async () => {
    return { success: true }
  }),

  refreshTokens: jest.fn(async (refreshToken) => {
    if (refreshToken === 'invalid.token') {
      throw new AuthError('Invalid refresh token')
    }

    if (refreshToken === 'expired.token') {
      throw new AuthError('Token expired')
    }

    return {
      accessToken: 'new.access.token',
      refreshToken: 'new.refresh.token'
    }
  }),

  requestPasswordReset: jest.fn(async (email) => {
    if (!email.includes('@')) {
      throw new AuthError('Invalid email format')
    }
    return { success: true }
  })
}