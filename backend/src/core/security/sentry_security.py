import sentry_sdk
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from datetime import datetime
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class SecurityEventType(Enum):
    AUTH_FAILURE = "auth_failure"
    RATE_LIMIT = "rate_limit"
    CONTENT_VIOLATION = "content_violation"
    FILE_VIOLATION = "file_violation"
    WEBSOCKET_ABUSE = "websocket_abuse"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCESS_DENIED = "access_denied"
    DATA_VALIDATION = "data_validation"

class SecurityLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SentrySecurity:
    def __init__(
        self,
        dsn: str,
        environment: str,
        release: Optional[str] = None,
        traces_sample_rate: float = 0.1
    ):
        """
        Initialize Sentry with security-focused configuration
        """
        try:
            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                traces_sample_rate=traces_sample_rate,
                integrations=[
                    RedisIntegration(),
                    SqlalchemyIntegration(),
                    FastApiIntegration(),
                    AsyncioIntegration(),
                ],
                before_send=self._before_send
            )
            
            # Security monitoring settings
            self.MIN_EVENT_INTERVAL = 60  # Minimum seconds between similar events
            self.event_cache = {}
            
            logger.info("Sentry security monitoring initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            raise

    def _before_send(
        self,
        event: Dict,
        hint: Dict
    ) -> Optional[Dict]:
        """
        Process and enrich security events before sending to Sentry
        """
        try:
            # Add security context
            if 'tags' not in event:
                event['tags'] = {}
            
            if event.get('level') in ['error', 'fatal']:
                event['tags']['security_relevant'] = 'true'
            
            # Check for sensitive data
            self._scrub_sensitive_data(event)
            
            # Add additional context
            if 'extra' not in event:
                event['extra'] = {}
            
            event['extra']['security_context'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'environment': sentry_sdk.Hub.current.client.options['environment']
            }
            
            return event

        except Exception as e:
            logger.error(f"Error in before_send hook: {e}")
            return event

    def _scrub_sensitive_data(self, event: Dict) -> None:
        """
        Remove sensitive data from events
        """
        sensitive_keys = {
            'password', 'token', 'secret', 'key', 'auth',
            'cookie', 'session', 'credential'
        }
        
        def scrub_dict(d: Dict) -> None:
            for k, v in d.items():
                if isinstance(k, str):
                    if any(s in k.lower() for s in sensitive_keys):
                        d[k] = '[REDACTED]'
                if isinstance(v, dict):
                    scrub_dict(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            scrub_dict(item)
        
        if isinstance(event, dict):
            scrub_dict(event)

    async def capture_security_event(
        self,
        event_type: SecurityEventType,
        level: SecurityLevel,
        message: str,
        context: Optional[Dict] = None,
        user_id: Optional[str] = None,
        fingerprint: Optional[str] = None
    ) -> None:
        """
        Capture a security-related event
        """
        try:
            # Check event throttling
            cache_key = f"{event_type}:{fingerprint or message}"
            last_sent = self.event_cache.get(cache_key)
            now = datetime.utcnow()
            
            if last_sent and (now - last_sent).total_seconds() < self.MIN_EVENT_INTERVAL:
                return
            
            self.event_cache[cache_key] = now
            
            # Prepare event data
            with sentry_sdk.push_scope() as scope:
                # Add tags
                scope.set_tag('event_type', event_type.value)
                scope.set_tag('security_level', level.value)
                
                if fingerprint:
                    scope.fingerprint = [event_type.value, fingerprint]
                
                # Add user context
                if user_id:
                    scope.set_user({'id': user_id})
                
                # Add extra context
                if context:
                    scope.set_context('security_context', context)
                
                # Set event level
                scope.level = level.value
                
                # Capture the event
                sentry_sdk.capture_message(
                    message,
                    level=level.value
                )

        except Exception as e:
            logger.error(f"Failed to capture security event: {e}")

    async def capture_auth_failure(
        self,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """
        Capture authentication failure event
        """
        context = {
            'ip_address': ip_address,
            'failure_reason': failure_reason,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.AUTH_FAILURE,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            ip_address
        )

    async def capture_rate_limit_violation(
        self,
        message: str,
        limit_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Capture rate limit violation event
        """
        context = {
            'limit_type': limit_type,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.RATE_LIMIT,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            f"{limit_type}:{ip_address}"
        )

    async def capture_content_violation(
        self,
        message: str,
        violation_type: str,
        content_type: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Capture content security violation event
        """
        context = {
            'violation_type': violation_type,
            'content_type': content_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.CONTENT_VIOLATION,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            violation_type
        )

    async def capture_file_violation(
        self,
        message: str,
        file_type: str,
        violation_type: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Capture file security violation event
        """
        context = {
            'file_type': file_type,
            'violation_type': violation_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.FILE_VIOLATION,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            f"{file_type}:{violation_type}"
        )

    async def capture_websocket_abuse(
        self,
        message: str,
        abuse_type: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Capture WebSocket abuse event
        """
        context = {
            'abuse_type': abuse_type,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.WEBSOCKET_ABUSE,
            SecurityLevel.ERROR,
            message,
            context,
            user_id,
            f"{abuse_type}:{ip_address}"
        )

    async def capture_suspicious_activity(
        self,
        message: str,
        activity_type: str,
        severity: SecurityLevel,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """
        Capture suspicious activity event
        """
        context = {
            'activity_type': activity_type,
            'ip_address': ip_address,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity,
            message,
            context,
            user_id,
            f"{activity_type}:{ip_address}"
        )

    async def capture_access_denied(
        self,
        message: str,
        resource_type: str,
        action: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Capture access denied event
        """
        context = {
            'resource_type': resource_type,
            'action': action,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.ACCESS_DENIED,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            f"{resource_type}:{action}"
        )

    async def capture_data_validation(
        self,
        message: str,
        validation_type: str,
        details: Dict,
        user_id: Optional[str] = None
    ) -> None:
        """
        Capture data validation event
        """
        context = {
            'validation_type': validation_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.capture_security_event(
            SecurityEventType.DATA_VALIDATION,
            SecurityLevel.WARNING,
            message,
            context,
            user_id,
            validation_type
        )