# Test Execution Guide

## Overview

This guide provides comprehensive instructions for executing the test suites created for the ProLaunch MVP v2 system, covering LlamaIndex integration, Prompt Template System, Citation Tracking, and UI components.

## Test Structure

The test suite is organized into the following categories:

### Backend Tests
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and workflows  
- **End-to-End Tests**: Test complete user workflows across the system
- **Performance Tests**: Test system performance under load

### Frontend Tests
- **Component Tests**: Test React components and UI interactions
- **Integration Tests**: Test component integration and state management
- **Accessibility Tests**: Test WCAG compliance and screen reader support

## Prerequisites

### Backend Testing Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install pytest pytest-asyncio pytest-cov pytest-mock
   pip install -r requirements-test.txt
   ```

2. **Environment Configuration**
   ```bash
   # Copy test environment template
   cp .env.test.example .env.test
   
   # Set required test environment variables
   export TESTING=true
   export DATABASE_URL=sqlite:///./test.db
   export REDIS_URL=redis://localhost:6379/1
   ```

3. **Test Database Setup**
   ```bash
   # Create test database
   python -m pytest --setup-only
   ```

### Frontend Testing Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   npm install --save-dev @testing-library/react @testing-library/jest-dom
   npm install --save-dev @testing-library/user-event vitest jsdom
   ```

2. **Test Configuration**
   ```bash
   # Ensure test configuration is properly set in vitest.config.ts
   # and jest.config.js (if using Jest)
   ```

## Test Execution Commands

### Backend Tests

#### Unit Tests

**LlamaIndex and AI Client Setup**
```bash
# Test LlamaIndex configuration
python -m pytest backend/tests/unit/test_llama_config.py -v

# Test LlamaIndex service
python -m pytest backend/tests/unit/test_llama_service.py -v

# Run all LlamaIndex unit tests
python -m pytest backend/tests/unit/ -k "llama" -v
```

**Prompt Template System**
```bash
# Test prompt loader functionality
python -m pytest backend/tests/unit/test_prompt_loader.py -v

# Test token budget optimization
python -m pytest backend/tests/unit/test_prompt_loader.py::TestTokenBudgetOptimization -v

# Test prompt validation
python -m pytest backend/tests/unit/test_prompt_loader.py::TestPromptValidation -v
```

**Citation Tracking Backend**
```bash
# Test basic citation service
python -m pytest backend/tests/unit/test_citation_service.py -v

# Test extended citation functionality  
python -m pytest backend/tests/unit/test_citation_service_extended.py -v

# Test citation workflow edge cases
python -m pytest backend/tests/unit/test_citation_service_extended.py::TestAdvancedCitationOperations -v
```

#### Integration Tests

**LlamaIndex Service Integration**
```bash
# Test complete LlamaIndex workflow
python -m pytest backend/tests/integration/test_llama_integration.py -v

# Test document processing integration
python -m pytest backend/tests/integration/test_llama_integration.py::TestLlamaIndexIntegration::test_complete_document_workflow -v
```

**Prompt Loader MCP Integration**
```bash
# Test prompt loader with MCP services
python -m pytest backend/tests/integration/test_prompt_loader_integration.py -v

# Test context injection workflow
python -m pytest backend/tests/integration/test_prompt_loader_integration.py::TestPromptLoaderMCPIntegration::test_context_injection_workflow -v
```

**Citation System Integration**
```bash
# Test citation system integration
python -m pytest backend/tests/integration/test_citation_integration.py -v

# Test citation lifecycle
python -m pytest backend/tests/integration/test_citation_integration.py::TestCitationWorkflowIntegration::test_complete_citation_lifecycle -v
```

#### End-to-End Tests

**Citation Workflow E2E**
```bash
# Test complete citation workflow via API
python -m pytest backend/tests/e2e/test_citation_workflow.py -v

# Test citation verification recovery
python -m pytest backend/tests/e2e/test_citation_workflow.py::TestCitationWorkflowE2E::test_citation_verification_failure_recovery -v
```

**AI Integration Workflow E2E**
```bash
# Test AI content generation with citations
python -m pytest backend/tests/e2e/test_ai_integration_workflow.py -v

# Test prompt chain workflow
python -m pytest backend/tests/e2e/test_ai_integration_workflow.py::TestAIContentGenerationWorkflow::test_prompt_chain_workflow_with_ai_generation -v
```

#### Performance Tests

**AI Services Performance**
```bash
# Test LlamaIndex performance
python -m pytest backend/tests/performance/test_ai_services_performance.py::TestLlamaIndexPerformance -v -s

# Test Prompt Loader performance
python -m pytest backend/tests/performance/test_ai_services_performance.py::TestPromptLoaderPerformance -v -s

# Test Citation Service performance
python -m pytest backend/tests/performance/test_ai_services_performance.py::TestCitationServicePerformance -v -s
```

### Frontend Tests

#### Component Tests

**Citation UI Components**
```bash
# Test Citation Card component
npm run test frontend/src/components/citations/__tests__/CitationCard.test.tsx

# Test Citation List component
npm run test frontend/src/components/citations/__tests__/CitationList.test.tsx

# Test Citation Form component
npm run test frontend/src/components/citations/__tests__/CitationForm.test.tsx
```

#### Run All Frontend Tests
```bash
# Run all frontend tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## Comprehensive Test Execution

### Run All Tests
```bash
# Backend: Run all tests with coverage
cd backend
python -m pytest --cov=src --cov-report=html --cov-report=term-missing -v

# Frontend: Run all tests with coverage
cd frontend
npm run test:coverage
```

### Parallel Test Execution
```bash
# Backend: Run tests in parallel
python -m pytest -n auto --dist=worksteal

