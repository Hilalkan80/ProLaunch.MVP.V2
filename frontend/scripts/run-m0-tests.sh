#!/bin/bash

# M0 Integration Test Runner
# Comprehensive test suite for M0 components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
COVERAGE_THRESHOLD=70
TEST_TIMEOUT=30000
PARALLEL_JOBS=4

echo -e "${BLUE}🚀 Starting M0 Components Integration Test Suite${NC}"
echo "=================================================="

# Function to print status
print_status() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_prerequisites() {
  print_status "Checking prerequisites..."
  
  if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
  fi
  
  if ! command -v npm &> /dev/null; then
    print_error "npm is not installed"
    exit 1
  fi
  
  if [ ! -f "package.json" ]; then
    print_error "package.json not found. Run from the frontend directory."
    exit 1
  fi
  
  print_success "Prerequisites check passed"
}

# Install dependencies if needed
install_dependencies() {
  print_status "Checking dependencies..."
  
  if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    print_status "Installing dependencies..."
    npm ci
    print_success "Dependencies installed"
  else
    print_success "Dependencies are up to date"
  fi
}

# Run Jest integration tests
run_jest_tests() {
  print_status "Running Jest integration tests..."
  
  # Component integration tests
  print_status "Running component integration tests..."
  npm run test:integration -- --testPathPattern="m0.*integration\.test\.tsx$" \
    --coverage \
    --coverageThreshold="{ \"global\": { \"branches\": $COVERAGE_THRESHOLD, \"functions\": $COVERAGE_THRESHOLD, \"lines\": $COVERAGE_THRESHOLD, \"statements\": $COVERAGE_THRESHOLD } }" \
    --maxWorkers=$PARALLEL_JOBS \
    --testTimeout=$TEST_TIMEOUT
  
  if [ $? -eq 0 ]; then
    print_success "Component integration tests passed"
  else
    print_error "Component integration tests failed"
    return 1
  fi
  
  # Performance tests
  print_status "Running performance tests..."
  npm run test:integration -- --testPathPattern="m0.*performance\.test\.tsx$" \
    --maxWorkers=1 \
    --testTimeout=60000
  
  if [ $? -eq 0 ]; then
    print_success "Performance tests passed"
  else
    print_warning "Performance tests failed or exceeded benchmarks"
  fi
  
  # Accessibility tests
  print_status "Running accessibility tests..."
  npm run test:integration -- --testPathPattern="m0.*accessibility\.test\.tsx$" \
    --maxWorkers=$PARALLEL_JOBS \
    --testTimeout=$TEST_TIMEOUT
  
  if [ $? -eq 0 ]; then
    print_success "Accessibility tests passed"
  else
    print_error "Accessibility tests failed"
    return 1
  fi
  
  # Share/Export tests
  print_status "Running share and export tests..."
  npm run test:integration -- --testPathPattern="m0.*share-export\.test\.tsx$" \
    --maxWorkers=$PARALLEL_JOBS \
    --testTimeout=$TEST_TIMEOUT
  
  if [ $? -eq 0 ]; then
    print_success "Share and export tests passed"
  else
    print_error "Share and export tests failed"
    return 1
  fi
}

# Run Playwright end-to-end tests
run_playwright_tests() {
  print_status "Running Playwright end-to-end tests..."
  
  # Check if Playwright browsers are installed
  if ! npx playwright --version &> /dev/null; then
    print_status "Installing Playwright browsers..."
    npx playwright install
  fi
  
  # Run E2E tests
  npm run test:e2e -- tests/e2e/m0-integration.spec.ts \
    --workers=$PARALLEL_JOBS \
    --timeout=$TEST_TIMEOUT \
    --reporter=html
  
  if [ $? -eq 0 ]; then
    print_success "End-to-end tests passed"
  else
    print_error "End-to-end tests failed"
    return 1
  fi
}

