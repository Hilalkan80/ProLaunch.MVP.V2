/**
 * Client-side rate limiting with exponential backoff
 * Protects against excessive API requests and potential abuse
 */

interface RequestRecord {
  count: number
  firstRequest: number
  lastRequest: number
  backoffUntil?: number
}

interface RateLimitConfig {
  maxRequests: number
  windowMs: number
  backoffMultiplier: number
  maxBackoffMs: number
  skipSuccessful?: boolean
}

interface ThrottleOptions {
  leading?: boolean
  trailing?: boolean
}

export class RateLimiter {
  private requests: Map<string, RequestRecord> = new Map()
  private readonly defaultConfig: RateLimitConfig = {
    maxRequests: 10,
    windowMs: 60000, // 1 minute
    backoffMultiplier: 2,
    maxBackoffMs: 300000, // 5 minutes
    skipSuccessful: false
  }

  /**
   * Check if request should be allowed
   */
  isAllowed(
    endpoint: string, 
    config: Partial<RateLimitConfig> = {}
  ): { allowed: boolean; retryAfter?: number; reason?: string } {
    const finalConfig = { ...this.defaultConfig, ...config }
    const now = Date.now()
    const key = this.getKey(endpoint)
    
    let record = this.requests.get(key)
    
    // Check if currently in backoff period
    if (record?.backoffUntil && now < record.backoffUntil) {
      return {
        allowed: false,
        retryAfter: record.backoffUntil - now,
        reason: 'Rate limited - exponential backoff active'
      }
    }
    
    // Initialize or reset record if window has passed
    if (!record || (now - record.firstRequest) > finalConfig.windowMs) {
      record = {
        count: 0,
        firstRequest: now,
        lastRequest: now
      }
      this.requests.set(key, record)
    }
    
    // Check if within rate limit
    if (record.count < finalConfig.maxRequests) {
      record.count++
      record.lastRequest = now
      return { allowed: true }
    }
    
    // Rate limit exceeded - apply exponential backoff
    const backoffDuration = Math.min(
      finalConfig.windowMs * Math.pow(finalConfig.backoffMultiplier, record.count - finalConfig.maxRequests),
      finalConfig.maxBackoffMs
    )
    
    record.backoffUntil = now + backoffDuration
    record.lastRequest = now
    
    return {
      allowed: false,
      retryAfter: backoffDuration,
      reason: `Rate limit exceeded. ${record.count} requests in ${finalConfig.windowMs}ms window`
    }
  }

  /**
   * Record successful request (can reset backoff)
   */
  recordSuccess(endpoint: string): void {
    const key = this.getKey(endpoint)
    const record = this.requests.get(key)
    
    if (record) {
      // Reset backoff on successful request
      delete record.backoffUntil
    }
  }

  /**
   * Record failed request (extends backoff)
   */
  recordFailure(endpoint: string): void {
    const key = this.getKey(endpoint)
    const record = this.requests.get(key)
    
    if (record) {
      record.count++
    }
  }

  /**
   * Create throttled function
   */
  throttle<T extends (...args: any[]) => any>(
    func: T,
    delay: number,
    options: ThrottleOptions = {}
  ): (...args: Parameters<T>) => Promise<ReturnType<T> | undefined> {
    let lastExecution = 0
    let timeoutId: NodeJS.Timeout | null = null
    const { leading = true, trailing = true } = options

    return async (...args: Parameters<T>): Promise<ReturnType<T> | undefined> => {
      const now = Date.now()
      const timeSinceLastExecution = now - lastExecution

      return new Promise((resolve) => {
        const execute = () => {
          lastExecution = Date.now()
          const result = func(...args)
          resolve(result)
        }

        if (timeSinceLastExecution >= delay) {
          if (leading) {
            execute()
          } else {
            timeoutId = setTimeout(execute, delay)
          }
        } else if (trailing) {
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          timeoutId = setTimeout(execute, delay - timeSinceLastExecution)
        } else {
          resolve(undefined)
        }
      })
    }
  }