# With specific number of workers
python -m pytest -n 4
```

### Test Categories by Priority

#### Critical Path Tests (Run First)
```bash
# Core functionality tests
python -m pytest backend/tests/unit/test_citation_service.py::TestCitationService::test_create_citation_success -v
python -m pytest backend/tests/unit/test_llama_service.py::TestLlamaIndexService::test_initialization_success -v
python -m pytest backend/tests/unit/test_prompt_loader.py::TestPromptLoading::test_load_prompt_basic -v
```

#### Integration Tests (Run Second)
```bash
# Key integration workflows
python -m pytest backend/tests/integration/ -k "test_complete" -v
```

#### Performance Tests (Run Last)
```bash
# Performance validation
python -m pytest backend/tests/performance/ -v -s --tb=short
```

## Test Data and Fixtures

### Test Data Setup

The tests use various fixtures for consistent test data:

- **Citations**: Sample citations with different source types, verification statuses, and quality scores
- **Prompts**: Test prompt templates with varying sizes and complexity
- **Users**: Test user accounts with different roles and permissions
- **AI Content**: Mock AI-generated content for integration testing

### Mock Services

Tests use mocked external services:

- **LlamaIndex**: Mocked LLM and embedding services
- **MCP Services**: Mocked Memory Bank, Ref, and TokenOptimizer services
- **External APIs**: Mocked verification and validation services
- **Database**: In-memory SQLite for isolated testing

## Test Environment Configuration

### Environment Variables

Required environment variables for testing:

```bash
# Backend Testing
export TESTING=true
export DATABASE_URL=sqlite:///./test.db
export REDIS_URL=redis://localhost:6379/1
export ANTHROPIC_API_KEY=test_anthropic_key
export OPENAI_API_KEY=test_openai_key

# Frontend Testing
export NODE_ENV=test
export NEXT_PUBLIC_API_URL=http://localhost:3001
```

### Database Configuration

Test database setup for different test types:

```python
# Unit Tests: In-memory SQLite
engine = create_engine("sqlite:///:memory:")

# Integration Tests: Temporary SQLite file  
engine = create_engine("sqlite:///./test_integration.db")

# E2E Tests: PostgreSQL test database
engine = create_engine("postgresql://test_user:test_pass@localhost/test_db")
```

## Continuous Integration

### GitHub Actions Configuration

The test suite integrates with CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          cd backend
          python -m pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm run test:coverage
```

### Pre-commit Hooks

Automated test execution on commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest backend/tests/unit/ --tb=short
        language: python
        pass_filenames: false
        always_run: true
```

## Test Coverage Requirements

### Backend Coverage Targets
- **Unit Tests**: Minimum 85% line coverage
- **Integration Tests**: Minimum 70% workflow coverage
- **Critical Components**: Minimum 90% coverage
  - Citation Service
  - LlamaIndex Service  
  - Prompt Loader

### Frontend Coverage Targets
- **Component Tests**: Minimum 80% component coverage
- **Integration Tests**: Minimum 60% user workflow coverage
- **Critical UI Components**: Minimum 85% coverage
  - Citation management components
  - Form components with validation

## Test Reporting

### Coverage Reports

Generate detailed coverage reports:

```bash
# Backend HTML coverage report
python -m pytest --cov=src --cov-report=html
# Report available at htmlcov/index.html

# Frontend coverage report
npm run test:coverage
# Report available at coverage/lcov-report/index.html
```

### Performance Test Reports

Performance tests generate metrics reports:

```python
# Example performance metrics output
{
    "test_name": "document_indexing",
    "total_operations": 5,
    "average_time": 0.245,
    "throughput_ops_per_sec": 20.4,
    "error_rate": 0.0
}
```

### Test Result Aggregation

Combine test results across all test types:

```bash
# Generate comprehensive test report
python scripts/generate_test_report.py --output=test_results.json
```

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Reset test database
python -m pytest --setup-only --reset-db

# Check database permissions
ls -la test.db
```

**Import Errors**
```bash
# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Check dependencies
pip check
```

**Mock Service Issues**
```bash
# Restart Redis (if using external Redis)
sudo service redis-server restart

# Clear test cache
python -m pytest --cache-clear
```

**Frontend Test Issues**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Reset test database
npm run test:setup
```

### Debug Mode

Run tests in debug mode for troubleshooting:

```bash
# Backend debug mode
python -m pytest -v -s --pdb backend/tests/unit/test_citation_service.py::test_failing_function

# Frontend debug mode with detailed output
npm run test -- --verbose --no-coverage
```

### Performance Debugging

Profile test performance:

```bash
# Profile test execution
python -m pytest --profile backend/tests/performance/

# Memory usage profiling
python -m pytest --memprof backend/tests/integration/
```

## Test Maintenance

### Regular Maintenance Tasks

1. **Update Test Data**: Refresh sample data and fixtures monthly
2. **Review Coverage**: Analyze coverage reports and add tests for uncovered code
3. **Performance Baselines**: Update performance benchmarks quarterly
4. **Mock Updates**: Update mocked services when external APIs change
5. **Dependency Updates**: Keep testing dependencies current

### Test Documentation

Keep test documentation current:

- Update this guide when adding new test suites
- Document new test patterns and conventions
- Maintain examples of complex test scenarios
- Update troubleshooting section based on common issues

## Success Criteria

Tests are considered successful when:

1. **All unit tests pass** with required coverage
2. **Integration tests pass** without flakiness
3. **E2E tests pass** end-to-end workflows  
4. **Performance tests meet** established benchmarks
5. **No regression** in existing functionality
6. **Code quality gates** are satisfied

This comprehensive test suite ensures the reliability, performance, and maintainability of the ProLaunch MVP v2 system across all components and integration points.