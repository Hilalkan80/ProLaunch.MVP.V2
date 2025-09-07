.PHONY: help test test-backend test-frontend test-e2e setup clean

help:
	@echo "Available commands:"
	@echo "  make setup          - Set up the complete environment"
	@echo "  make test          - Run all tests"
	@echo "  make test-backend  - Run backend tests"
	@echo "  make test-frontend - Run frontend tests"
	@echo "  make test-e2e      - Run E2E tests"
	@echo "  make clean         - Clean up containers and volumes"

setup:
	docker-compose build
	docker-compose up -d postgres redis
	sleep 5  # Wait for services
	docker-compose run --rm backend alembic upgrade head
	docker-compose run --rm test_runner alembic upgrade head

test: test-backend test-frontend

test-backend:
	@echo "Running backend tests..."
	docker-compose run --rm test_runner pytest tests/ -v --cov=src --cov-report=term-missing

test-backend-watch:
	@echo "Running backend tests in watch mode..."
	docker-compose run --rm test_runner pytest-watch tests/

test-frontend:
	@echo "Running frontend tests..."
	docker-compose run --rm frontend npm test

test-e2e:
	@echo "Running E2E tests..."
	docker-compose up -d
	docker-compose run --rm frontend npx playwright test

test-auth:
	@echo "Running authentication tests only..."
	docker-compose run --rm test_runner pytest tests/auth/ -v

clean:
	docker-compose down -v
	docker system prune -f