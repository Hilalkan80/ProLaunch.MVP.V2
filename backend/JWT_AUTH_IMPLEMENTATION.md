# JWT Authentication System Implementation

## Overview

A comprehensive JWT-based authentication system has been implemented for the ProLaunch MVP backend. This system provides secure user authentication, authorization, and session management using PostgreSQL for persistent storage and Redis for token caching and session management.

## Key Features

### Security Features
- **BCrypt Password Hashing**: Industry-standard password hashing with configurable cost factor (12 rounds)
- **JWT Token Management**: Secure token generation and validation with RS256 algorithm support
- **Token Rotation**: Refresh token rotation for enhanced security
- **Token Blacklisting**: Immediate token invalidation capability
- **Rate Limiting**: Tier-based rate limiting for API protection
- **Account Lockout**: Automatic lockout after failed login attempts
- **Session Management**: Redis-based session tracking

### Authentication Features
- User registration with business profile
- Email/password login
- Token refresh with rotation
- Logout (single device and all devices)
- Password strength validation
- Email verification support
- Multi-factor authentication ready (MFA structure in place)

### Authorization Features
- Role-based access control via subscription tiers
- Milestone access control
- Protected route middleware
- Tier-based feature access
- Rate limiting by subscription level

## Architecture Components

### 1. Database Models (`backend/src/models/`)

#### User Model
- Core user information (email, password hash, profile)
- Business details (idea, target market, experience)
- Subscription management
- Security tracking (login attempts, lockout status)

#### Token Models
- RefreshToken: Tracks active refresh tokens with metadata
- TokenBlacklist: Stores revoked tokens for security

### 2. Security Module (`backend/src/core/security.py`)

#### PasswordManager
- Password hashing using BCrypt
- Password strength validation
- Secure password verification

#### JWTManager
- Access token generation (15-minute default expiry)
- Refresh token generation (7-day default expiry)
- Token decoding and validation
- JWT ID (jti) generation for blacklisting

#### SecurityUtils
- Secure random token generation
- Email hashing for privacy
- Constant-time string comparison
- Input sanitization

### 3. Authentication Service (`backend/src/services/auth_service.py`)

Core authentication operations:
- User registration with validation
- Login with security checks
- Token refresh with rotation
- Logout (single/all devices)
- Session management via Redis

### 4. API Endpoints (`backend/src/api/auth.py`)

#### Public Endpoints
- `POST /api/v1/auth/register` - New user registration
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/logout-all` - Logout from all devices
- `GET /api/v1/auth/verify` - Token verification

### 5. Authentication Middleware (`backend/src/core/dependencies.py`)

#### Dependencies
- `get_current_user` - Extract user from JWT token
- `get_current_active_user` - Verify user is active
- `get_verified_user` - Require email verification
- `require_subscription_tier` - Tier-based access control
- `require_milestone_access` - Milestone access validation
- `RateLimiter` - Request rate limiting

### 6. Error Handling (`backend/src/core/exceptions.py`)

Custom exception classes for:
- Authentication errors
- Authorization failures
- Validation errors
- Rate limiting
- Account issues
- Security violations

## Database Schema

### Users Table
```sql
- id (UUID, primary key)
- email (unique, indexed)
- password_hash
- business_idea
- subscription_tier (enum)
- is_active, is_verified
- login tracking fields
- timestamps
```

### Refresh Tokens Table
```sql
- id (UUID, primary key)
- token (unique, indexed)
- user_id (indexed)
- family_id (for rotation)
- device metadata
- expiration tracking
```

### Token Blacklist Table
```sql
- id (UUID, primary key)
- jti (unique, indexed)
- user_id
- expiration
- blacklist reason
```

## Security Best Practices Implemented

1. **Password Security**
   - BCrypt with high cost factor (12)
   - Strength requirements enforced
   - No password storage in plain text

2. **Token Security**
   - Short-lived access tokens (15 minutes)
   - Refresh token rotation
   - Token blacklisting capability
   - Unique JWT IDs for tracking

3. **Session Security**
   - Redis-based session management
   - Session validation on each request
   - Device tracking for sessions

4. **Account Security**
   - Automatic lockout after failed attempts
   - IP address tracking
   - Suspicious activity detection
   - Token reuse detection

5. **API Security**
   - Rate limiting by tier
   - CORS configuration
   - Input validation and sanitization
   - Comprehensive error handling

## Configuration

### Environment Variables Required
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/prolaunch
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=prolaunch

# JWT Settings
JWT_SECRET=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional
REDIS_DB=0
```

## Running Migrations

```bash
# Initialize Alembic (first time only)
cd backend
alembic init migrations

# Create a new migration
alembic revision --autogenerate -m "Initial auth tables"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

## Usage Examples

### 1. User Registration
```python
POST /api/v1/auth/register
{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "business_idea": "AI-powered analytics platform",
    "target_market": "Small businesses",
    "experience_level": "some-experience",
    "full_name": "John Doe",
    "company_name": "TechCorp"
}
```

### 2. User Login
```python
POST /api/v1/auth/login
{
    "email": "user@example.com",
    "password": "SecurePassword123!"
}
```

### 3. Protected Route Access
```python
GET /api/v1/protected/profile
Headers: {
    "Authorization": "Bearer <access_token>"
}
```

### 4. Token Refresh
```python
POST /api/v1/auth/refresh
{
    "refresh_token": "<refresh_token>"
}
```

## Testing the Implementation

### 1. Start the Backend
```bash
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Access API Documentation
Navigate to `http://localhost:8000/docs` for Swagger UI

### 3. Test Authentication Flow
1. Register a new user
2. Login with credentials
3. Use access token for protected routes
4. Refresh token when expired
5. Logout when done

## Monitoring and Maintenance

### Session Monitoring
- Active sessions stored in Redis
- Session expiry configurable
- Real-time session tracking

### Token Cleanup
- Expired tokens automatically cleaned
- Blacklist entries removed after natural expiry
- Database indexes for efficient queries

### Security Monitoring
- Failed login attempt tracking
- Account lockout monitoring
- Suspicious activity detection
- Token reuse detection

## Performance Considerations

### Database Optimization
- Indexes on frequently queried columns
- Composite indexes for complex queries
- UUID primary keys for distributed systems
- Connection pooling configured

### Redis Optimization
- Key expiry for automatic cleanup
- Efficient data structures
- Connection pooling
- Cluster support ready

### API Performance
- Async/await throughout
- Connection pooling
- Efficient query patterns
- Caching strategies

## Future Enhancements

1. **Email Verification**
   - Email sending service integration
   - Verification token generation
   - Verification workflow

2. **Multi-Factor Authentication**
   - TOTP support
   - SMS verification
   - Backup codes

3. **OAuth Integration**
   - Google OAuth
   - GitHub OAuth
   - Microsoft OAuth

4. **Advanced Security**
   - Device fingerprinting
   - Geolocation verification
   - Anomaly detection

5. **Audit Logging**
   - Comprehensive activity logs
   - Security event tracking
   - Compliance reporting

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check DATABASE_URL environment variable
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Redis Connection Failed**
   - Verify Redis is running
   - Check REDIS_HOST and REDIS_PORT
   - Test Redis connection separately

3. **Token Validation Failed**
   - Verify JWT_SECRET is set correctly
   - Check token expiry time
   - Ensure clock synchronization

4. **Migration Errors**
   - Check database permissions
   - Verify schema compatibility
   - Review migration scripts

## Support

For issues or questions about the authentication system:
1. Check the API documentation at `/docs`
2. Review error messages and logs
3. Consult the troubleshooting section
4. Check environment variable configuration