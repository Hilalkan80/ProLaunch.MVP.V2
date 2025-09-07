# ProLaunch MVP

A conversational AI-powered business launch platform that guides entrepreneurs through milestone-based business development using FastAPI, Next.js, and advanced AI orchestration.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Local Development Setup

1. **Clone and setup environment**:
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Update .env with your API keys and configuration
   # At minimum, add your OPENAI_API_KEY
   ```

2. **Run the setup script**:
   ```bash
   chmod +x scripts/setup-dev-env.sh
   ./scripts/setup-dev-env.sh
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001

### Manual Setup (if script fails)

```bash
# Build and start services
docker-compose up --build -d

# Wait for services to be ready (check logs)
docker-compose logs -f

# Access the application at http://localhost:3000
```

## Architecture Overview

### Technology Stack
- **Backend**: FastAPI (Python 3.11) with async support
- **Frontend**: Next.js 14 with React 18 and TypeScript
- **Database**: PostgreSQL 17 with pgvector extension
- **Cache**: Redis 7 with persistence
- **AI**: LlamaIndex integration with OpenAI
- **Storage**: MinIO (S3-compatible) for local development

### Key Features
- **Milestone-based progression**: M0-M5 structured business development
- **AI-powered conversations**: Context-aware chat with document generation
- **Vector search**: Semantic search across chat history and suppliers
- **Real-time updates**: WebSocket integration for live chat
- **Multi-tenancy**: User isolation with subscription tiers

## Project Structure

```
ProLaunch.MVP.V2/
├── backend/                    # FastAPI application
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # Next.js application
│   ├── Dockerfile
│   └── package.json
├── db/                        # Database scripts
│   └── init.sql               # Schema initialization
├── scripts/                   # Utility scripts
│   ├── setup-dev-env.sh      # Development environment setup
│   └── backup-db.sh          # Database backup utility
├── .github/workflows/         # CI/CD pipelines
│   ├── ci-cd.yml             # Main CI/CD pipeline
│   └── security-scan.yml     # Security scanning
├── docker-compose.yml         # Development environment
├── docker-compose.prod.yml    # Production environment
├── .env.example              # Environment template
├── .env.production           # Production environment template
└── .env.staging              # Staging environment template
```

## Development

### Environment Variables

Copy `.env.example` to `.env` and update the following required variables:

```bash
# Required for AI functionality
OPENAI_API_KEY=your_openai_api_key_here

# Security (generate secure values for production)
SECRET_KEY=your_very_secure_secret_key_here
NEXTAUTH_SECRET=your_nextauth_secret_key_here

# Database (defaults work for development)
DB_PASSWORD=dev_password_123
REDIS_PASSWORD=dev_redis_123
```

### Database Schema

The application uses PostgreSQL with pgvector extension for:
- User management and authentication
- Milestone progress tracking
- Chat sessions and message history
- Document generation and storage
- Semantic search capabilities
- Supplier database for marketplace features

Key tables:
- `users` - User accounts and subscription info
- `milestones` - Business development milestones (M0-M5)
- `user_milestone_progress` - Individual progress tracking
- `chat_sessions` & `chat_messages` - AI conversation history
- `generated_documents` - AI-generated business documents
- `suppliers` - Marketplace supplier database

### API Endpoints

The FastAPI backend provides:
- `/auth/*` - Authentication and user management
- `/chat/*` - AI conversation endpoints
- `/milestones/*` - Milestone management
- `/documents/*` - Document generation and retrieval
- `/suppliers/*` - Supplier search and management
- `/health` - Health check endpoint
- `/docs` - Interactive API documentation

### Frontend Architecture

The Next.js frontend features:
- **Chat-first UI**: Primary interaction through conversational interface
- **Milestone dashboard**: Progress tracking and navigation
- **Document viewer**: Generated business documents
- **Supplier marketplace**: Search and connect with service providers
- **Real-time updates**: WebSocket integration for live chat

## Deployment

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Staging/Production Deployment

1. **Environment Setup**:
   ```bash
   # Copy production environment template
   cp .env.production .env
   # Update with production values
   ```

2. **Deploy with production compose**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **CI/CD Pipeline**:
   - GitHub Actions automatically builds and deploys
   - Security scanning on every push
   - Manual deployment workflow for production

### Database Management

```bash
# Create backup
./scripts/backup-db.sh

# Reset database (development only)
docker-compose down -v
docker-compose up -d
```

## Security Features

- **Authentication**: JWT-based authentication with secure session management
- **Authorization**: Role-based access control with subscription tiers
- **Data encryption**: AES-256 encryption for sensitive data
- **API security**: Rate limiting, CORS configuration, input validation
- **Container security**: Non-root user execution, minimal attack surface
- **Dependency scanning**: Automated vulnerability scanning in CI/CD

## Monitoring and Observability

- **Health checks**: Built-in health endpoints for all services
- **Logging**: Structured logging with configurable levels
- **Error tracking**: Sentry integration for error monitoring
- **Performance monitoring**: API response time and database query tracking
- **Security monitoring**: Automated vulnerability scanning

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and security checks
5. Submit a pull request

### Code Quality

The project includes automated checks for:
- Code formatting (Black, Prettier)
- Linting (Flake8, ESLint)
- Type checking (MyPy, TypeScript)
- Security scanning (Bandit, npm audit)
- Test coverage requirements

## License

This project is proprietary and confidential. All rights reserved.

## Support

For technical support or questions:
- Review the API documentation at http://localhost:8000/docs
- Check the logs: `docker-compose logs -f`
- Ensure all environment variables are properly configured
- Verify all services are healthy: `docker-compose ps`