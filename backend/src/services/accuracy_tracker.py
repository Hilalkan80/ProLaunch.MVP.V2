"""
Accuracy tracking system for citation quality monitoring.

This module provides real-time accuracy tracking, alerting, and reporting
for the citation system to ensure 95% accuracy threshold is maintained.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from enum import Enum

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
import redis
from prometheus_client import Counter, Gauge, Histogram
import sentry_sdk

from ..models.citation import (
    Citation, AccuracyTracking, VerificationLog,
    MetricType, FeedbackType, VerificationStatus
)
from ..core.exceptions import ServiceUnavailableError
from ..utils.notifications import NotificationService

logger = logging.getLogger(__name__)


# Prometheus metrics
accuracy_score_gauge = Gauge(
    'citation_accuracy_score',
    'Current citation accuracy score',
    ['citation_id', 'metric_type']
)

accuracy_threshold_violations = Counter(
    'citation_accuracy_threshold_violations',
    'Number of times accuracy fell below threshold',
    ['severity']
)

feedback_submissions = Counter(
    'citation_feedback_submissions',
    'Number of feedback submissions',
    ['feedback_type', 'metric_type']
)

verification_duration = Histogram(
    'citation_verification_duration_seconds',
    'Time taken to verify citations',
    buckets=[1, 5, 10, 30, 60, 120, 300]
)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AccuracyStatus(str, Enum):
    """System accuracy status."""
    GREEN = "green"  # >= 95%
    YELLOW = "yellow"  # 90-94%
    RED = "red"  # < 90%


class AccuracyAlert(object):
    """Accuracy alert model."""
    
    def __init__(
        self,
        severity: AlertSeverity,
        message: str,
        citation_id: Optional[UUID] = None,
        current_score: float = 0.0,
        threshold: float = 0.95,
        metadata: Dict[str, Any] = None
    ):
        self.id = UUID()
        self.severity = severity
        self.message = message
        self.citation_id = citation_id
        self.current_score = current_score
        self.threshold = threshold
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.resolved = False
        self.resolved_at = None


class AccuracyTracker:
    """
    Real-time accuracy tracking and monitoring system.
    
    Monitors citation accuracy, generates alerts, and provides
    reporting to maintain 95% accuracy threshold.
    """
    
    def __init__(
        self,
        db: Session,
        redis_client: Optional[redis.Redis] = None,
        notification_service: Optional[NotificationService] = None
    ):
        """Initialize accuracy tracker."""
        self.db = db
        self.redis = redis_client
        self.notifications = notification_service
        self.accuracy_threshold = 0.95
        self.warning_threshold = 0.90
        self.active_alerts: Dict[str, AccuracyAlert] = {}
        self._monitoring_task = None
    
    async def start_monitoring(self):
        """Start continuous accuracy monitoring."""
        if self._monitoring_task:
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started accuracy monitoring")
    
    async def stop_monitoring(self):
        """Stop accuracy monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            logger.info("Stopped accuracy monitoring")
    
    async def _monitoring_loop(self):
        """Continuous monitoring loop."""
        while True:
            try:
                await self.check_system_accuracy()
                await self.check_individual_citations()
                await self.process_stale_verifications()
                await asyncio.sleep(300)  # Check every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                sentry_sdk.capture_exception(e)
                await asyncio.sleep(60)  # Wait before retrying
    
    async def check_system_accuracy(self) -> AccuracyStatus:
        """
        Check overall system accuracy.
        
        Returns:
            Current accuracy status
        """
        try:
            # Calculate system-wide accuracy
            result = self.db.execute(
                select(func.avg(Citation.overall_quality_score))
                .where(Citation.is_active == True)
            ).scalar()
            
            overall_accuracy = float(result) if result else 0.0
            
            # Update Prometheus metric
            accuracy_score_gauge.labels(
                citation_id="system",
                metric_type="overall"
            ).set(overall_accuracy)
            
            # Determine status
            if overall_accuracy >= self.accuracy_threshold:
                status = AccuracyStatus.GREEN
            elif overall_accuracy >= self.warning_threshold:
                status = AccuracyStatus.YELLOW
                await self._create_alert(
                    AlertSeverity.WARNING,
                    f"System accuracy below target: {overall_accuracy:.1%}",
                    current_score=overall_accuracy
                )
            else:
                status = AccuracyStatus.RED
                await self._create_alert(
                    AlertSeverity.CRITICAL,
                    f"System accuracy critical: {overall_accuracy:.1%}",
                    current_score=overall_accuracy
                )
            
            # Cache the status
            if self.redis:
                self.redis.setex(
                    "citation:system:accuracy",
                    300,  # 5 minute TTL
                    overall_accuracy
                )
                self.redis.setex(
                    "citation:system:status",
                    300,
                    status.value
                )
            
            logger.info(f"System accuracy: {overall_accuracy:.1%} - Status: {status.value}")
            return status
            
        except Exception as e:
            logger.error(f"Error checking system accuracy: {e}")
            raise ServiceUnavailableError(f"Accuracy check failed: {e}")
    
    async def check_individual_citations(self, limit: int = 100):
        """
        Check individual citations for accuracy issues.
        
        Args:
            limit: Maximum citations to check
        """
        try:
            # Find citations with low accuracy
            low_accuracy_citations = self.db.execute(
                select(Citation)
                .where(
                    and_(
                        Citation.is_active == True,
                        Citation.overall_quality_score < self.warning_threshold
                    )
                )
                .order_by(Citation.overall_quality_score.asc())
                .limit(limit)
            ).scalars().all()
            
            for citation in low_accuracy_citations:
                # Update metric
                accuracy_score_gauge.labels(
                    citation_id=str(citation.id),
                    metric_type="overall"
                ).set(citation.overall_quality_score)
                
                # Create alert if below threshold
                if citation.overall_quality_score < self.accuracy_threshold:
                    severity = (
                        AlertSeverity.CRITICAL
                        if citation.overall_quality_score < 0.80
                        else AlertSeverity.WARNING
                    )
                    
                    await self._create_alert(
                        severity,
                        f"Citation accuracy low: {citation.title[:50]}...",
                        citation_id=citation.id,
                        current_score=citation.overall_quality_score
                    )
                    
                    # Mark for reverification
                    citation.requires_reverification = True
                    self.db.commit()
            
            logger.info(f"Checked {len(low_accuracy_citations)} low-accuracy citations")
            
        except Exception as e:
            logger.error(f"Error checking individual citations: {e}")
    
    async def process_stale_verifications(self):
        """Process citations with stale verifications."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            stale_citations = self.db.execute(
                select(Citation)
                .where(
                    and_(
                        Citation.is_active == True,
                        or_(
                            Citation.last_verified == None,
                            Citation.last_verified < cutoff_date
                        )
                    )
                )
                .limit(50)
            ).scalars().all()
            
            for citation in stale_citations:
                citation.verification_status = VerificationStatus.STALE
                citation.requires_reverification = True
                
                # Reduce availability score for stale citations
                citation.availability_score = max(0.5, citation.availability_score - 0.1)
            
            if stale_citations:
                self.db.commit()
                logger.info(f"Marked {len(stale_citations)} citations as stale")
            
        except Exception as e:
            logger.error(f"Error processing stale verifications: {e}")
    
    async def calculate_accuracy_metrics(
        self,
        citation_id: UUID
    ) -> Dict[str, float]:
        """
        Calculate detailed accuracy metrics for a citation.
        
        Args:
            citation_id: Citation ID
            
        Returns:
            Dictionary of metric scores
        """
        try:
            # Get all feedback for the citation
            feedback_data = self.db.execute(
                select(
                    AccuracyTracking.metric_type,
                    func.avg(AccuracyTracking.score).label('avg_score'),
                    func.count(AccuracyTracking.id).label('count'),
                    func.avg(AccuracyTracking.confidence_level).label('avg_confidence')
                )
                .where(AccuracyTracking.citation_id == citation_id)
                .group_by(AccuracyTracking.metric_type)
            ).all()
            
            metrics = {
                MetricType.ACCURACY: 0.0,
                MetricType.RELEVANCE: 0.0,
                MetricType.AVAILABILITY: 1.0,
                MetricType.COMPLETENESS: 0.0,
                MetricType.TIMELINESS: 0.0
            }
            
            for row in feedback_data:
                metrics[row.metric_type] = float(row.avg_score)
                
                # Update Prometheus metric
                accuracy_score_gauge.labels(
                    citation_id=str(citation_id),
                    metric_type=row.metric_type
                ).set(float(row.avg_score))
            
            # Calculate weighted overall score
            overall = (
                metrics[MetricType.ACCURACY] * 0.4 +
                metrics[MetricType.RELEVANCE] * 0.3 +
                metrics[MetricType.AVAILABILITY] * 0.2 +
                metrics[MetricType.COMPLETENESS] * 0.05 +
                metrics[MetricType.TIMELINESS] * 0.05
            )
            
            metrics['overall'] = overall
            
            # Cache metrics
            if self.redis:
                cache_key = f"citation:{citation_id}:metrics"
                self.redis.hset(cache_key, mapping={
                    k.value if hasattr(k, 'value') else k: v
                    for k, v in metrics.items()
                })
                self.redis.expire(cache_key, 3600)  # 1 hour TTL
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating accuracy metrics: {e}")
            raise
    
    async def submit_feedback(
        self,
        citation_id: UUID,
        metric_type: MetricType,
        score: float,
        feedback_type: FeedbackType,
        evaluator_id: UUID,
        feedback_data: Dict[str, Any] = None
    ) -> AccuracyTracking:
        """
        Submit accuracy feedback for a citation.
        
        Args:
            citation_id: Citation ID
            metric_type: Type of metric
            score: Score (0-1)
            feedback_type: Type of feedback
            evaluator_id: ID of evaluator
            feedback_data: Additional feedback data
            
        Returns:
            Accuracy tracking record
        """
        try:
            # Create tracking record
            tracking = AccuracyTracking(
                citation_id=citation_id,
                evaluator_id=evaluator_id,
                metric_type=metric_type,
                score=score,
                feedback_type=feedback_type,
                feedback_data=feedback_data or {},
                evaluated_at=datetime.utcnow(),
                confidence_level=0.8 if feedback_type == FeedbackType.EXPERT else 0.5
            )
            
            self.db.add(tracking)
            
            # Update citation scores
            citation = self.db.get(Citation, citation_id)
            if citation:
                metrics = await self.calculate_accuracy_metrics(citation_id)
                
                citation.accuracy_score = metrics.get(MetricType.ACCURACY, 0.0)
                citation.relevance_score = metrics.get(MetricType.RELEVANCE, 0.0)
                citation.availability_score = metrics.get(MetricType.AVAILABILITY, 1.0)
                citation.overall_quality_score = metrics.get('overall', 0.0)
                
                # Check if alert needed
                if citation.overall_quality_score < self.accuracy_threshold:
                    await self._create_alert(
                        AlertSeverity.WARNING,
                        f"Citation accuracy dropped after feedback: {citation.title[:50]}...",
                        citation_id=citation_id,
                        current_score=citation.overall_quality_score
                    )
            
            self.db.commit()
            
            # Update metrics
            feedback_submissions.labels(
                feedback_type=feedback_type.value,
                metric_type=metric_type.value
            ).inc()
            
            logger.info(f"Submitted {feedback_type.value} feedback for citation {citation_id}")
            return tracking
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error submitting feedback: {e}")
            raise
    
    async def get_accuracy_trends(
        self,
        citation_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get accuracy trends over time.
        
        Args:
            citation_id: Optional citation ID (None for system-wide)
            days: Number of days to analyze
            
        Returns:
            Trend data with daily averages
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            if citation_id:
                # Trends for specific citation
                query = select(
                    func.date(AccuracyTracking.evaluated_at).label('date'),
                    AccuracyTracking.metric_type,
                    func.avg(AccuracyTracking.score).label('avg_score')
                ).where(
                    and_(
                        AccuracyTracking.citation_id == citation_id,
                        AccuracyTracking.evaluated_at >= start_date
                    )
                ).group_by(
                    func.date(AccuracyTracking.evaluated_at),
                    AccuracyTracking.metric_type
                )
            else:
                # System-wide trends
                query = select(
                    func.date(Citation.updated_at).label('date'),
                    func.avg(Citation.overall_quality_score).label('avg_score')
                ).where(
                    and_(
                        Citation.is_active == True,
                        Citation.updated_at >= start_date
                    )
                ).group_by(func.date(Citation.updated_at))
            
            results = self.db.execute(query).all()
            
            # Format trends data
            trends = {}
            for row in results:
                date_str = row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date)
                if citation_id and hasattr(row, 'metric_type'):
                    if date_str not in trends:
                        trends[date_str] = {}
                    trends[date_str][row.metric_type.value] = float(row.avg_score)
                else:
                    trends[date_str] = float(row.avg_score)
            
            return {
                'citation_id': str(citation_id) if citation_id else 'system',
                'period_days': days,
                'start_date': start_date.isoformat(),
                'trends': trends
            }
            
        except Exception as e:
            logger.error(f"Error getting accuracy trends: {e}")
            raise
    
    async def generate_accuracy_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive accuracy report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Detailed accuracy report
        """
        try:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Overall system metrics
            system_metrics = self.db.execute(
                select(
                    func.avg(Citation.overall_quality_score).label('avg_accuracy'),
                    func.min(Citation.overall_quality_score).label('min_accuracy'),
                    func.max(Citation.overall_quality_score).label('max_accuracy'),
                    func.stddev(Citation.overall_quality_score).label('stddev_accuracy'),
                    func.count(Citation.id).label('total_citations')
                ).where(
                    and_(
                        Citation.is_active == True,
                        Citation.created_at >= start_date,
                        Citation.created_at <= end_date
                    )
                )
            ).first()
            
            # Accuracy by source type
            source_metrics = self.db.execute(
                select(
                    Citation.source_type,
                    func.avg(Citation.overall_quality_score).label('avg_accuracy'),
                    func.count(Citation.id).label('count')
                ).where(
                    and_(
                        Citation.is_active == True,
                        Citation.created_at >= start_date,
                        Citation.created_at <= end_date
                    )
                ).group_by(Citation.source_type)
            ).all()
            
            # Verification statistics
            verification_stats = self.db.execute(
                select(
                    VerificationLog.status,
                    func.count(VerificationLog.id).label('count'),
                    func.avg(VerificationLog.duration_ms).label('avg_duration')
                ).where(
                    and_(
                        VerificationLog.started_at >= start_date,
                        VerificationLog.started_at <= end_date
                    )
                ).group_by(VerificationLog.status)
            ).all()
            
            # Feedback statistics
            feedback_stats = self.db.execute(
                select(
                    AccuracyTracking.feedback_type,
                    AccuracyTracking.metric_type,
                    func.count(AccuracyTracking.id).label('count'),
                    func.avg(AccuracyTracking.score).label('avg_score')
                ).where(
                    and_(
                        AccuracyTracking.evaluated_at >= start_date,
                        AccuracyTracking.evaluated_at <= end_date
                    )
                ).group_by(
                    AccuracyTracking.feedback_type,
                    AccuracyTracking.metric_type
                )
            ).all()
            
            # Alert statistics
            alert_count = len([
                alert for alert in self.active_alerts.values()
                if start_date <= alert.created_at <= end_date
            ])
            
            report = {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'system_metrics': {
                    'average_accuracy': float(system_metrics.avg_accuracy or 0) * 100,
                    'min_accuracy': float(system_metrics.min_accuracy or 0) * 100,
                    'max_accuracy': float(system_metrics.max_accuracy or 0) * 100,
                    'stddev_accuracy': float(system_metrics.stddev_accuracy or 0) * 100,
                    'total_citations': system_metrics.total_citations,
                    'status': await self.check_system_accuracy()
                },
                'source_metrics': [
                    {
                        'source_type': row.source_type,
                        'average_accuracy': float(row.avg_accuracy) * 100,
                        'citation_count': row.count
                    }
                    for row in source_metrics
                ],
                'verification_stats': [
                    {
                        'status': row.status,
                        'count': row.count,
                        'avg_duration_ms': float(row.avg_duration) if row.avg_duration else 0
                    }
                    for row in verification_stats
                ],
                'feedback_stats': [
                    {
                        'feedback_type': row.feedback_type,
                        'metric_type': row.metric_type,
                        'count': row.count,
                        'average_score': float(row.avg_score) * 100
                    }
                    for row in feedback_stats
                ],
                'alert_statistics': {
                    'total_alerts': alert_count,
                    'active_alerts': len([
                        a for a in self.active_alerts.values()
                        if not a.resolved
                    ])
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating accuracy report: {e}")
            raise
    
    async def _create_alert(
        self,
        severity: AlertSeverity,
        message: str,
        citation_id: Optional[UUID] = None,
        current_score: float = 0.0
    ):
        """
        Create and send an accuracy alert.
        
        Args:
            severity: Alert severity
            message: Alert message
            citation_id: Optional citation ID
            current_score: Current accuracy score
        """
        try:
            alert = AccuracyAlert(
                severity=severity,
                message=message,
                citation_id=citation_id,
                current_score=current_score,
                threshold=self.accuracy_threshold
            )
            
            # Store alert
            alert_key = f"alert:{alert.id}"
            self.active_alerts[alert_key] = alert
            
            # Send notification
            if self.notifications:
                await self.notifications.send_alert(
                    title="Citation Accuracy Alert",
                    message=message,
                    severity=severity.value,
                    metadata={
                        'citation_id': str(citation_id) if citation_id else None,
                        'current_score': current_score,
                        'threshold': self.accuracy_threshold
                    }
                )
            
            # Log to Sentry for critical alerts
            if severity == AlertSeverity.CRITICAL:
                sentry_sdk.capture_message(
                    message,
                    level="error",
                    extras={
                        'citation_id': str(citation_id) if citation_id else None,
                        'current_score': current_score
                    }
                )
            
            # Update metric
            accuracy_threshold_violations.labels(severity=severity.value).inc()
            
            logger.warning(f"Created {severity.value} alert: {message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def resolve_alert(self, alert_id: str):
        """
        Resolve an active alert.
        
        Args:
            alert_id: Alert ID to resolve
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Resolved alert {alert_id}")