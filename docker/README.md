# ProLaunch Docker Environment

This directory contains all Docker-related configurations for the ProLaunch application.

## Architecture Overview

The Docker environment includes the following services:

### Core Services
- **PostgreSQL 17** with pgvector extension for vector embeddings
- **Redis 7** for caching and session management
- **MinIO** for S3-compatible object storage
- **Nginx** as reverse proxy and load balancer

### ELK Stack
- **Elasticsearch** for search and analytics
- **Logstash** for log processing and ingestion
- **Kibana** for visualization and monitoring

### Development Tools (via docker-compose.override.yml)
- **pgAdmin** for PostgreSQL management
- **Redis Commander** for Redis management  
- **Mailhog** for email testing

### Production Monitoring (via docker-compose.prod.yml)
- **Prometheus** for metrics collection
- **Grafana** for metrics visualization
- **Node Exporter** for system metrics
- **cAdvisor** for container metrics

## Directory Structure

```
docker/
├── elasticsearch/
│   ├── Dockerfile
│   └── config/
│       └── elasticsearch.yml
├── kibana/
│   ├── Dockerfile
│   └── config/
│       └── kibana.yml
├── logstash/
│   ├── Dockerfile
│   ├── config/
│   │   └── logstash.yml
│   └── pipeline/
│       └── logstash.conf
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── conf.d/
│   │   └── default.conf
│   └── ssl/
├── postgres/
│   ├── Dockerfile
│   ├── postgresql.conf
│   └── init/
│       └── 02-init-database.sql
└── redis/
    └── redis.conf
```

## Getting Started

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- Make (optional, for using Makefile commands)
- At least 8GB RAM available for Docker

### Initial Setup

1. Copy the environment file:
```bash
cp .env.docker .env
```

2. Update the `.env` file with your configuration

3. Run the setup command:
```bash
make setup
```

4. Start the services:
```bash
make up
```

### Quick Start Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart [service-name]

# Access service shell
docker-compose exec [service-name] sh
```

## Service URLs

### Application Services
- Main Application: http://localhost
- API: http://localhost/api
- WebSocket: ws://localhost/ws

### Admin Interfaces
- Kibana: http://localhost:5601
- MinIO Console: http://localhost:9001
- pgAdmin: http://localhost:5050 (development only)
- Redis Commander: http://localhost:8081 (development only)
- Mailhog: http://localhost:8025 (development only)

### Monitoring (Production)
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Node Exporter: http://localhost:9100
- cAdvisor: http://localhost:8080

## Configuration

### Environment Variables

Key environment variables in `.env`:

```env
# Database
POSTGRES_DB=prolaunch
POSTGRES_USER=prolaunch_user
POSTGRES_PASSWORD=<secure-password>

# Redis
REDIS_PASSWORD=<secure-password>

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<secure-password>

# Elasticsearch
ELASTIC_PASSWORD=<secure-password>

# Kibana
KIBANA_ENCRYPTION_KEY=<32-character-string>
```

### SSL/TLS Configuration

For production, replace self-signed certificates in `docker/nginx/ssl/` with valid certificates:

1. Place your certificate files:
   - `nginx.crt` - SSL certificate
   - `nginx.key` - Private key

2. Update Nginx configuration if using custom certificate paths

### Resource Limits

Default resource limits are configured in docker-compose.yml:

- PostgreSQL: 2GB RAM, 2 CPUs
- Redis: 512MB RAM, 1 CPU
- MinIO: 1GB RAM, 2 CPUs
- Elasticsearch: 2GB RAM, 2 CPUs
- Logstash: 1GB RAM, 1 CPU
- Kibana: 1GB RAM, 1 CPU
- Nginx: 512MB RAM, 1 CPU

Adjust these based on your requirements in the deploy section.

## Development Workflow

### Database Management

```bash
# Connect to PostgreSQL
make shell-postgres

# Reset database
make reset-db

# Create backup
make backup

# Restore from backup
make restore
```

### Debugging

```bash
# View logs for specific service
make logs-[service-name]

# Check service health
make health

# Access service shell
make shell-[service-name]
```

### Testing Email

Mailhog captures all outgoing emails in development:
1. Configure your app to use SMTP host: `mailhog` port: `1025`
2. View captured emails at http://localhost:8025

## Production Deployment

### Using Production Configuration

```bash
# Start with production settings
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or use Make command
make prod
```

### Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Enable SSL/TLS for all services
- [ ] Configure firewall rules
- [ ] Set up backup automation
- [ ] Enable authentication for admin interfaces
- [ ] Review and adjust resource limits
- [ ] Set up monitoring alerts
- [ ] Configure log retention policies

### Monitoring Setup

1. Access Grafana at http://localhost:3000
2. Default credentials: admin/admin (change immediately)
3. Add Prometheus data source: http://prometheus:9090
4. Import dashboards for:
   - Docker containers
   - PostgreSQL
   - Redis
   - Elasticsearch
   - Nginx

## Maintenance

### Backup and Restore

```bash
# Create backup
make backup

# Restore from specific date
make restore
# Enter date when prompted (YYYYMMDD format)
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Rebuild custom images
make build

# Apply updates
make restart
```

### Cleanup

```bash
# Remove stopped containers
docker system prune

# Remove all volumes (WARNING: deletes data)
make clean

# Complete reset
make reset
```

## Troubleshooting

### Common Issues

**Services not starting:**
- Check logs: `docker-compose logs [service-name]`
- Verify port availability: `netstat -tulpn | grep [port]`
- Check resource availability: `docker system df`

**Permission errors:**
- Ensure proper file permissions in mounted volumes
- Check Docker daemon permissions

**Connection refused:**
- Verify service is running: `docker-compose ps`
- Check network configuration
- Verify firewall rules

**Out of memory:**
- Adjust resource limits in docker-compose.yml
- Check system resources: `free -h`
- Clear unused resources: `docker system prune`

### Health Checks

All services include health checks. View status:

```bash
docker-compose ps
make health
```

### Debug Mode

Enable debug logging by setting in `.env`:
```env
APP_DEBUG=true
```

## Performance Tuning

### PostgreSQL
- Adjust `shared_buffers` and `effective_cache_size` in postgresql.conf
- Configure connection pooling
- Optimize queries using EXPLAIN ANALYZE

### Redis
- Configure maxmemory policy
- Enable persistence based on needs
- Use Redis Cluster for high availability

### Elasticsearch
- Adjust heap size: `ES_JAVA_OPTS`
- Configure number of shards and replicas
- Implement proper index lifecycle management

### Nginx
- Tune worker processes and connections
- Configure caching strategies
- Enable compression for static assets

## Support

For issues or questions:
1. Check the logs: `make logs`
2. Review this documentation
3. Check service health: `make health`
4. Consult service-specific documentation

## License

Copyright (c) 2024 ProLaunch. All rights reserved.