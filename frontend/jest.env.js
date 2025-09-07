// Environment variables for testing
process.env.NODE_ENV = 'test'
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
process.env.NEXT_PUBLIC_APP_ENV = 'test'

// JWT test configuration
process.env.JWT_SECRET = 'test-jwt-secret-key-for-testing-only'

// Mock environment variables that might be used in components
process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID = 'test-ga-id'
process.env.NEXT_PUBLIC_SENTRY_DSN = 'test-sentry-dsn'