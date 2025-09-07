#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p .docker/data/postgres
mkdir -p .docker/data/redis
mkdir -p .docker/data/minio

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please update the environment variables in .env before continuing"
    exit 1
fi

# Build and start containers
echo "Building and starting containers..."
docker-compose up --build -d

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 10

# Initialize database
echo "Initializing database..."
docker-compose exec db psql -U prolaunch -d prolaunch -f /docker-entrypoint-initdb.d/init.sql

# Create MinIO buckets
echo "Creating MinIO buckets..."
docker-compose exec -e MINIO_ROOT_USER=prolaunch -e MINIO_ROOT_PASSWORD=prolaunch123 minio mc alias set myminio http://localhost:9000 prolaunch prolaunch123
docker-compose exec -e MINIO_ROOT_USER=prolaunch -e MINIO_ROOT_PASSWORD=prolaunch123 minio mc mb myminio/uploads
docker-compose exec -e MINIO_ROOT_USER=prolaunch -e MINIO_ROOT_PASSWORD=prolaunch123 minio mc policy set public myminio/uploads

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend && npm install
cd ..

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend && pip install -r requirements.txt
cd ..

echo "Development environment setup complete!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"