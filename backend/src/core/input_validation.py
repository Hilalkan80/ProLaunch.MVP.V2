"""
Input Validation and Sanitization Module

Provides comprehensive input validation and sanitization utilities
to prevent injection attacks and ensure data integrity.
"""

import re
import html
import urllib.parse
import os
import mimetypes
import hashlib
from typing import Any, Dict, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
import bleach
import dns.resolver
from email_validator import validate_email, EmailNotValidError
from fastapi import HTTPException, status, UploadFile
import magic
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Comprehensive input validation utilities for preventing injection attacks.
    """
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|EXECUTE)\b)",
        r"(--|#|\/\*|\*\/)",  # SQL comments
        r"(\bOR\b\s*\d+\s*=\s*\d+)",  # OR 1=1
        r"(\bAND\b\s*\d+\s*=\s*\d+)",  # AND 1=1
        r"(;|\||&&)",  # Command chaining
        r"(xp_cmdshell|sp_executesql)",  # SQL Server specific
        r"(WAITFOR\s+DELAY|BENCHMARK)",  # Time-based attacks
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<applet[^>]*>",
        r"<meta[^>]*>",
        r"<link[^>]*>",
        r"<style[^>]*>.*?</style>",
        r"expression\s*\(",  # CSS expressions
        r"vbscript:",
        r"data:text/html",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",  # Shell metacharacters
        r"\$\([^)]*\)",  # Command substitution
        r"`[^`]*`",  # Backtick execution
        r"&&|\|\|",  # Command chaining
        r">\s*\/dev\/null",  # Redirection
        r"2>&1",  # Error redirection
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # Directory traversal
        r"\.\\/",  # Windows traversal
        r"%2e%2e/",  # URL encoded traversal
        r"%252e%252e/",  # Double encoded
        r"\.\.%c0%af",  # Unicode encoded
        r"\.\.%c1%9c",  # Unicode encoded
        r"/etc/passwd",  # Common target
        r"C:\\Windows",  # Windows paths
        r"file://",  # File protocol
    ]
    
    @classmethod
    def detect_sql_injection(cls, input_string: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Args:
            input_string: Input to validate
            
        Returns:
            True if SQL injection pattern detected
        """
        if not input_string:
            return False
        
        input_upper = input_string.upper()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_upper, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        
        return False
    
    @classmethod
    def detect_xss(cls, input_string: str) -> bool:
        """
        Detect potential XSS attacks.
        
        Args:
            input_string: Input to validate
            
        Returns:
            True if XSS pattern detected
        """
        if not input_string:
            return False
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
                return True
        
        return False
    
    @classmethod
    def detect_command_injection(cls, input_string: str) -> bool:
        """
        Detect potential command injection attempts.
        
        Args:
            input_string: Input to validate
            
        Returns:
            True if command injection pattern detected
        """
        if not input_string:
            return False
        
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_string):
                logger.warning(f"Command injection pattern detected: {pattern}")
                return True
        
        return False
    
    @classmethod
    def detect_path_traversal(cls, input_string: str) -> bool:
        """
        Detect potential path traversal attempts.
        
        Args:
            input_string: Input to validate
            
        Returns:
            True if path traversal pattern detected
        """
        if not input_string:
            return False
        
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, input_string, re.IGNORECASE):
                logger.warning(f"Path traversal pattern detected: {pattern}")
                return True
        
        return False
    
    @classmethod
    def validate_input(
        cls,
        input_string: str,
        max_length: int = 1000,
        allow_html: bool = False,
        check_injections: bool = True
    ) -> Tuple[bool, str, List[str]]:
        """
        Comprehensive input validation.
        
        Args:
            input_string: Input to validate
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            check_injections: Whether to check for injection attacks
            
        Returns:
            Tuple of (is_valid, sanitized_input, errors)
        """
        errors = []
        
        # Check length
        if len(input_string) > max_length:
            errors.append(f"Input exceeds maximum length of {max_length}")
        
        # Check for various injection attacks
        if check_injections:
            if cls.detect_sql_injection(input_string):
                errors.append("Potential SQL injection detected")
            
            if not allow_html and cls.detect_xss(input_string):
                errors.append("Potential XSS attack detected")
            
            if cls.detect_command_injection(input_string):
                errors.append("Potential command injection detected")
            
            if cls.detect_path_traversal(input_string):
                errors.append("Potential path traversal detected")
        
        # Sanitize input
        sanitized = InputSanitizer.sanitize_string(
            input_string,
            allow_html=allow_html,
            max_length=max_length
        )
        
        is_valid = len(errors) == 0
        
        return is_valid, sanitized, errors


