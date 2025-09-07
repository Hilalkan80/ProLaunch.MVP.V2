/**
 * Authentication types
 */

export interface User {
  id: string
  email: string
  fullName?: string
  businessIdea?: string
  companyName?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  fullName?: string
  businessIdea?: string
  companyName?: string
}

export interface Tokens {
  accessToken: string
  refreshToken: string
  tokenType?: string
  expiresIn?: number
}

export interface AuthResponse {
  success: boolean
  user: User
  tokens: Tokens
}