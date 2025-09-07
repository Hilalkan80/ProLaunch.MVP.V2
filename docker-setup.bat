@echo off
SETLOCAL ENABLEEXTENSIONS

echo Setting up Docker environment for ProLaunch...

REM Check if Docker is installed
docker -v >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Create required directories
echo Creating required directories...
mkdir docker\postgres\init 2>nul
mkdir docker\nginx\conf.d 2>nul
mkdir docker\nginx\ssl 2>nul
mkdir docker\elasticsearch\config 2>nul
mkdir docker\logstash\config 2>nul
mkdir docker\logstash\pipeline 2>nul
mkdir docker\kibana\config 2>nul
mkdir monitoring\prometheus 2>nul
mkdir monitoring\prometheus\rules 2>nul
mkdir monitoring\grafana\provisioning 2>nul

REM Copy environment file if it doesn't exist
IF NOT EXIST .env (
    echo Creating .env file from template...
    copy .env.docker .env
)

REM Create Docker network if it doesn't exist
echo Creating Docker network...
docker network create prolaunch-network 2>nul

REM Build and start services
echo Building and starting services...
docker-compose -f docker-compose.yml -f docker-compose.override.yml build
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to build services
    exit /b 1
)

echo Starting services...
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to start services
    exit /b 1
)

echo Waiting for services to be healthy...
timeout /t 30 /nobreak

REM Check service health
echo Checking service health...
docker-compose ps

echo Setup complete! Services are now running.
echo.
echo Access points:
echo - PostgreSQL: localhost:5432
echo - Redis: localhost:6379
echo - MinIO API: localhost:9000
echo - MinIO Console: localhost:9001
echo - Elasticsearch: localhost:9200
echo - Kibana: localhost:5601
echo - Nginx: localhost:80 (HTTP) / localhost:443 (HTTPS)
echo - pgAdmin: localhost:5050
echo - Redis Commander: localhost:8081
echo - MailHog: localhost:8025
echo.
echo Development Tools:
echo - Grafana: localhost:3000
echo - Prometheus: localhost:9090
echo - cAdvisor: localhost:8080
echo - Node Exporter: localhost:9100

ENDLOCAL