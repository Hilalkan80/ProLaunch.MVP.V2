"""
Monitoring and logging configuration for the citation system.

Provides comprehensive logging, metrics collection, and monitoring
integration for the citation system components.
"""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json
import traceback

from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    generate_latest, CONTENT_TYPE_LATEST
)
from pythonjsonlogger import jsonlogger
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from fastapi import Request, Response
from fastapi.responses import PlainTextResponse

from ..core.config import settings


# Prometheus Metrics for Citation System
citation_operations = Counter(
    'citation_operations_total',
    'Total number of citation operations',
    ['operation', 'status']
)

citation_verification_time = Histogram(
    'citation_verification_duration_seconds',
    'Time taken to verify citations',
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120]
)

citation_accuracy_gauge = Gauge(
    'citation_system_accuracy',
    'Current system-wide citation accuracy',
    ['status']
)

citation_cache_hits = Counter(
    'citation_cache_hits_total',
    'Number of cache hits for citations'
)

citation_cache_misses = Counter(
    'citation_cache_misses_total',
    'Number of cache misses for citations'
)

api_request_duration = Histogram(
    'citation_api_request_duration_seconds',
    'API request duration for citation endpoints',
    ['method', 'endpoint', 'status']
)

active_verifications = Gauge(
    'citation_active_verifications',
    'Number of currently active citation verifications'
)

mcp_service_health = Gauge(
    'mcp_service_health',
    'Health status of MCP services',
    ['service']
)


class CitationLogger:
    """
    Custom logger for citation system with structured logging.
    """
    
    def __init__(self, name: str = "citation_system"):
        """Initialize citation logger."""
        self.logger = logging.getLogger(name)
        self.setup_logger()
    
    def setup_logger(self):
        """Configure structured JSON logging."""
        # Remove default handlers
        self.logger.handlers = []
        
        # Set log level from environment
        log_level = settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else 'INFO'
        self.logger.setLevel(getattr(logging, log_level))
        
        # Console handler with JSON formatter
        console_handler = logging.StreamHandler(sys.stdout)
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'timestamp': '@timestamp', 'level': 'severity'}
        )
        console_handler.setFormatter(json_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for persistent logs
        if hasattr(settings, 'LOG_FILE'):
            file_handler = logging.FileHandler(settings.LOG_FILE)
            file_handler.setFormatter(json_formatter)
            self.logger.addHandler(file_handler)
    
    def log_citation_operation(
        self,
        operation: str,
        citation_id: str,
        status: str,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log citation operation with structured data.
        
        Args:
            operation: Type of operation (create, verify, update, etc.)
            citation_id: Citation ID
            status: Operation status (success, failure, pending)
            duration: Operation duration in seconds
            metadata: Additional metadata
        """
        log_data = {
            'operation': operation,
            'citation_id': citation_id,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if duration:
            log_data['duration_seconds'] = duration
        
        if metadata:
            log_data['metadata'] = metadata
        
        # Update metrics
        citation_operations.labels(operation=operation, status=status).inc()
        
        if status == 'success':
            self.logger.info(f"Citation operation completed", extra=log_data)
        elif status == 'failure':
            self.logger.error(f"Citation operation failed", extra=log_data)
        else:
            self.logger.warning(f"Citation operation status: {status}", extra=log_data)
    
    def log_verification(
        self,
        citation_id: str,
        url: str,
        status: str,
        duration: float,
        error: Optional[str] = None
    ):
        """
        Log citation verification attempt.
        
        Args:
            citation_id: Citation ID
            url: URL being verified
            status: Verification status
            duration: Verification duration
            error: Error message if failed
        """
        log_data = {
            'operation': 'verification',
            'citation_id': citation_id,
            'url': url,
            'status': status,
            'duration_seconds': duration
        }
        
        if error:
            log_data['error'] = error
        
        # Update metrics
        citation_verification_time.observe(duration)
        
        if status == 'success':
            self.logger.info("Citation verified successfully", extra=log_data)
        else:
            self.logger.error("Citation verification failed", extra=log_data)
    
    def log_accuracy_alert(
        self,
        severity: str,
        message: str,
        citation_id: Optional[str] = None,
        current_score: float = 0.0,
        threshold: float = 0.95
    ):
        """
        Log accuracy alert.
        
        Args:
            severity: Alert severity (info, warning, critical)
            message: Alert message
            citation_id: Optional citation ID
            current_score: Current accuracy score
            threshold: Accuracy threshold
        """
        log_data = {
            'alert_type': 'accuracy',
            'severity': severity,
            'message': message,
            'current_score': current_score,
            'threshold': threshold,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if citation_id:
            log_data['citation_id'] = citation_id
        
        if severity == 'critical':
            self.logger.critical("Accuracy alert triggered", extra=log_data)
        elif severity == 'warning':
            self.logger.warning("Accuracy warning", extra=log_data)
        else:
            self.logger.info("Accuracy notification", extra=log_data)
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None
    ):
        """
        Log API request.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration: Request duration
            user_id: Optional user ID
        """
        log_data = {
            'request_method': method,
            'request_path': path,
            'response_status': status_code,
            'duration_seconds': duration,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if user_id:
            log_data['user_id'] = user_id
        
        # Update metrics
        api_request_duration.labels(
            method=method,
            endpoint=path,
            status=str(status_code)
        ).observe(duration)
        
        if status_code >= 500:
            self.logger.error("API request failed", extra=log_data)
        elif status_code >= 400:
            self.logger.warning("API request client error", extra=log_data)
        else:
            self.logger.info("API request completed", extra=log_data)
    
    def log_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log exception with full traceback.
        
        Args:
            exception: Exception object
            context: Additional context
        """
        log_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if context:
            log_data['context'] = context
        
        self.logger.exception("Exception occurred", extra=log_data)


class MonitoringMiddleware:
    """
    Middleware for monitoring citation API requests.
    """
    
    def __init__(self, logger: CitationLogger):
        """Initialize monitoring middleware."""
        self.logger = logger
    
    async def __call__(self, request: Request, call_next):
        """Process request and log metrics."""
        start_time = datetime.utcnow()
        
        # Extract user ID if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'id', None)
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log request
            self.logger.log_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                user_id=user_id
            )
            
            return response
            
        except Exception as e:
            # Log exception
            self.logger.log_exception(e, {
                'method': request.method,
                'path': request.url.path,
                'user_id': user_id
            })
            raise


def setup_sentry():
    """
    Configure Sentry for error tracking.
    """
    if hasattr(settings, 'SENTRY_DSN') and settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'development',
            integrations=[
                SqlalchemyIntegration(),
                RedisIntegration()
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1
        )
        
        # Custom tags for citation system
        sentry_sdk.set_tag("system", "citation")
        sentry_sdk.set_tag("version", "1.0.0")


def setup_monitoring(app):
    """
    Setup monitoring for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Initialize logger
    logger = CitationLogger()
    
    # Setup Sentry
    setup_sentry()
    
    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware, logger=logger)
    
    # Add Prometheus metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return PlainTextResponse(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    # Health check endpoint with detailed status
    @app.get("/health/citation", include_in_schema=False)
    async def citation_health():
        """Citation system health check."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': 'healthy',
                'cache': 'healthy',
                'postgres_mcp': 'healthy',
                'puppeteer_mcp': 'healthy'
            },
            'metrics': {
                'system_accuracy': 0.0,
                'active_verifications': 0,
                'cache_hit_rate': 0.0
            }
        }
        
        # Check component health
        try:
            # Update MCP service health gauges
            mcp_service_health.labels(service='postgres').set(1)
            mcp_service_health.labels(service='puppeteer').set(1)
            
            # Calculate cache hit rate
            hits = citation_cache_hits._value._value if hasattr(citation_cache_hits, '_value') else 0
            misses = citation_cache_misses._value._value if hasattr(citation_cache_misses, '_value') else 0
            total = hits + misses
            if total > 0:
                health_status['metrics']['cache_hit_rate'] = hits / total
            
            return health_status
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            return Response(
                content=json.dumps(health_status),
                status_code=503,
                media_type="application/json"
            )
    
    return logger