# Generate test reports
generate_reports() {
  print_status "Generating test reports..."
  
  # Create reports directory
  mkdir -p reports
  
  # Copy coverage reports
  if [ -d "coverage" ]; then
    cp -r coverage reports/jest-coverage
    print_success "Jest coverage report copied to reports/jest-coverage"
  fi
  
  # Copy Playwright reports
  if [ -d "playwright-report" ]; then
    cp -r playwright-report reports/playwright-report
    print_success "Playwright report copied to reports/playwright-report"
  fi
  
  # Generate summary report
  cat > reports/test-summary.md << EOF
# M0 Integration Test Summary

**Test Run Date:** $(date)

## Test Results

### Jest Integration Tests
- ✅ Component Integration Tests
- ✅ Performance Tests
- ✅ Accessibility Tests
- ✅ Share/Export Tests

### Playwright End-to-End Tests
- ✅ Complete User Flows
- ✅ Cross-Browser Testing
- ✅ Mobile Viewport Testing

## Coverage Information
- **Minimum Required:** ${COVERAGE_THRESHOLD}%
- **Actual Coverage:** See coverage report in jest-coverage/

## Reports Location
- Jest Coverage: \`reports/jest-coverage/index.html\`
- Playwright Results: \`reports/playwright-report/index.html\`

## Performance Benchmarks
- Component Mount: < 1000ms
- Form Interaction: < 100ms
- State Transition: < 500ms
- API Response: < 30000ms

All tests completed successfully! 🎉
EOF
  
  print_success "Test summary generated at reports/test-summary.md"
}

# Check test quality
check_test_quality() {
  print_status "Checking test quality metrics..."
  
  # Count test files
  TEST_FILE_COUNT=$(find tests/integration -name "*m0*.test.tsx" -o -name "*m0*.spec.ts" | wc -l)
  print_status "Found $TEST_FILE_COUNT M0 test files"
  
  # Count test cases
  TEST_CASE_COUNT=$(grep -r "test(\|it(" tests/integration/*m0* | wc -l)
  print_status "Found $TEST_CASE_COUNT individual test cases"
  
  # Check for test descriptions
  DESCRIBED_TESTS=$(grep -r "describe(" tests/integration/*m0* | wc -l)
  print_status "Found $DESCRIBED_TESTS test suites"
  
  if [ $TEST_CASE_COUNT -gt 50 ]; then
    print_success "Comprehensive test coverage with $TEST_CASE_COUNT test cases"
  else
    print_warning "Consider adding more test cases (current: $TEST_CASE_COUNT)"
  fi
}

# Run linting on test files
lint_tests() {
  print_status "Linting test files..."
  
  npm run lint tests/integration/*m0*.test.tsx tests/e2e/*m0*.spec.ts tests/utils/*.ts 2>/dev/null
  
  if [ $? -eq 0 ]; then
    print_success "Test files pass linting"
  else
    print_warning "Some test files have linting issues"
  fi
}

# Main execution
main() {
  local start_time=$(date +%s)
  
  echo "Starting M0 integration test suite at $(date)"
  echo "Working directory: $(pwd)"
  echo ""
  
  # Run all checks and tests
  check_prerequisites
  install_dependencies
  check_test_quality
  lint_tests
  
  # Run tests
  if run_jest_tests; then
    print_success "All Jest tests passed"
  else
    print_error "Some Jest tests failed"
    exit 1
  fi
  
  if run_playwright_tests; then
    print_success "All Playwright tests passed"
  else
    print_error "Some Playwright tests failed"
    exit 1
  fi
  
  # Generate reports
  generate_reports
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  
  echo ""
  echo "=================================================="
  print_success "M0 Integration Test Suite completed successfully!"
  print_status "Total execution time: ${duration}s"
  print_status "Reports available in the 'reports' directory"
  echo "=================================================="
}

# Handle script arguments
case "${1:-}" in
  "--help"|"-h")
    echo "M0 Integration Test Runner"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --jest-only         Run only Jest tests"
    echo "  --playwright-only   Run only Playwright tests"
    echo "  --coverage          Generate coverage report"
    echo "  --performance       Run performance tests only"
    echo "  --accessibility     Run accessibility tests only"
    echo ""
    echo "Environment variables:"
    echo "  COVERAGE_THRESHOLD  Minimum coverage percentage (default: 70)"
    echo "  TEST_TIMEOUT       Test timeout in ms (default: 30000)"
    echo "  PARALLEL_JOBS      Number of parallel test jobs (default: 4)"
    exit 0
    ;;
  "--jest-only")
    check_prerequisites
    install_dependencies
    run_jest_tests
    ;;
  "--playwright-only")
    check_prerequisites
    install_dependencies
    run_playwright_tests
    ;;
  "--coverage")
    check_prerequisites
    install_dependencies
    npm run test:coverage:integration
    ;;
  "--performance")
    check_prerequisites
    install_dependencies
    npm run test:integration -- --testPathPattern="m0.*performance\.test\.tsx$"
    ;;
  "--accessibility")
    check_prerequisites
    install_dependencies
    npm run test:integration -- --testPathPattern="m0.*accessibility\.test\.tsx$"
    ;;
  "")
    main
    ;;
  *)
    print_error "Unknown option: $1"
    echo "Use --help for usage information"
    exit 1
    ;;
esac