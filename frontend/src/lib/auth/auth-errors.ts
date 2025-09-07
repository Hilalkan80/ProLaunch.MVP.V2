/**
 * Custom authentication error class
 */
export class AuthError extends Error {
  code?: string
  details?: Record<string, any>

  constructor(message: string, code?: string, details?: Record<string, any>) {
    super(message)
    this.name = 'AuthError'
    this.code = code
    this.details = details

    // Set prototype explicitly for better error handling
    Object.setPrototypeOf(this, AuthError.prototype)
  }
}