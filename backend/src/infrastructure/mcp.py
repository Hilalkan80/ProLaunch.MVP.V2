"""
MCP (Model Context Protocol) integration for PostgreSQL and Puppeteer.

This module provides integration with MCP services for enhanced
citation storage and verification capabilities.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from urllib.parse import urljoin

from ..core.config import settings
from ..core.exceptions import ServiceUnavailableError, ExternalServiceError

logger = logging.getLogger(__name__)


class PostgresMCP:
    """
    PostgreSQL MCP integration for advanced database operations.
    
    Provides vector search, full-text search, and optimized queries
    for citation management.
    """
    
    def __init__(self, connection_url: str = None):
        """Initialize PostgreSQL MCP connection."""
        self.connection_url = connection_url or settings.POSTGRES_MCP_URL
        self.pool_size = 20
        self.max_overflow = 10
        self._connection = None
    
    async def connect(self):
        """Establish connection to PostgreSQL MCP."""
        try:
            # In a real implementation, this would establish a connection pool
            # For now, we'll simulate the connection
            logger.info(f"Connecting to PostgreSQL MCP at {self.connection_url}")
            self._connection = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL MCP: {e}")
            raise ServiceUnavailableError(f"PostgreSQL MCP connection failed: {e}")
    
    async def vector_search(
        self,
        query_embedding: List[float],
        table: str = "citations",
        embedding_column: str = "content_embedding",
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on citations.
        
        Args:
            query_embedding: Query vector embedding
            table: Table to search
            embedding_column: Column containing embeddings
            limit: Maximum results to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar citations with similarity scores
        """
        if not self._connection:
            await self.connect()
        
        try:
            # Simulated vector search query
            # In production, this would use pgvector extension
            query = f"""
                SELECT id, reference_id, title, excerpt,
                       1 - ({embedding_column} <-> %s) AS similarity
                FROM {table}
                WHERE 1 - ({embedding_column} <-> %s) > %s
                ORDER BY similarity DESC
                LIMIT %s
            """
            
            # Simulate results
            results = [
                {
                    'id': 'citation_1',
                    'reference_id': 'ref_20250906_0001',
                    'title': 'Sample Citation',
                    'excerpt': 'This is a sample excerpt',
                    'similarity': 0.95
                }
            ]
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise ExternalServiceError(f"Vector search failed: {e}")
    
    async def full_text_search(
        self,
        query: str,
        table: str = "citations",
        columns: List[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Perform full-text search on citations.
        
        Args:
            query: Search query
            table: Table to search
            columns: Columns to search (default: title, excerpt, context)
            limit: Maximum results to return
            
        Returns:
            List of matching citations with relevance scores
        """
        if not self._connection:
            await self.connect()
        
        columns = columns or ['title', 'excerpt', 'context']
        
        try:
            # Simulated full-text search
            # In production, this would use PostgreSQL's full-text search
            search_vector = ' || '.join([f"coalesce({col}, '')" for col in columns])
            
            query_sql = f"""
                SELECT id, reference_id, title, excerpt,
                       ts_rank(to_tsvector('english', {search_vector}),
                              plainto_tsquery('english', %s)) AS rank
                FROM {table}
                WHERE to_tsvector('english', {search_vector}) @@
                      plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """
            
            # Simulate results
            results = [
                {
                    'id': 'citation_2',
                    'reference_id': 'ref_20250906_0002',
                    'title': f'Result for: {query}',
                    'excerpt': 'Matching excerpt text',
                    'rank': 0.87
                }
            ]
            
            logger.info(f"Full-text search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            raise ExternalServiceError(f"Full-text search failed: {e}")
    
    async def bulk_insert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        on_conflict: str = "DO NOTHING"
    ) -> int:
        """
        Perform bulk insert operation.
        
        Args:
            table: Table name
            data: List of records to insert
            on_conflict: Conflict resolution strategy
            
        Returns:
            Number of records inserted
        """
        if not self._connection:
            await self.connect()
        
        if not data:
            return 0
        
        try:
            # Simulate bulk insert
            # In production, this would use COPY or multi-value INSERT
            inserted_count = len(data)
            
            logger.info(f"Bulk inserted {inserted_count} records into {table}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            raise ExternalServiceError(f"Bulk insert failed: {e}")
    
    async def execute_optimized_query(
        self,
        query: str,
        params: tuple = None
    ) -> List[Dict[str, Any]]:
        """
        Execute an optimized query with query planning.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        if not self._connection:
            await self.connect()
        
        try:
            # Simulate query execution
            # In production, this would use prepared statements and query optimization
            results = []
            
            logger.debug(f"Executed optimized query: {query[:100]}...")
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ExternalServiceError(f"Query execution failed: {e}")


class PuppeteerMCP:
    """
    Puppeteer MCP integration for web scraping and verification.
    
    Provides headless browser capabilities for citation verification,
    screenshot capture, and content extraction.
    """
    
    def __init__(self, service_url: str = None):
        """Initialize Puppeteer MCP connection."""
        self.service_url = service_url or settings.PUPPETEER_MCP_URL
        self.timeout = 30000  # 30 seconds
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout/1000)
            )
        return self.session
    
    async def verify_url(
        self,
        url: str,
        capture_screenshot: bool = True,
        extract_metadata: bool = True,
        wait_for: str = "networkidle2"
    ) -> Dict[str, Any]:
        """
        Verify a URL and extract content.
        
        Args:
            url: URL to verify
            capture_screenshot: Whether to capture screenshot
            extract_metadata: Whether to extract page metadata
            wait_for: Wait condition for page load
            
        Returns:
            Verification results including content and metadata
        """
        session = await self._get_session()
        
        try:
            # Prepare request payload
            payload = {
                'url': url,
                'options': {
                    'waitUntil': wait_for,
                    'timeout': self.timeout,
                    'captureScreenshot': capture_screenshot,
                    'extractMetadata': extract_metadata,
                    'userAgent': 'ProLaunch-Citation-Verifier/1.0'
                }
            }
            
            # Make request to Puppeteer MCP service
            async with session.post(
                urljoin(self.service_url, '/verify'),
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Process the result
                    verification_result = {
                        'url': url,
                        'status': 'verified',
                        'timestamp': datetime.utcnow().isoformat(),
                        'content': result.get('content', ''),
                        'title': result.get('title', ''),
                        'metadata': result.get('metadata', {}),
                        'screenshot_url': result.get('screenshotUrl'),
                        'content_length': len(result.get('content', '')),
                        'load_time_ms': result.get('loadTime', 0)
                    }
                    
                    logger.info(f"Successfully verified URL: {url}")
                    return verification_result
                    
                elif response.status == 404:
                    raise ExternalServiceError(f"URL not found: {url}")
                else:
                    error_text = await response.text()
                    raise ExternalServiceError(f"Verification failed: {error_text}")
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout verifying URL: {url}")
            raise ServiceUnavailableError(f"Verification timeout for URL: {url}")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error verifying URL: {e}")
            raise ServiceUnavailableError(f"HTTP error during verification: {e}")
        except Exception as e:
            logger.error(f"Unexpected error verifying URL: {e}")
            raise
    
    async def extract_content(
        self,
        url: str,
        selectors: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Extract specific content from a webpage.
        
        Args:
            url: URL to extract from
            selectors: CSS selectors for specific elements
            
        Returns:
            Extracted content
        """
        session = await self._get_session()
        
        default_selectors = {
            'title': 'title, h1',
            'author': '[rel="author"], .author, .by-author',
            'date': 'time, .date, .published',
            'content': 'main, article, .content, #content'
        }
        
        selectors = selectors or default_selectors
        
        try:
            payload = {
                'url': url,
                'selectors': selectors
            }
            
            async with session.post(
                urljoin(self.service_url, '/extract'),
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"Successfully extracted content from: {url}")
                    return result
                else:
                    error_text = await response.text()
                    raise ExternalServiceError(f"Content extraction failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            raise
    
    async def capture_screenshot(
        self,
        url: str,
        full_page: bool = True,
        viewport: Dict[str, int] = None
    ) -> str:
        """
        Capture screenshot of a webpage.
        
        Args:
            url: URL to capture
            full_page: Whether to capture full page
            viewport: Viewport dimensions
            
        Returns:
            Screenshot URL or base64 data
        """
        session = await self._get_session()
        
        viewport = viewport or {'width': 1280, 'height': 720}
        
        try:
            payload = {
                'url': url,
                'options': {
                    'fullPage': full_page,
                    'viewport': viewport,
                    'type': 'png'
                }
            }
            
            async with session.post(
                urljoin(self.service_url, '/screenshot'),
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    screenshot_url = result.get('screenshotUrl') or result.get('data')
                    
                    logger.info(f"Successfully captured screenshot of: {url}")
                    return screenshot_url
                else:
                    error_text = await response.text()
                    raise ExternalServiceError(f"Screenshot capture failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error capturing screenshot of {url}: {e}")
            raise
    
    async def check_availability(
        self,
        urls: List[str],
        concurrent_limit: int = 5
    ) -> Dict[str, bool]:
        """
        Check availability of multiple URLs concurrently.
        
        Args:
            urls: List of URLs to check
            concurrent_limit: Maximum concurrent checks
            
        Returns:
            Dictionary mapping URLs to availability status
        """
        session = await self._get_session()
        availability = {}
        
        async def check_single_url(url: str):
            try:
                async with session.head(url, allow_redirects=True) as response:
                    availability[url] = response.status < 400
            except:
                availability[url] = False
        
        # Process URLs in batches
        for i in range(0, len(urls), concurrent_limit):
            batch = urls[i:i + concurrent_limit]
            await asyncio.gather(*[check_single_url(url) for url in batch])
        
        logger.info(f"Checked availability of {len(urls)} URLs")
        return availability
    
    async def archive_content(
        self,
        url: str,
        format: str = "mhtml"
    ) -> str:
        """
        Archive webpage content for preservation.
        
        Args:
            url: URL to archive
            format: Archive format (mhtml, pdf, html)
            
        Returns:
            Archive file URL or data
        """
        session = await self._get_session()
        
        try:
            payload = {
                'url': url,
                'format': format
            }
            
            async with session.post(
                urljoin(self.service_url, '/archive'),
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    archive_url = result.get('archiveUrl')
                    
                    logger.info(f"Successfully archived content from: {url}")
                    return archive_url
                else:
                    error_text = await response.text()
                    raise ExternalServiceError(f"Content archiving failed: {error_text}")
                    
        except Exception as e:
            logger.error(f"Error archiving content from {url}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None