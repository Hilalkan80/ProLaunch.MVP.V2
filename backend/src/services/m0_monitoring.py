"""
M0 Monitoring and Performance Tracking Service

Real-time monitoring, alerting, and performance optimization for M0 system.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
import logging
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from ..models.m0_feasibility import (
    M0FeasibilitySnapshot, M0PerformanceLog, M0Status
)
from ..infrastructure.redis.redis_mcp import RedisMCPClient

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics to track."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    SUCCESS_RATE = "success_rate"
    API_CALLS = "api_calls"
    RESOURCE_USAGE = "resource_usage"


class M0MonitoringService:
    """
    Comprehensive monitoring service for M0 feasibility system.
    
    Features:
    - Real-time performance metrics
    - Automatic alerting on anomalies
    - Trend analysis and predictions
    - Resource usage tracking
    - SLA monitoring
    """
    
    # SLA Targets
    SLA_TARGETS = {
        "latency_p95_ms": 60000,  # 95th percentile under 60s
        "latency_p99_ms": 75000,  # 99th percentile under 75s
        "success_rate": 0.95,  # 95% success rate
        "cache_hit_rate": 0.30,  # 30% cache hit rate
        "availability": 0.999  # 99.9% availability
    }
    
    # Alert Thresholds
    ALERT_THRESHOLDS = {
        "latency_warning_ms": 55000,  # Warning at 55s
        "latency_critical_ms": 70000,  # Critical at 70s
        "error_rate_warning": 0.05,  # 5% errors
        "error_rate_critical": 0.10,  # 10% errors
        "cache_hit_rate_low": 0.20,  # Low cache performance
        "api_calls_per_minute": 100  # Rate limit threshold
    }
    
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: RedisMCPClient
    ):
        """Initialize monitoring service."""
        self.db = db_session
        self.redis = redis_client
        
        # Metrics storage (in-memory circular buffers)
        self.metrics_buffer: Dict[str, deque] = {
            MetricType.LATENCY: deque(maxlen=1000),
            MetricType.THROUGHPUT: deque(maxlen=1000),
            MetricType.ERROR_RATE: deque(maxlen=1000),
            MetricType.CACHE_HIT_RATE: deque(maxlen=1000),
            MetricType.SUCCESS_RATE: deque(maxlen=1000),
            MetricType.API_CALLS: deque(maxlen=1000)
        }
        
        # Aggregated metrics
        self.aggregated_metrics: Dict[str, Any] = {}
        
        # Alert history
        self.alerts: deque = deque(maxlen=100)
        self.alert_callbacks: List[Any] = []
        
        # Monitoring tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.aggregation_task: Optional[asyncio.Task] = None
        
        # Performance baselines
        self.baselines: Dict[str, float] = {}
        self.anomaly_detector = AnomalyDetector()
    
    async def initialize(self) -> bool:
        """Initialize monitoring service and start background tasks."""
        try:
            # Load historical baselines
            await self._load_baselines()
            
            # Start monitoring tasks
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.aggregation_task = asyncio.create_task(self._aggregation_loop())
            
            logger.info("M0 Monitoring Service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            return False
    
    async def record_generation(
        self,
        snapshot_id: str,
        latency_ms: int,
        success: bool,
        used_cache: bool,
        error: Optional[str] = None
    ) -> None:
        """
        Record M0 generation metrics.
        
        Args:
            snapshot_id: Generated snapshot ID
            latency_ms: Total generation time
            success: Whether generation succeeded
            used_cache: Whether cache was used
            error: Error message if failed
        """
        try:
            timestamp = datetime.utcnow()
            
            # Record in metrics buffer
            self.metrics_buffer[MetricType.LATENCY].append({
                "timestamp": timestamp,
                "value": latency_ms,
                "snapshot_id": snapshot_id
            })
            
            # Update success rate
            self.metrics_buffer[MetricType.SUCCESS_RATE].append({
                "timestamp": timestamp,
                "value": 1 if success else 0
            })
            
            # Update cache hit rate
            if used_cache:
                self.metrics_buffer[MetricType.CACHE_HIT_RATE].append({
                    "timestamp": timestamp,
                    "value": 1
                })
            
            # Check for alerts
            await self._check_alerts(latency_ms, success, error)
            
            # Store in Redis for real-time dashboard
            await self._update_real_time_metrics({
                "latest_latency": latency_ms,
                "latest_success": success,
                "latest_timestamp": timestamp.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to record generation metrics: {e}")
    
    async def record_api_call(
        self,
        service: str,
        latency_ms: int,
        success: bool
    ) -> None:
        """
        Record external API call metrics.
        
        Args:
            service: API service name
            latency_ms: API call latency
            success: Whether call succeeded
        """
        try:
            self.metrics_buffer[MetricType.API_CALLS].append({
                "timestamp": datetime.utcnow(),
                "service": service,
                "latency_ms": latency_ms,
                "success": success
            })
            
        except Exception as e:
            logger.error(f"Failed to record API call: {e}")
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get real-time performance metrics.
        
        Returns:
            Current performance metrics
        """
        try:
            # Calculate current metrics
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "current": {},
                "aggregated": self.aggregated_metrics,
                "sla_status": {},
                "alerts": []
            }
            
            # Current performance (last 5 minutes)
            recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
            
            # Latency metrics
            recent_latencies = [
                m["value"] for m in self.metrics_buffer[MetricType.LATENCY]
                if m["timestamp"] > recent_cutoff
            ]
            
            if recent_latencies:
                metrics["current"]["avg_latency_ms"] = sum(recent_latencies) / len(recent_latencies)
                metrics["current"]["p95_latency_ms"] = self._calculate_percentile(recent_latencies, 95)
                metrics["current"]["p99_latency_ms"] = self._calculate_percentile(recent_latencies, 99)
            
            # Success rate
            recent_successes = [
                m["value"] for m in self.metrics_buffer[MetricType.SUCCESS_RATE]
                if m["timestamp"] > recent_cutoff
            ]
            
            if recent_successes:
                metrics["current"]["success_rate"] = sum(recent_successes) / len(recent_successes)
            
            # Cache hit rate
            recent_cache_hits = [
                m["value"] for m in self.metrics_buffer[MetricType.CACHE_HIT_RATE]
                if m["timestamp"] > recent_cutoff
            ]
            
            if recent_cache_hits:
                metrics["current"]["cache_hit_rate"] = sum(recent_cache_hits) / len(recent_cache_hits)
            
            # Check SLA status
            metrics["sla_status"] = await self._check_sla_compliance(metrics["current"])
            
            # Recent alerts
            metrics["alerts"] = list(self.alerts)[-10:]  # Last 10 alerts
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {}
    
    async def get_historical_metrics(
        self,
        time_range: str = "24h",
        metric_type: Optional[MetricType] = None
    ) -> Dict[str, Any]:
        """
        Get historical performance metrics.
        
        Args:
            time_range: Time range for metrics
            metric_type: Specific metric type to retrieve
            
        Returns:
            Historical metrics data
        """
        try:
            # Parse time range
            time_ranges = {
                "1h": timedelta(hours=1),
                "6h": timedelta(hours=6),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30)
            }
            
            delta = time_ranges.get(time_range, timedelta(hours=24))
            since = datetime.utcnow() - delta
            
            # Query database for historical data
            stmt = select(M0PerformanceLog).where(
                M0PerformanceLog.created_at >= since
            ).order_by(M0PerformanceLog.created_at)
            
            result = await self.db.execute(stmt)
            logs = result.scalars().all()
            
            # Process into time series
            metrics = {
                "time_range": time_range,
                "data_points": [],
                "summary": {}
            }
            
            for log in logs:
                data_point = {
                    "timestamp": log.created_at.isoformat(),
                    "total_time_ms": log.total_time_ms,
                    "research_time_ms": log.research_time_ms,
                    "analysis_time_ms": log.analysis_time_ms,
                    "used_cache": log.used_cache,
                    "had_errors": log.had_errors
                }
                
                metrics["data_points"].append(data_point)
            
            # Calculate summary statistics
            if metrics["data_points"]:
                total_times = [dp["total_time_ms"] for dp in metrics["data_points"]]
                error_count = sum(1 for dp in metrics["data_points"] if dp["had_errors"])
                cache_count = sum(1 for dp in metrics["data_points"] if dp["used_cache"])
                
                metrics["summary"] = {
                    "total_generations": len(metrics["data_points"]),
                    "avg_time_ms": sum(total_times) / len(total_times),
                    "min_time_ms": min(total_times),
                    "max_time_ms": max(total_times),
                    "p95_time_ms": self._calculate_percentile(total_times, 95),
                    "p99_time_ms": self._calculate_percentile(total_times, 99),
                    "error_rate": error_count / len(metrics["data_points"]),
                    "cache_hit_rate": cache_count / len(metrics["data_points"])
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return {}
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage metrics.
        
        Returns:
            Resource usage data
        """
        try:
            usage = {
                "timestamp": datetime.utcnow().isoformat(),
                "database": {},
                "cache": {},
                "api_quota": {}
            }
            
            # Database metrics
            stmt = select(func.count(M0FeasibilitySnapshot.id))
            result = await self.db.execute(stmt)
            usage["database"]["total_snapshots"] = result.scalar() or 0
            
            # Cache metrics
            cache_stats = await self.redis.get_cache("m0:cache:stats")
            if cache_stats:
                usage["cache"] = cache_stats
            
            # API quota usage (would connect to actual services)
            usage["api_quota"] = {
                "llm_calls_today": len([
                    c for c in self.metrics_buffer[MetricType.API_CALLS]
                    if c["service"] == "llm" and 
                    c["timestamp"] > datetime.utcnow() - timedelta(days=1)
                ]),
                "search_calls_today": len([
                    c for c in self.metrics_buffer[MetricType.API_CALLS]
                    if c["service"] == "search" and
                    c["timestamp"] > datetime.utcnow() - timedelta(days=1)
                ])
            }
            
            return usage
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return {}
    
    async def _monitoring_loop(self) -> None:
        """Background loop for continuous monitoring."""
        while True:
            try:
                # Collect metrics every 30 seconds
                await asyncio.sleep(30)
                
                # Query recent performance logs
                stmt = select(M0PerformanceLog).where(
                    M0PerformanceLog.created_at > datetime.utcnow() - timedelta(minutes=1)
                )
                
                result = await self.db.execute(stmt)
                recent_logs = result.scalars().all()
                
                # Update metrics buffers
                for log in recent_logs:
                    self.metrics_buffer[MetricType.LATENCY].append({
                        "timestamp": log.created_at,
                        "value": log.total_time_ms,
                        "snapshot_id": str(log.snapshot_id)
                    })
                    
                    self.metrics_buffer[MetricType.SUCCESS_RATE].append({
                        "timestamp": log.created_at,
                        "value": 0 if log.had_errors else 1
                    })
                
                # Check for anomalies
                await self._detect_anomalies()
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _aggregation_loop(self) -> None:
        """Background loop for metric aggregation."""
        while True:
            try:
                # Aggregate metrics every 5 minutes
                await asyncio.sleep(300)
                
                # Calculate aggregated metrics
                await self._calculate_aggregated_metrics()
                
                # Store in Redis for dashboard
                await self.redis.set_cache(
                    "m0:metrics:aggregated",
                    self.aggregated_metrics,
                    600  # 10 minute TTL
                )
                
                # Clean old data from buffers
                cutoff = datetime.utcnow() - timedelta(hours=1)
                for metric_type in self.metrics_buffer:
                    self.metrics_buffer[metric_type] = deque(
                        [m for m in self.metrics_buffer[metric_type] 
                         if m.get("timestamp", datetime.utcnow()) > cutoff],
                        maxlen=1000
                    )
                
            except Exception as e:
                logger.error(f"Aggregation loop error: {e}")
                await asyncio.sleep(300)
    
    async def _calculate_aggregated_metrics(self) -> None:
        """Calculate aggregated metrics from buffers."""
        try:
            self.aggregated_metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "1h": {},
                "6h": {},
                "24h": {}
            }
            
            for period, hours in [("1h", 1), ("6h", 6), ("24h", 24)]:
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                
                # Latency aggregation
                latencies = [
                    m["value"] for m in self.metrics_buffer[MetricType.LATENCY]
                    if m["timestamp"] > cutoff
                ]
                
                if latencies:
                    self.aggregated_metrics[period]["avg_latency"] = sum(latencies) / len(latencies)
                    self.aggregated_metrics[period]["p95_latency"] = self._calculate_percentile(latencies, 95)
                    self.aggregated_metrics[period]["p99_latency"] = self._calculate_percentile(latencies, 99)
                
                # Success rate aggregation
                successes = [
                    m["value"] for m in self.metrics_buffer[MetricType.SUCCESS_RATE]
                    if m["timestamp"] > cutoff
                ]
                
                if successes:
                    self.aggregated_metrics[period]["success_rate"] = sum(successes) / len(successes)
                
                # Throughput calculation
                self.aggregated_metrics[period]["throughput_per_hour"] = len(latencies) / hours if hours > 0 else 0
                
        except Exception as e:
            logger.error(f"Failed to calculate aggregated metrics: {e}")
    
    async def _check_alerts(
        self,
        latency_ms: int,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Check for alert conditions."""
        alerts = []
        
        # Latency alerts
        if latency_ms > self.ALERT_THRESHOLDS["latency_critical_ms"]:
            alerts.append({
                "level": AlertLevel.CRITICAL,
                "metric": "latency",
                "value": latency_ms,
                "threshold": self.ALERT_THRESHOLDS["latency_critical_ms"],
                "message": f"Critical latency: {latency_ms}ms exceeds {self.ALERT_THRESHOLDS['latency_critical_ms']}ms"
            })
        elif latency_ms > self.ALERT_THRESHOLDS["latency_warning_ms"]:
            alerts.append({
                "level": AlertLevel.WARNING,
                "metric": "latency",
                "value": latency_ms,
                "threshold": self.ALERT_THRESHOLDS["latency_warning_ms"],
                "message": f"High latency: {latency_ms}ms exceeds {self.ALERT_THRESHOLDS['latency_warning_ms']}ms"
            })
        
        # Error alerts
        if not success:
            alerts.append({
                "level": AlertLevel.ERROR,
                "metric": "error",
                "error": error,
                "message": f"Generation failed: {error}"
            })
        
        # Process alerts
        for alert in alerts:
            alert["timestamp"] = datetime.utcnow().isoformat()
            self.alerts.append(alert)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    async def _check_sla_compliance(self, current_metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Check SLA compliance status."""
        sla_status = {}
        
        # Check each SLA target
        if "p95_latency_ms" in current_metrics:
            sla_status["latency_p95"] = current_metrics["p95_latency_ms"] <= self.SLA_TARGETS["latency_p95_ms"]
        
        if "p99_latency_ms" in current_metrics:
            sla_status["latency_p99"] = current_metrics["p99_latency_ms"] <= self.SLA_TARGETS["latency_p99_ms"]
        
        if "success_rate" in current_metrics:
            sla_status["success_rate"] = current_metrics["success_rate"] >= self.SLA_TARGETS["success_rate"]
        
        if "cache_hit_rate" in current_metrics:
            sla_status["cache_hit_rate"] = current_metrics["cache_hit_rate"] >= self.SLA_TARGETS["cache_hit_rate"]
        
        return sla_status
    
    async def _detect_anomalies(self) -> None:
        """Detect anomalies in metrics."""
        try:
            # Get recent metrics
            recent_latencies = [
                m["value"] for m in self.metrics_buffer[MetricType.LATENCY]
                if m["timestamp"] > datetime.utcnow() - timedelta(minutes=10)
            ]
            
            if len(recent_latencies) >= 10:
                # Check for anomalies
                anomalies = self.anomaly_detector.detect(recent_latencies)
                
                for anomaly in anomalies:
                    alert = {
                        "level": AlertLevel.WARNING,
                        "metric": "anomaly",
                        "type": anomaly["type"],
                        "value": anomaly["value"],
                        "message": f"Anomaly detected: {anomaly['description']}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    self.alerts.append(alert)
                    
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
    
    async def _load_baselines(self) -> None:
        """Load performance baselines from historical data."""
        try:
            # Query last 7 days of data
            stmt = select(M0PerformanceLog).where(
                M0PerformanceLog.created_at > datetime.utcnow() - timedelta(days=7)
            )
            
            result = await self.db.execute(stmt)
            logs = result.scalars().all()
            
            if logs:
                latencies = [log.total_time_ms for log in logs]
                
                self.baselines = {
                    "avg_latency": sum(latencies) / len(latencies),
                    "p95_latency": self._calculate_percentile(latencies, 95),
                    "p99_latency": self._calculate_percentile(latencies, 99),
                    "min_latency": min(latencies),
                    "max_latency": max(latencies)
                }
                
                logger.info(f"Loaded baselines from {len(logs)} historical records")
                
        except Exception as e:
            logger.error(f"Failed to load baselines: {e}")
    
    async def _update_real_time_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update real-time metrics in Redis."""
        try:
            await self.redis.set_cache(
                "m0:metrics:realtime",
                metrics,
                60  # 1 minute TTL
            )
        except Exception as e:
            logger.error(f"Failed to update real-time metrics: {e}")
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from list."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100))
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[index]
    
    def register_alert_callback(self, callback: Any) -> None:
        """Register callback for alerts."""
        self.alert_callbacks.append(callback)
    
    async def export_metrics(
        self,
        format: str = "json",
        time_range: str = "24h"
    ) -> Any:
        """
        Export metrics in various formats.
        
        Args:
            format: Export format (json, csv, prometheus)
            time_range: Time range for export
            
        Returns:
            Exported metrics data
        """
        try:
            metrics = await self.get_historical_metrics(time_range)
            
            if format == "json":
                return json.dumps(metrics, indent=2, default=str)
                
            elif format == "csv":
                # Convert to CSV format
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=["timestamp", "total_time_ms", "research_time_ms", 
                               "analysis_time_ms", "used_cache", "had_errors"]
                )
                
                writer.writeheader()
                for point in metrics.get("data_points", []):
                    writer.writerow(point)
                
                return output.getvalue()
                
            elif format == "prometheus":
                # Prometheus format
                lines = []
                
                if "summary" in metrics:
                    lines.append(f"# HELP m0_latency_ms M0 generation latency in milliseconds")
                    lines.append(f"# TYPE m0_latency_ms summary")
                    lines.append(f"m0_latency_ms{{quantile=\"0.5\"}} {metrics['summary'].get('avg_time_ms', 0)}")
                    lines.append(f"m0_latency_ms{{quantile=\"0.95\"}} {metrics['summary'].get('p95_time_ms', 0)}")
                    lines.append(f"m0_latency_ms{{quantile=\"0.99\"}} {metrics['summary'].get('p99_time_ms', 0)}")
                    
                    lines.append(f"# HELP m0_success_rate M0 generation success rate")
                    lines.append(f"# TYPE m0_success_rate gauge")
                    lines.append(f"m0_success_rate {1 - metrics['summary'].get('error_rate', 0)}")
                
                return "\n".join(lines)
                
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown monitoring service."""
        try:
            # Cancel background tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            if self.aggregation_task:
                self.aggregation_task.cancel()
            
            # Save final metrics
            await self._calculate_aggregated_metrics()
            
            logger.info("M0 Monitoring Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


class AnomalyDetector:
    """Simple anomaly detection for metrics."""
    
    def __init__(self, sensitivity: float = 2.0):
        """
        Initialize anomaly detector.
        
        Args:
            sensitivity: Standard deviations for anomaly threshold
        """
        self.sensitivity = sensitivity
    
    def detect(self, values: List[float]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in values using statistical methods.
        
        Args:
            values: List of metric values
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        if len(values) < 10:
            return anomalies
        
        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # Detect outliers
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std_dev) if std_dev > 0 else 0
            
            if z_score > self.sensitivity:
                anomalies.append({
                    "type": "statistical_outlier",
                    "index": i,
                    "value": value,
                    "z_score": z_score,
                    "description": f"Value {value} is {z_score:.2f} standard deviations from mean"
                })
        
        # Detect sudden spikes
        for i in range(1, len(values)):
            change_rate = abs(values[i] - values[i-1]) / values[i-1] if values[i-1] > 0 else 0
            
            if change_rate > 0.5:  # 50% change
                anomalies.append({
                    "type": "sudden_spike",
                    "index": i,
                    "value": values[i],
                    "change_rate": change_rate,
                    "description": f"Sudden {change_rate:.0%} change detected"
                })
        
        return anomalies