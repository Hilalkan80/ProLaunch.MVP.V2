# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Environment
```bash
# Quick setup with automated script
./scripts/setup-dev-env.sh

# Manual development setup
cp .env.example .env
make up ENV=dev

# Show container status
make ps

# View logs
make logs

# Clean environment
make clean
```

### Testing
```bash
# Frontend Tests
npm run test:unit
npm run test:security
npm run test:integration
npm run test:coverage

# Backend Tests
pytest tests/unit/ -v --cov=src
pytest tests/integration/ -v
pytest tests/security/ -v -m security
```

## Architecture Overview

ProLaunch MVP is a multi-tier SaaS platform with:

### Backend (FastAPI + PostgreSQL)
- FastAPI with async support and Python 3.11
- PostgreSQL 17 with pgvector for vector storage
- Redis 7 for caching and real-time updates
- LlamaIndex integration for AI capabilities

### Frontend (Next.js)
- Next.js 14 with React 18 and TypeScript
- Chakra UI component library
- WebSocket integration for real-time updates
- Role-based access control

### Development Notes
- Development uses Docker Compose with hot-reload
- Strict testing requirements (70% coverage minimum, 85% for auth)
- Security scanning integrated into CI/CD pipeline
- Multi-tenant architecture with subscription management