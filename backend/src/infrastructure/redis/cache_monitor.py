"""
Redis Cache Performance Monitoring

Provides real-time monitoring, alerting, and optimization recommendations
for the Redis caching layer.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to monitor"""
    HIT_RATE = "hit_rate"
    LATENCY = "latency"
    MEMORY_USAGE = "memory_usage"
    CONNECTION_POOL = "connection_pool"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    EVICTION_RATE = "eviction_rate"


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    
    def is_anomaly(self, baseline: float, threshold: float) -> bool:
        """Check if metric is anomalous compared to baseline"""
        deviation = abs(self.value - baseline) / baseline if baseline else 0
        return deviation > threshold


@dataclass
class Alert:
    """Performance alert"""
    severity: AlertSeverity
    metric_type: MetricType
    message: str
    value: float
    threshold: float
    timestamp: datetime
    recommendations: List[str] = field(default_factory=list)


class CachePerformanceMonitor:
    """
    Monitors Redis cache performance with:
    - Real-time metrics collection
    - Anomaly detection
    - Performance alerts
    - Optimization recommendations
    - Historical analysis
    """
    
    def __init__(
        self,
        cache_service,
        connection_manager,
        enable_alerts: bool = True,
        enable_auto_tuning: bool = False
    ):
        """Initialize the performance monitor"""
        self.cache_service = cache_service
        self.connection_manager = connection_manager
        self.enable_alerts = enable_alerts
        self.enable_auto_tuning = enable_auto_tuning
        
        # Metrics storage (in-memory circular buffer)
        self._metrics_buffer: Dict[MetricType, List[PerformanceMetric]] = {
            metric_type: [] for metric_type in MetricType
        }
        self._buffer_size = 1000
        
        # Baselines for anomaly detection
        self._baselines: Dict[MetricType, float] = {}
        self._baseline_window = 100  # Number of samples for baseline
        
        # Thresholds for alerts
        self._thresholds = {
            MetricType.HIT_RATE: {"warning": 0.7, "error": 0.5, "critical": 0.3},
            MetricType.LATENCY: {"warning": 100, "error": 500, "critical": 1000},  # ms
            MetricType.MEMORY_USAGE: {"warning": 0.7, "error": 0.85, "critical": 0.95},
            MetricType.ERROR_RATE: {"warning": 0.01, "error": 0.05, "critical": 0.1},
            MetricType.EVICTION_RATE: {"warning": 0.1, "error": 0.2, "critical": 0.3},
        }
        
        # Alert history
        self._alerts: List[Alert] = []
        self._alert_callbacks = []
        
        # Monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._collection_interval = 10  # seconds
        
        # Performance recommendations
        self._recommendations_engine = PerformanceRecommendations()
    
    async def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already running")
            return
        
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Cache performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        logger.info("Cache performance monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                
                # Store metrics
                for metric in metrics:
                    self._store_metric(metric)
                
                # Update baselines
                self._update_baselines()
                
                # Check for anomalies and alerts
                if self.enable_alerts:
                    alerts = self._check_alerts(metrics)
                    for alert in alerts:
                        await self._handle_alert(alert)
                
                # Auto-tuning if enabled
                if self.enable_auto_tuning:
                    await self._auto_tune_cache()
                
                # Wait for next collection
                await asyncio.sleep(self._collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self._collection_interval)
    
    async def _collect_metrics(self) -> List[PerformanceMetric]:
        """Collect current performance metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        # Cache hit rate
        cache_metrics = await self.cache_service.get_cache_metrics()
        total_requests = cache_metrics.get("l1_hits", 0) + cache_metrics.get("l1_misses", 0)
        if total_requests > 0:
            hit_rate = cache_metrics.get("l1_hits", 0) / total_requests
            metrics.append(PerformanceMetric(
                MetricType.HIT_RATE,
                hit_rate,
                timestamp,
                {"layer": "l1"}
            ))
        
        # L2 hit rate
        l2_total = cache_metrics.get("l2_hits", 0) + cache_metrics.get("l2_misses", 0)
        if l2_total > 0:
            l2_hit_rate = cache_metrics.get("l2_hits", 0) / l2_total
            metrics.append(PerformanceMetric(
                MetricType.HIT_RATE,
                l2_hit_rate,
                timestamp,
                {"layer": "l2"}
            ))
        
        # Memory usage
        try:
            redis_info = await self.connection_manager.get_info("memory")
            used_memory = redis_info.get("used_memory", 0)
            max_memory = redis_info.get("maxmemory", 0) or (4 * 1024 * 1024 * 1024)  # Default 4GB
            memory_usage = used_memory / max_memory if max_memory else 0
            
            metrics.append(PerformanceMetric(
                MetricType.MEMORY_USAGE,
                memory_usage,
                timestamp
            ))
            
            # Eviction rate
            evicted_keys = redis_info.get("evicted_keys", 0)
            if hasattr(self, "_last_evicted_keys"):
                eviction_rate = (evicted_keys - self._last_evicted_keys) / self._collection_interval
                metrics.append(PerformanceMetric(
                    MetricType.EVICTION_RATE,
                    eviction_rate,
                    timestamp
                ))
            self._last_evicted_keys = evicted_keys
            
        except Exception as e:
            logger.error(f"Failed to collect Redis info: {e}")
        
        # Connection pool metrics
        conn_metrics = self.connection_manager.get_metrics()
        if conn_metrics:
            # Error rate
            total_commands = conn_metrics.get("commands_executed", 0) + conn_metrics.get("commands_failed", 0)
            if total_commands > 0:
                error_rate = conn_metrics.get("commands_failed", 0) / total_commands
                metrics.append(PerformanceMetric(
                    MetricType.ERROR_RATE,
                    error_rate,
                    timestamp
                ))
            
            # Connection pool usage
            pool_size = conn_metrics.get("created_connections", 0)
            active_connections = conn_metrics.get("active_connections", 0)
            if pool_size > 0:
                pool_usage = active_connections / pool_size
                metrics.append(PerformanceMetric(
                    MetricType.CONNECTION_POOL,
                    pool_usage,
                    timestamp
                ))
        
        # Measure latency (sample operation)
        latency = await self._measure_latency()
        if latency:
            metrics.append(PerformanceMetric(
                MetricType.LATENCY,
                latency,
                timestamp
            ))
        
        return metrics
    
    async def _measure_latency(self) -> Optional[float]:
        """Measure cache operation latency"""
        try:
            start = datetime.utcnow()
            
            # Perform sample operations
            test_key = "__perf_test_key__"
            await self.cache_service._safe_redis_set(test_key, "test", 10)
            await self.cache_service._safe_redis_get(test_key)
            await self.cache_service._safe_redis_delete(test_key)
            
            end = datetime.utcnow()
            latency_ms = (end - start).total_seconds() * 1000 / 3  # Average of 3 operations
            
            return latency_ms
            
        except Exception as e:
            logger.error(f"Failed to measure latency: {e}")
            return None
    
    def _store_metric(self, metric: PerformanceMetric) -> None:
        """Store metric in circular buffer"""
        buffer = self._metrics_buffer[metric.metric_type]
        buffer.append(metric)
        
        # Maintain buffer size
        if len(buffer) > self._buffer_size:
            buffer.pop(0)
    
    def _update_baselines(self) -> None:
        """Update baselines for anomaly detection"""
        for metric_type, buffer in self._metrics_buffer.items():
            if len(buffer) >= self._baseline_window:
                recent_values = [m.value for m in buffer[-self._baseline_window:]]
                self._baselines[metric_type] = statistics.median(recent_values)
    
    def _check_alerts(self, metrics: List[PerformanceMetric]) -> List[Alert]:
        """Check metrics for alert conditions"""
        alerts = []
        
        for metric in metrics:
            if metric.metric_type not in self._thresholds:
                continue
            
            thresholds = self._thresholds[metric.metric_type]
            
            # Check hit rate (lower is worse)
            if metric.metric_type == MetricType.HIT_RATE:
                if metric.value < thresholds["critical"]:
                    alerts.append(self._create_alert(
                        AlertSeverity.CRITICAL,
                        metric,
                        thresholds["critical"],
                        "Cache hit rate critically low"
                    ))
                elif metric.value < thresholds["error"]:
                    alerts.append(self._create_alert(
                        AlertSeverity.ERROR,
                        metric,
                        thresholds["error"],
                        "Cache hit rate below acceptable level"
                    ))
                elif metric.value < thresholds["warning"]:
                    alerts.append(self._create_alert(
                        AlertSeverity.WARNING,
                        metric,
                        thresholds["warning"],
                        "Cache hit rate degraded"
                    ))
            
            # Check other metrics (higher is worse)
            else:
                if metric.value > thresholds.get("critical", float('inf')):
                    alerts.append(self._create_alert(
                        AlertSeverity.CRITICAL,
                        metric,
                        thresholds["critical"],
                        f"{metric.metric_type.value} critically high"
                    ))
                elif metric.value > thresholds.get("error", float('inf')):
                    alerts.append(self._create_alert(
                        AlertSeverity.ERROR,
                        metric,
                        thresholds["error"],
                        f"{metric.metric_type.value} above error threshold"
                    ))
                elif metric.value > thresholds.get("warning", float('inf')):
                    alerts.append(self._create_alert(
                        AlertSeverity.WARNING,
                        metric,
                        thresholds["warning"],
                        f"{metric.metric_type.value} above warning threshold"
                    ))
        
        return alerts
    
    def _create_alert(
        self,
        severity: AlertSeverity,
        metric: PerformanceMetric,
        threshold: float,
        message: str
    ) -> Alert:
        """Create an alert with recommendations"""
        recommendations = self._recommendations_engine.get_recommendations(
            metric.metric_type,
            metric.value,
            severity
        )
        
        return Alert(
            severity=severity,
            metric_type=metric.metric_type,
            message=message,
            value=metric.value,
            threshold=threshold,
            timestamp=metric.timestamp,
            recommendations=recommendations
        )
    
    async def _handle_alert(self, alert: Alert) -> None:
        """Handle a performance alert"""
        # Log alert
        log_level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }[alert.severity]
        
        logger.log(
            log_level,
            f"Cache Performance Alert: {alert.message} "
            f"(value: {alert.value:.2f}, threshold: {alert.threshold:.2f})"
        )
        
        # Log recommendations
        if alert.recommendations:
            logger.info(f"Recommendations: {', '.join(alert.recommendations)}")
        
        # Store alert
        self._alerts.append(alert)
        if len(self._alerts) > 1000:
            self._alerts = self._alerts[-1000:]  # Keep last 1000 alerts
        
        # Execute callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def _auto_tune_cache(self) -> None:
        """Automatically tune cache parameters based on metrics"""
        if not self._baselines:
            return
        
        # Auto-tune TTLs based on hit rate
        hit_rate_baseline = self._baselines.get(MetricType.HIT_RATE, 0)
        if hit_rate_baseline < 0.5:
            # Increase TTLs if hit rate is low
            logger.info("Auto-tuning: Increasing cache TTLs due to low hit rate")
            # This would update TTL configuration
        
        # Auto-tune L1 cache size based on memory pressure
        memory_usage = self._baselines.get(MetricType.MEMORY_USAGE, 0)
        if memory_usage > 0.8:
            # Reduce L1 cache size
            current_size = self.cache_service._l1_max_size
            new_size = int(current_size * 0.8)
            self.cache_service._l1_max_size = max(new_size, 100)
            logger.info(f"Auto-tuning: Reduced L1 cache size to {new_size}")
        elif memory_usage < 0.3 and self.cache_service._l1_max_size < 5000:
            # Increase L1 cache size
            new_size = int(self.cache_service._l1_max_size * 1.2)
            self.cache_service._l1_max_size = min(new_size, 5000)
            logger.info(f"Auto-tuning: Increased L1 cache size to {new_size}")
    
    def register_alert_callback(self, callback) -> None:
        """Register a callback for alerts"""
        self._alert_callbacks.append(callback)
    
    def get_metrics_summary(
        self,
        metric_type: Optional[MetricType] = None,
        duration: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for metrics"""
        if duration:
            cutoff_time = datetime.utcnow() - duration
        else:
            cutoff_time = datetime.min
        
        summary = {}
        
        metric_types = [metric_type] if metric_type else MetricType
        
        for mt in metric_types:
            buffer = self._metrics_buffer.get(mt, [])
            recent_metrics = [
                m for m in buffer
                if m.timestamp > cutoff_time
            ]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[mt.value] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "latest": values[-1],
                    "baseline": self._baselines.get(mt, 0)
                }
        
        return summary
    
    def get_recent_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        limit: int = 10
    ) -> List[Alert]:
        """Get recent alerts"""
        alerts = self._alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]
    
    async def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring_duration": len(self._alerts) * self._collection_interval,
            "metrics_summary": self.get_metrics_summary(),
            "recent_alerts": [
                {
                    "severity": alert.severity.value,
                    "type": alert.metric_type.value,
                    "message": alert.message,
                    "value": alert.value,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in self.get_recent_alerts(limit=20)
            ],
            "cache_health": await self._assess_cache_health(),
            "recommendations": self._get_optimization_recommendations()
        }
        
        return report
    
    async def _assess_cache_health(self) -> str:
        """Assess overall cache health"""
        recent_metrics = self.get_metrics_summary(duration=timedelta(minutes=5))
        
        if not recent_metrics:
            return "UNKNOWN"
        
        # Check critical metrics
        hit_rate = recent_metrics.get(MetricType.HIT_RATE.value, {}).get("mean", 0)
        error_rate = recent_metrics.get(MetricType.ERROR_RATE.value, {}).get("mean", 0)
        memory_usage = recent_metrics.get(MetricType.MEMORY_USAGE.value, {}).get("mean", 0)
        
        if error_rate > 0.1 or hit_rate < 0.3 or memory_usage > 0.95:
            return "CRITICAL"
        elif error_rate > 0.05 or hit_rate < 0.5 or memory_usage > 0.85:
            return "DEGRADED"
        elif error_rate > 0.01 or hit_rate < 0.7 or memory_usage > 0.7:
            return "WARNING"
        else:
            return "HEALTHY"
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Get cache optimization recommendations"""
        recommendations = []
        
        # Analyze recent metrics
        recent_metrics = self.get_metrics_summary(duration=timedelta(minutes=30))
        
        if recent_metrics:
            # Hit rate recommendations
            hit_rate = recent_metrics.get(MetricType.HIT_RATE.value, {}).get("mean", 1)
            if hit_rate < 0.7:
                recommendations.append("Consider increasing cache TTLs to improve hit rate")
                recommendations.append("Review cache key patterns for optimization opportunities")
            
            # Memory recommendations
            memory_usage = recent_metrics.get(MetricType.MEMORY_USAGE.value, {}).get("mean", 0)
            if memory_usage > 0.8:
                recommendations.append("Consider enabling cache eviction policies")
                recommendations.append("Review and remove unused cache keys")
            elif memory_usage < 0.3:
                recommendations.append("Cache is underutilized - consider caching more data")
            
            # Latency recommendations
            latency = recent_metrics.get(MetricType.LATENCY.value, {}).get("mean", 0)
            if latency > 100:
                recommendations.append("High latency detected - check network connectivity")
                recommendations.append("Consider using connection pooling or pipelining")
        
        return recommendations


class PerformanceRecommendations:
    """Engine for generating performance recommendations"""
    
    def get_recommendations(
        self,
        metric_type: MetricType,
        value: float,
        severity: AlertSeverity
    ) -> List[str]:
        """Get recommendations based on metric and severity"""
        recommendations = []
        
        if metric_type == MetricType.HIT_RATE:
            if severity == AlertSeverity.CRITICAL:
                recommendations.extend([
                    "Immediately increase cache TTLs",
                    "Implement cache warming for critical data",
                    "Review and fix cache invalidation logic"
                ])
            elif severity == AlertSeverity.ERROR:
                recommendations.extend([
                    "Increase cache TTLs by 50%",
                    "Enable refresh-ahead caching for frequently accessed data",
                    "Analyze cache miss patterns"
                ])
            else:
                recommendations.extend([
                    "Monitor cache patterns",
                    "Consider adjusting TTLs",
                    "Review cache key design"
                ])
        
        elif metric_type == MetricType.MEMORY_USAGE:
            if severity == AlertSeverity.CRITICAL:
                recommendations.extend([
                    "Immediately enable eviction policies",
                    "Reduce cache TTLs",
                    "Remove unnecessary cached data",
                    "Consider scaling Redis instance"
                ])
            elif severity == AlertSeverity.ERROR:
                recommendations.extend([
                    "Enable LRU eviction policy",
                    "Implement cache size limits",
                    "Review large cached objects"
                ])
            else:
                recommendations.extend([
                    "Monitor memory trends",
                    "Plan for capacity increase",
                    "Optimize data structures"
                ])
        
        elif metric_type == MetricType.LATENCY:
            if value > 500:
                recommendations.extend([
                    "Check network connectivity",
                    "Increase connection pool size",
                    "Enable pipelining for batch operations",
                    "Consider using Redis cluster"
                ])
            elif value > 100:
                recommendations.extend([
                    "Optimize slow commands",
                    "Use connection pooling",
                    "Review network configuration"
                ])
        
        elif metric_type == MetricType.ERROR_RATE:
            if severity >= AlertSeverity.ERROR:
                recommendations.extend([
                    "Check Redis server logs",
                    "Review connection configuration",
                    "Implement retry logic with backoff",
                    "Enable circuit breaker"
                ])
        
        elif metric_type == MetricType.EVICTION_RATE:
            if value > 0.2:
                recommendations.extend([
                    "Increase Redis memory limit",
                    "Reduce cache TTLs for non-critical data",
                    "Implement tiered caching strategy",
                    "Review cache priority settings"
                ])
        
        return recommendations