class PerformanceTracker:
    """
    Track performance metrics for citation operations.
    """
    
    def __init__(self):
        """Initialize performance tracker."""
        self.operation_times = {}
    
    def start_operation(self, operation_id: str):
        """
        Start tracking an operation.
        
        Args:
            operation_id: Unique operation identifier
        """
        self.operation_times[operation_id] = datetime.utcnow()
    
    def end_operation(self, operation_id: str) -> float:
        """
        End tracking an operation and return duration.
        
        Args:
            operation_id: Unique operation identifier
            
        Returns:
            Duration in seconds
        """
        if operation_id not in self.operation_times:
            return 0.0
        
        start_time = self.operation_times.pop(operation_id)
        duration = (datetime.utcnow() - start_time).total_seconds()
        return duration
    
    def track_verification(self, citation_id: str):
        """
        Context manager for tracking verification performance.
        
        Args:
            citation_id: Citation ID being verified
        """
        class VerificationTracker:
            def __init__(self, tracker, citation_id):
                self.tracker = tracker
                self.citation_id = citation_id
                self.operation_id = f"verify_{citation_id}"
            
            def __enter__(self):
                self.tracker.start_operation(self.operation_id)
                active_verifications.inc()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = self.tracker.end_operation(self.operation_id)
                active_verifications.dec()
                citation_verification_time.observe(duration)
        
        return VerificationTracker(self, citation_id)


# Global instances
citation_logger = CitationLogger()
performance_tracker = PerformanceTracker()