class InputSanitizer:
    """
    Input sanitization utilities for cleaning user input.
    """
    
    # Allowed HTML tags for rich text (if needed)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'a', 'img'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'width', 'height']
    }
    
    @classmethod
    def sanitize_string(
        cls,
        input_string: str,
        allow_html: bool = False,
        max_length: Optional[int] = None
    ) -> str:
        """
        Sanitize user input string.
        
        Args:
            input_string: Input to sanitize
            allow_html: Whether to allow HTML
            max_length: Maximum length to enforce
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return ""
        
        # Remove null bytes
        sanitized = input_string.replace('\x00', '')
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        # Enforce max length
        if max_length:
            sanitized = sanitized[:max_length]
        
        # Handle HTML
        if allow_html:
            # Use bleach to clean HTML
            sanitized = bleach.clean(
                sanitized,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            # Escape HTML entities
            sanitized = html.escape(sanitized)
        
        # Remove control characters (except newline and tab)
        sanitized = ''.join(
            char for char in sanitized
            if char == '\n' or char == '\t' or not ord(char) < 32
        )
        
        return sanitized
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        
        # Remove leading dots (hidden files)
        filename = filename.lstrip('.')
        
        # Limit length
        name, ext = os.path.splitext(filename)
        name = name[:100]  # Limit name to 100 chars
        
        # Ensure extension is safe
        if ext:
            ext = ext.lower()
            # Remove multiple extensions
            ext = ext.split('.')[0] if '.' in ext else ext
        
        return f"{name}{ext}" if ext else name
    
    @classmethod
    def sanitize_url(cls, url: str, allowed_schemes: List[str] = None) -> Optional[str]:
        """
        Sanitize and validate URL.
        
        Args:
            url: URL to sanitize
            allowed_schemes: List of allowed URL schemes
            
        Returns:
            Sanitized URL or None if invalid
        """
        if not url:
            return None
        
        allowed_schemes = allowed_schemes or ['http', 'https']
        
        try:
            # Parse URL
            parsed = urllib.parse.urlparse(url)
            
            # Check scheme
            if parsed.scheme not in allowed_schemes:
                logger.warning(f"Invalid URL scheme: {parsed.scheme}")
                return None
            
            # Rebuild URL with only allowed components
            sanitized = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                '', '', ''  # Remove params, query, fragment for safety
            ))
            
            return sanitized
            
        except Exception as e:
            logger.error(f"URL sanitization error: {e}")
            return None
    
    @classmethod
    def sanitize_email(cls, email: str) -> Tuple[bool, Optional[str]]:
        """
        Sanitize and validate email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Tuple of (is_valid, normalized_email)
        """
        try:
            # Validate and normalize email
            validation = validate_email(email, check_deliverability=False)
            normalized = validation.normalized
            
            # Additional checks for common attack patterns
            if any(char in normalized for char in ['<', '>', '"', "'", ';']):
                return False, None
            
            return True, normalized
            
        except EmailNotValidError:
            return False, None
    
    @classmethod
    def sanitize_json(cls, data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """
        Recursively sanitize JSON data.
        
        Args:
            data: JSON data to sanitize
            max_depth: Maximum nesting depth
            
        Returns:
            Sanitized JSON data
        """
        def _sanitize_recursive(obj: Any, depth: int = 0) -> Any:
            if depth > max_depth:
                raise ValueError(f"JSON nesting exceeds maximum depth of {max_depth}")
            
            if isinstance(obj, dict):
                return {
                    cls.sanitize_string(str(k)): _sanitize_recursive(v, depth + 1)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [_sanitize_recursive(item, depth + 1) for item in obj]
            elif isinstance(obj, str):
                return cls.sanitize_string(obj)
            else:
                return obj
        
        return _sanitize_recursive(data)


class FileValidator:
    """
    File upload validation and security checks.
    """
    
    # Allowed MIME types by category
    ALLOWED_MIME_TYPES = {
        "image": [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "image/svg+xml", "image/bmp"
        ],
        "document": [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain", "text/csv"
        ],
        "video": [
            "video/mp4", "video/mpeg", "video/quicktime",
            "video/x-msvideo", "video/webm"
        ],
        "audio": [
            "audio/mpeg", "audio/wav", "audio/ogg",
            "audio/mp4", "audio/webm"
        ]
    }
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = [
        '.exe', '.dll', '.scr', '.bat', '.cmd', '.com',
        '.pif', '.vbs', '.js', '.jar', '.zip', '.rar',
        '.sh', '.app', '.deb', '.rpm', '.msi', '.dmg'
    ]
    
    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        "image": 10 * 1024 * 1024,  # 10MB
        "document": 50 * 1024 * 1024,  # 50MB
        "video": 500 * 1024 * 1024,  # 500MB
        "audio": 100 * 1024 * 1024,  # 100MB
        "default": 10 * 1024 * 1024  # 10MB
    }
    
    @classmethod
    async def validate_file_upload(
        cls,
        file: UploadFile,
        allowed_types: List[str] = None,
        max_size: Optional[int] = None,
        scan_content: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate uploaded file for security.
        
        Args:
            file: Uploaded file
            allowed_types: List of allowed file categories
            max_size: Maximum file size in bytes
            scan_content: Whether to scan file content
            
        Returns:
            Tuple of (is_valid, error_message, metadata)
        """
        metadata = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": 0
        }
        
        # Sanitize filename
        safe_filename = InputSanitizer.sanitize_filename(file.filename)
        metadata["safe_filename"] = safe_filename
        
        # Check extension
        _, ext = os.path.splitext(file.filename.lower())
        if ext in cls.DANGEROUS_EXTENSIONS:
            return False, f"Dangerous file extension: {ext}", metadata
        
        # Read file content for validation
        content = await file.read()
        file_size = len(content)
        metadata["size"] = file_size
        
        # Reset file position
        await file.seek(0)
        
        # Check file size
        if allowed_types:
            type_category = allowed_types[0] if allowed_types else "default"
            default_max_size = cls.MAX_FILE_SIZES.get(type_category, cls.MAX_FILE_SIZES["default"])
        else:
            default_max_size = cls.MAX_FILE_SIZES["default"]
        
        max_size = max_size or default_max_size
        if file_size > max_size:
            return False, f"File size exceeds maximum of {max_size} bytes", metadata
        
        # Verify MIME type using python-magic
        if scan_content:
            try:
                file_magic = magic.Magic(mime=True)
                detected_mime = file_magic.from_buffer(content[:1024])
                metadata["detected_mime"] = detected_mime
                
                # Check if MIME type is allowed
                if allowed_types:
                    allowed_mimes = []
                    for type_cat in allowed_types:
                        allowed_mimes.extend(cls.ALLOWED_MIME_TYPES.get(type_cat, []))
                    
                    if detected_mime not in allowed_mimes:
                        return False, f"File type not allowed: {detected_mime}", metadata
                
                # Check for MIME type mismatch
                if file.content_type and file.content_type != detected_mime:
                    logger.warning(f"MIME type mismatch: declared={file.content_type}, detected={detected_mime}")
                    # This could indicate an attack attempt
                    return False, "File type mismatch detected", metadata
                    
            except Exception as e:
                logger.error(f"Error detecting file type: {e}")
                return False, "Could not verify file type", metadata
        
        # Additional content scanning for malware patterns
        if scan_content:
            if cls._scan_for_malware_patterns(content):
                return False, "Suspicious content detected", metadata
        
        return True, "", metadata
    
    @classmethod
    def _scan_for_malware_patterns(cls, content: bytes) -> bool:
        """
        Scan file content for known malware patterns.
        
        Args:
            content: File content as bytes
            
        Returns:
            True if suspicious patterns detected
        """
        # Check for common malware signatures
        malware_signatures = [
            b'MZ',  # DOS/Windows executable
            b'\x7fELF',  # Linux executable
            b'%PDF-',  # PDF header (check for malicious PDFs)
        ]
        
        # Only flag executables as suspicious
        if content[:2] == b'MZ' or content[:4] == b'\x7fELF':
            return True
        
        # Check for embedded scripts in documents
        script_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'document.write',
            b'ActiveXObject'
        ]
        
        for pattern in script_patterns:
            if pattern in content[:10000]:  # Check first 10KB
                logger.warning(f"Suspicious pattern found: {pattern}")
                return True
        
        return False
    
    @classmethod
    def calculate_file_hash(cls, content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content.
        
        Args:
            content: File content
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()


class FormValidator:
    """
    Form input validation utilities.
    """
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength and requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Length check
        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")
        
        # Complexity checks
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password check
        common_passwords = [
            'password', '12345678', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein'
        ]
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, List[str]]:
        """
        Validate username format and content.
        
        Args:
            username: Username to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Length check
        if len(username) < 3:
            errors.append("Username must be at least 3 characters")
        if len(username) > 30:
            errors.append("Username must not exceed 30 characters")
        
        # Format check
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            errors.append("Username can only contain letters, numbers, hyphens, and underscores")
        
        # Reserved names check
        reserved_names = [
            'admin', 'root', 'administrator', 'system',
            'user', 'test', 'guest', 'public'
        ]
        if username.lower() in reserved_names:
            errors.append("Username is reserved")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            Tuple of (is_valid, normalized_phone)
        """
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        # Check length (international format)
        if len(digits) < 10 or len(digits) > 15:
            return False, ""
        
        # Format as international
        if len(digits) == 10:  # US number
            formatted = f"+1{digits}"
        else:
            formatted = f"+{digits}"
        
        return True, formatted