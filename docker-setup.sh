#!/bin/bash

set -e

echo "Setting up Docker environment for ProLaunch..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Create required directories
echo "Creating required directories..."
mkdir -p docker/postgres/init \
    docker/nginx/conf.d \
    docker/nginx/ssl \
    docker/elasticsearch/config \
    docker/logstash/config \
    docker/logstash/pipeline \
    docker/kibana/config \
    monitoring/prometheus \
    monitoring/prometheus/rules \
    monitoring/grafana/provisioning

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.docker .env
fi

# Create Docker network if it doesn't exist
echo "Creating Docker network..."
docker network create prolaunch-network 2>/dev/null || true

# Build and start services
echo "Building and starting services..."
if ! docker-compose -f docker-compose.yml -f docker-compose.override.yml build; then
    echo "Failed to build services"
    exit 1
fi

echo "Starting services..."
if ! docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d; then
    echo "Failed to start services"
    exit 1
fi

echo "Waiting for services to be healthy..."
sleep 30

# Check service health
echo "Checking service health..."
docker-compose ps

echo "Setup complete! Services are now running."
echo
echo "Access points:"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"
echo "- MinIO API: localhost:9000"
echo "- MinIO Console: localhost:9001"
echo "- Elasticsearch: localhost:9200"
echo "- Kibana: localhost:5601"
echo "- Nginx: localhost:80 (HTTP) / localhost:443 (HTTPS)"
echo "- pgAdmin: localhost:5050"
echo "- Redis Commander: localhost:8081"
echo "- MailHog: localhost:8025"
echo
echo "Development Tools:"
echo "- Grafana: localhost:3000"
echo "- Prometheus: localhost:9090"
echo "- cAdvisor: localhost:8080"
echo "- Node Exporter: localhost:9100"