  /**
   * Create debounced function
   */
  debounce<T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): (...args: Parameters<T>) => Promise<ReturnType<T>> {
    let timeoutId: NodeJS.Timeout | null = null

    return (...args: Parameters<T>): Promise<ReturnType<T>> => {
      return new Promise((resolve) => {
        if (timeoutId) {
          clearTimeout(timeoutId)
        }

        timeoutId = setTimeout(() => {
          const result = func(...args)
          resolve(result)
        }, delay)
      })
    }
  }

  /**
   * Implement request queue for managing burst requests
   */
  createRequestQueue(maxConcurrent: number = 3, delay: number = 100) {
    const queue: Array<() => Promise<any>> = []
    let running = 0

    const processQueue = async (): Promise<void> => {
      if (queue.length === 0 || running >= maxConcurrent) {
        return
      }

      running++
      const request = queue.shift()!

      try {
        await request()
      } finally {
        running--
        // Add delay between requests
        setTimeout(() => {
          processQueue()
        }, delay)
      }
    }

    return {
      add: <T>(request: () => Promise<T>): Promise<T> => {
        return new Promise((resolve, reject) => {
          queue.push(async () => {
            try {
              const result = await request()
              resolve(result)
            } catch (error) {
              reject(error)
            }
          })
          processQueue()
        })
      },
      size: () => queue.length,
      clear: () => {
        queue.length = 0
      }
    }
  }

  /**
   * Clear expired records
   */
  cleanup(): void {
    const now = Date.now()
    
    for (const [key, record] of this.requests.entries()) {
      // Remove records older than 1 hour
      if (now - record.lastRequest > 3600000) {
        this.requests.delete(key)
      }
    }
  }

  /**
   * Get current rate limit status
   */
  getStatus(endpoint: string): {
    requestCount: number
    windowStart: number
    backoffUntil?: number
    isRateLimited: boolean
  } {
    const key = this.getKey(endpoint)
    const record = this.requests.get(key)
    const now = Date.now()

    if (!record) {
      return {
        requestCount: 0,
        windowStart: now,
        isRateLimited: false
      }
    }

    return {
      requestCount: record.count,
      windowStart: record.firstRequest,
      backoffUntil: record.backoffUntil,
      isRateLimited: Boolean(record.backoffUntil && now < record.backoffUntil)
    }
  }

  /**
   * Reset rate limit for specific endpoint
   */
  reset(endpoint: string): void {
    const key = this.getKey(endpoint)
    this.requests.delete(key)
  }

  /**
   * Reset all rate limits
   */
  resetAll(): void {
    this.requests.clear()
  }

  /**
   * Generate key for endpoint
   */
  private getKey(endpoint: string): string {
    // Include user identifier if available for per-user rate limiting
    const userKey = this.getUserIdentifier()
    return `${userKey}:${endpoint}`
  }

  /**
   * Get user identifier for rate limiting
   */
  private getUserIdentifier(): string {
    // Use IP address simulation or session ID
    return 'user-session' // In real app, this would be more sophisticated
  }
}

// Global rate limiter instance
export const globalRateLimiter = new RateLimiter()

/**
 * Rate limiting decorator for async functions
 */
export function rateLimit(config: Partial<RateLimitConfig> = {}) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value

    descriptor.value = async function (...args: any[]) {
      const endpoint = `${target.constructor.name}.${propertyKey}`
      const { allowed, retryAfter, reason } = globalRateLimiter.isAllowed(endpoint, config)

      if (!allowed) {
        const error = new Error(`Rate limit exceeded: ${reason}`)
        ;(error as any).retryAfter = retryAfter
        throw error
      }

      try {
        const result = await originalMethod.apply(this, args)
        globalRateLimiter.recordSuccess(endpoint)
        return result
      } catch (error) {
        globalRateLimiter.recordFailure(endpoint)
        throw error
      }
    }

    return descriptor
  }
}