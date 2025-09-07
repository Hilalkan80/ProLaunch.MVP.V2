import re
import bleach
import json
import logging
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
from html import escape

logger = logging.getLogger(__name__)

class ContentSecurity:
    def __init__(self):
        # Bleach settings for HTML sanitization
        self.ALLOWED_TAGS = [
            'p', 'br', 'span', 'div', 'strong', 'em', 'u', 'a',
            'ul', 'ol', 'li', 'code', 'pre'
        ]
        
        self.ALLOWED_ATTRIBUTES = {
            'a': ['href', 'title', 'rel'],
            'span': ['class'],
            'code': ['class'],
            'pre': ['class']
        }
        
        self.ALLOWED_STYLES: List[str] = []
        
        # Content validation settings
        self.MAX_MESSAGE_LENGTH = 4000
        self.MAX_LINKS_PER_MESSAGE = 5
        self.MAX_MENTIONS_PER_MESSAGE = 10
        
        # Patterns for detecting malicious content
        self.SUSPICIOUS_PATTERNS = [
            r'<script.*?>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onclick',
            r'onerror',
            r'onload',
            r'eval\(',
            r'document\.cookie',
            r'document\.write',
            r'localStorage',
            r'sessionStorage',
            r'\\u0000',  # Null bytes
            r'\\x00',    # Null bytes
            r'\.\./\..',  # Path traversal
        ]

        # Link validation
        self.BLOCKED_DOMAINS = set([
            'example.com',  # Add your blocked domains
            'malicious.com'
        ])
        
        # Load blocked words (profanity, spam patterns, etc.)
        self.blocked_words = set([
            'spam',
            'scam',
            # Add more blocked words
        ])

    def sanitize_message_content(
        self,
        content: str,
        allow_html: bool = False
    ) -> Tuple[str, List[str]]:
        """
        Sanitize message content and return sanitized content
        plus list of security warnings
        """
        warnings = []
        
        try:
            # Basic input validation
            if not content or not isinstance(content, str):
                return '', ['Invalid content type']
            
            # Check message length
            if len(content) > self.MAX_MESSAGE_LENGTH:
                warnings.append('Message exceeds maximum length')
                content = content[:self.MAX_MESSAGE_LENGTH]
            
            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    warnings.append(f'Suspicious pattern detected: {pattern}')
                    # Remove or escape the pattern
                    content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            
            # Sanitize HTML if allowed, otherwise escape it
            if allow_html:
                content = bleach.clean(
                    content,
                    tags=self.ALLOWED_TAGS,
                    attributes=self.ALLOWED_ATTRIBUTES,
                    styles=self.ALLOWED_STYLES,
                    strip=True
                )
            else:
                content = escape(content)
            
            # Validate links
            links = re.findall(r'https?://[^\s<>"]+', content)
            if len(links) > self.MAX_LINKS_PER_MESSAGE:
                warnings.append('Too many links in message')
                # Keep only the first MAX_LINKS_PER_MESSAGE links
                for link in links[self.MAX_LINKS_PER_MESSAGE:]:
                    content = content.replace(link, '[link removed]')
            
            # Check remaining links
            for link in links[:self.MAX_LINKS_PER_MESSAGE]:
                if not self.is_safe_link(link):
                    warnings.append(f'Potentially unsafe link detected: {link}')
                    content = content.replace(link, '[unsafe link removed]')
            
            # Check for blocked words
            for word in self.blocked_words:
                if word in content.lower():
                    warnings.append('Blocked word detected')
                    content = content.replace(word, '*' * len(word))
            
            # Additional custom validations can be added here
            
            return content, warnings

        except Exception as e:
            logger.error(f"Content sanitization error: {e}")
            return '', ['Content sanitization failed']

    def sanitize_metadata(
        self,
        metadata: Dict
    ) -> Tuple[Dict, List[str]]:
        """
        Sanitize message metadata
        """
        warnings = []
        safe_metadata = {}
        
        try:
            if not isinstance(metadata, dict):
                return {}, ['Invalid metadata type']
            
            for key, value in metadata.items():
                # Sanitize string values
                if isinstance(value, str):
                    safe_value, value_warnings = self.sanitize_message_content(
                        value,
                        allow_html=False
                    )
                    warnings.extend(value_warnings)
                    safe_metadata[key] = safe_value
                
                # Handle nested dictionaries
                elif isinstance(value, dict):
                    safe_dict, dict_warnings = self.sanitize_metadata(value)
                    warnings.extend(dict_warnings)
                    safe_metadata[key] = safe_dict
                
                # Handle lists
                elif isinstance(value, list):
                    safe_list = []
                    for item in value:
                        if isinstance(item, str):
                            safe_item, item_warnings = self.sanitize_message_content(
                                item,
                                allow_html=False
                            )
                            warnings.extend(item_warnings)
                            safe_list.append(safe_item)
                        elif isinstance(item, dict):
                            safe_dict, dict_warnings = self.sanitize_metadata(item)
                            warnings.extend(dict_warnings)
                            safe_list.append(safe_dict)
                        else:
                            safe_list.append(item)
                    safe_metadata[key] = safe_list
                
                # Pass through other types (numbers, booleans, null)
                else:
                    safe_metadata[key] = value
            
            return safe_metadata, warnings

        except Exception as e:
            logger.error(f"Metadata sanitization error: {e}")
            return {}, ['Metadata sanitization failed']

    def is_safe_link(self, url: str) -> bool:
        """
        Check if a URL is safe
        """
        try:
            parsed = urlparse(url)
            
            # Check for blocked domains
            domain = parsed.netloc.lower()
            if domain in self.BLOCKED_DOMAINS:
                return False
            
            # Check for suspicious TLDs
            if domain.split('.')[-1] in ['xyz', 'top', 'tk']:
                return False
            
            # Check protocol
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check for IP addresses
            if re.match(r'\d+\.\d+\.\d+\.\d+', domain):
                return False
            
            return True

        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    def calculate_content_score(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[int, List[str]]:
        """
        Calculate a security score for the content
        Returns score (0-100) and list of reasons
        """
        score = 100
        reasons = []
        
        try:
            # Check content length and complexity
            if len(content) < 2:
                score -= 10
                reasons.append('Content too short')
            elif len(content) > self.MAX_MESSAGE_LENGTH * 0.9:
                score -= 10
                reasons.append('Content near maximum length')
            
            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    score -= 20
                    reasons.append(f'Suspicious pattern found: {pattern}')
            
            # Check links
            links = re.findall(r'https?://[^\s<>"]+', content)
            if len(links) > self.MAX_LINKS_PER_MESSAGE:
                score -= 15
                reasons.append('Too many links')
            
            for link in links:
                if not self.is_safe_link(link):
                    score -= 15
                    reasons.append('Unsafe link detected')
            
            # Check for blocked words
            for word in self.blocked_words:
                if word in content.lower():
                    score -= 10
                    reasons.append('Blocked word detected')
            
            # Check metadata if provided
            if metadata:
                try:
                    json_str = json.dumps(metadata)
                    if len(json_str) > 1000:
                        score -= 10
                        reasons.append('Large metadata')
                    
                    if re.search(r'(eval|cookie|script|onclick)', json_str, re.I):
                        score -= 20
                        reasons.append('Suspicious metadata content')
                except:
                    score -= 15
                    reasons.append('Invalid metadata format')
            
            # Ensure score stays within 0-100
            return max(0, min(100, score)), reasons

        except Exception as e:
            logger.error(f"Content scoring error: {e}")
            return 0, ['Content scoring failed']

    async def validate_and_sanitize_message(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        allow_html: bool = False
    ) -> Tuple[str, Dict, List[str], int]:
        """
        Validate and sanitize a complete message
        Returns (safe_content, safe_metadata, warnings, security_score)
        """
        warnings = []
        
        # Sanitize content
        safe_content, content_warnings = self.sanitize_message_content(
            content,
            allow_html
        )
        warnings.extend(content_warnings)
        
        # Sanitize metadata
        safe_metadata = {}
        if metadata:
            safe_metadata, metadata_warnings = self.sanitize_metadata(metadata)
            warnings.extend(metadata_warnings)
        
        # Calculate security score
        score, score_reasons = self.calculate_content_score(
            safe_content,
            safe_metadata
        )
        warnings.extend(score_reasons)
        
        return safe_content, safe_metadata, warnings, score


# Create singleton instances
content_validator = ContentSecurity()

# Additional exports for compatibility
class ContentSecurityError(Exception):
    """Exception raised for content security violations"""
    pass

# File validator is in file_security.py
try:
    from .file_security import file_validator
except ImportError:
    file_validator = None