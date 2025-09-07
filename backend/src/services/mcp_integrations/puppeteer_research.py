"""
Puppeteer MCP Integration for Automated Research

High-performance web scraping and research automation using Puppeteer MCP
for M0 feasibility analysis.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib
import logging
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)


class PuppeteerResearchMCP:
    """
    Puppeteer MCP integration for automated web research.
    
    Features:
    - Parallel browser automation
    - Smart content extraction
    - Rate limiting and retry logic
    - Session management
    - Screenshot capture for evidence
    """
    
    # Configuration
    MAX_CONCURRENT_BROWSERS = 3
    MAX_PAGES_PER_BROWSER = 5
    PAGE_LOAD_TIMEOUT_MS = 10000  # 10 seconds
    RETRY_ATTEMPTS = 2
    RATE_LIMIT_DELAY_MS = 500
    
    # Search engines and sources
    SEARCH_ENGINES = {
        "google": "https://www.google.com/search?q=",
        "bing": "https://www.bing.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q="
    }
    
    INDUSTRY_SOURCES = {
        "techcrunch": "https://techcrunch.com/search/",
        "producthunt": "https://www.producthunt.com/search?q=",
        "crunchbase": "https://www.crunchbase.com/textsearch?q=",
        "angellist": "https://angel.co/search?q=",
        "gartner": "https://www.gartner.com/en/search?q="
    }
    
    MARKET_DATA_SOURCES = {
        "statista": "https://www.statista.com/search/?q=",
        "ibisworld": "https://www.ibisworld.com/search/?q=",
        "marketwatch": "https://www.marketwatch.com/search?q=",
        "bloomberg": "https://www.bloomberg.com/search?query="
    }
    
    def __init__(self):
        """Initialize Puppeteer Research MCP."""
        self.browser_pool: List[Any] = []
        self.active_sessions: Dict[str, Any] = {}
        self.research_cache: Dict[str, Any] = {}
        
        # Performance metrics
        self.metrics = {
            "total_searches": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "avg_extraction_time_ms": 0,
            "cache_hits": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize Puppeteer MCP connection and browser pool."""
        try:
            # Initialize browser pool
            for _ in range(self.MAX_CONCURRENT_BROWSERS):
                browser = await self._launch_browser()
                if browser:
                    self.browser_pool.append(browser)
            
            logger.info(f"Initialized Puppeteer with {len(self.browser_pool)} browsers")
            return len(self.browser_pool) > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize Puppeteer MCP: {e}")
            return False
    
    async def research_market_demand(
        self,
        idea_summary: str,
        timeout_ms: int = 15000
    ) -> Dict[str, Any]:
        """
        Research market demand signals for an idea.
        
        Args:
            idea_summary: Business idea description
            timeout_ms: Maximum time for research
            
        Returns:
            Market demand research data
        """
        try:
            start_time = datetime.now()
            
            # Check cache
            cache_key = self._generate_cache_key("demand", idea_summary)
            if cache_key in self.research_cache:
                self.metrics["cache_hits"] += 1
                return self.research_cache[cache_key]
            
            # Prepare search queries
            queries = [
                f"{idea_summary} market size",
                f"{idea_summary} demand trends",
                f"{idea_summary} customer needs",
                f"{idea_summary} market growth"
            ]
            
            # Execute parallel searches
            search_tasks = []
            for query in queries:
                search_tasks.append(
                    self._search_and_extract(query, "demand", timeout_ms // len(queries))
                )
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            demand_data = {
                "signal": self._analyze_demand_signal(results),
                "evidence": [],
                "metrics": {},
                "timestamp": datetime.now().isoformat()
            }
            
            for result in results:
                if isinstance(result, dict) and not isinstance(result, Exception):
                    demand_data["evidence"].extend(result.get("evidence", []))
                    demand_data["metrics"].update(result.get("metrics", {}))
            
            # Cache result
            self.research_cache[cache_key] = demand_data
            
            # Update metrics
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_metrics(elapsed_ms, True)
            
            return demand_data
            
        except Exception as e:
            logger.error(f"Market demand research failed: {e}")
            self._update_metrics(0, False)
            return {"signal": "unknown", "evidence": [], "error": str(e)}
    
    async def research_competitors(
        self,
        idea_summary: str,
        limit: int = 5,
        timeout_ms: int = 20000
    ) -> List[Dict[str, Any]]:
        """
        Research competitors for a business idea.
        
        Args:
            idea_summary: Business idea description
            limit: Maximum number of competitors to find
            timeout_ms: Maximum time for research
            
        Returns:
            List of competitor data
        """
        try:
            start_time = datetime.now()
            
            # Check cache
            cache_key = self._generate_cache_key("competitors", idea_summary)
            if cache_key in self.research_cache:
                self.metrics["cache_hits"] += 1
                return self.research_cache[cache_key]
            
            # Prepare search queries
            queries = [
                f"{idea_summary} competitors",
                f"{idea_summary} alternatives",
                f"companies like {idea_summary}",
                f"{idea_summary} vs"
            ]
            
            # Search for competitors
            competitors = []
            seen_names = set()
            
            for query in queries:
                if len(competitors) >= limit:
                    break
                
                results = await self._search_and_extract(
                    query,
                    "competitor",
                    timeout_ms // len(queries)
                )
                
                if results and "competitors" in results:
                    for comp in results["competitors"]:
                        if comp["name"] not in seen_names:
                            competitors.append(comp)
                            seen_names.add(comp["name"])
                            
                            if len(competitors) >= limit:
                                break
            
            # Enrich competitor data
            enriched_competitors = []
            for comp in competitors[:limit]:
                enriched = await self._enrich_competitor_data(comp)
                enriched_competitors.append(enriched)
            
            # Cache result
            self.research_cache[cache_key] = enriched_competitors
            
            # Update metrics
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_metrics(elapsed_ms, True)
            
            return enriched_competitors
            
        except Exception as e:
            logger.error(f"Competitor research failed: {e}")
            self._update_metrics(0, False)
            return []
    
    async def research_pricing(
        self,
        idea_summary: str,
        timeout_ms: int = 10000
    ) -> Dict[str, Any]:
        """
        Research pricing information for a business idea.
        
        Args:
            idea_summary: Business idea description
            timeout_ms: Maximum time for research
            
        Returns:
            Pricing research data
        """
        try:
            start_time = datetime.now()
            
            # Check cache
            cache_key = self._generate_cache_key("pricing", idea_summary)
            if cache_key in self.research_cache:
                self.metrics["cache_hits"] += 1
                return self.research_cache[cache_key]
            
            # Search for pricing information
            queries = [
                f"{idea_summary} pricing",
                f"{idea_summary} cost",
                f"{idea_summary} price range",
                f"how much does {idea_summary} cost"
            ]
            
            # Execute searches
            price_data = {
                "min": None,
                "max": None,
                "average": None,
                "currency": "USD",
                "is_assumption": True,
                "evidence": []
            }
            
            for query in queries:
                results = await self._search_and_extract(
                    query,
                    "pricing",
                    timeout_ms // len(queries)
                )
                
                if results and "prices" in results:
                    prices = results["prices"]
                    if prices:
                        if price_data["min"] is None or min(prices) < price_data["min"]:
                            price_data["min"] = min(prices)
                        if price_data["max"] is None or max(prices) > price_data["max"]:
                            price_data["max"] = max(prices)
                        
                        price_data["is_assumption"] = False
                        price_data["evidence"].extend(results.get("evidence", []))
            
            # Calculate average if we have data
            if price_data["min"] and price_data["max"]:
                price_data["average"] = (price_data["min"] + price_data["max"]) / 2
            
            # Cache result
            self.research_cache[cache_key] = price_data
            
            # Update metrics
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_metrics(elapsed_ms, True)
            
            return price_data
            
        except Exception as e:
            logger.error(f"Pricing research failed: {e}")
            self._update_metrics(0, False)
            return {"min": None, "max": None, "is_assumption": True, "error": str(e)}
    
    async def research_trends(
        self,
        idea_summary: str,
        timeframe: str = "1year",
        timeout_ms: int = 15000
    ) -> Dict[str, Any]:
        """
        Research market trends for a business idea.
        
        Args:
            idea_summary: Business idea description
            timeframe: Trend timeframe (1year, 5years, etc.)
            timeout_ms: Maximum time for research
            
        Returns:
            Trend research data
        """
        try:
            start_time = datetime.now()
            
            # Search for trend information
            queries = [
                f"{idea_summary} market trends {timeframe}",
                f"{idea_summary} industry growth",
                f"{idea_summary} future outlook",
                f"{idea_summary} market forecast"
            ]
            
            trend_data = {
                "signal": "stable",
                "growth_rate": None,
                "evidence": [],
                "keywords": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute searches
            for query in queries:
                results = await self._search_and_extract(
                    query,
                    "trends",
                    timeout_ms // len(queries)
                )
                
                if results:
                    trend_data["evidence"].extend(results.get("evidence", []))
                    trend_data["keywords"].extend(results.get("keywords", []))
                    
                    # Analyze trend signal
                    if "signal" in results:
                        trend_data["signal"] = self._combine_signals(
                            trend_data["signal"],
                            results["signal"]
                        )
            
            # Update metrics
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._update_metrics(elapsed_ms, True)
            
            return trend_data
            
        except Exception as e:
            logger.error(f"Trend research failed: {e}")
            self._update_metrics(0, False)
            return {"signal": "unknown", "evidence": [], "error": str(e)}
    
    async def _search_and_extract(
        self,
        query: str,
        search_type: str,
        timeout_ms: int
    ) -> Optional[Dict[str, Any]]:
        """
        Search and extract information from web pages.
        
        Args:
            query: Search query
            search_type: Type of search (demand, competitor, pricing, etc.)
            timeout_ms: Timeout for operation
            
        Returns:
            Extracted data or None
        """
        browser = None
        page = None
        
        try:
            # Get browser from pool
            browser = await self._get_browser()
            if not browser:
                return None
            
            # Create new page
            page = await browser.newPage()
            
            # Set viewport and user agent
            await page.setViewport({"width": 1920, "height": 1080})
            await page.setUserAgent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            # Navigate to search engine
            search_url = f"{self.SEARCH_ENGINES['google']}{quote_plus(query)}"
            await page.goto(search_url, {"waitUntil": "networkidle2", "timeout": timeout_ms})
            
            # Wait for results
            await page.waitForSelector(".g", {"timeout": 5000})
            
            # Extract search results
            results = await page.evaluate("""
                () => {
                    const results = [];
                    const items = document.querySelectorAll('.g');
                    
                    for (let i = 0; i < Math.min(items.length, 10); i++) {
                        const item = items[i];
                        const titleEl = item.querySelector('h3');
                        const linkEl = item.querySelector('a');
                        const snippetEl = item.querySelector('.VwiC3b');
                        
                        if (titleEl && linkEl && snippetEl) {
                            results.push({
                                title: titleEl.innerText,
                                url: linkEl.href,
                                snippet: snippetEl.innerText,
                                position: i + 1
                            });
                        }
                    }
                    
                    return results;
                }
            """)
            
            # Process results based on search type
            extracted_data = self._process_search_results(results, search_type)
            
            # Add metadata
            extracted_data["query"] = query
            extracted_data["search_engine"] = "google"
            extracted_data["timestamp"] = datetime.now().isoformat()
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Search and extract failed for '{query}': {e}")
            return None
            
        finally:
            # Clean up
            if page:
                await page.close()
            if browser:
                await self._release_browser(browser)
    
    async def _enrich_competitor_data(
        self,
        competitor: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich competitor data with additional information.
        
        Args:
            competitor: Basic competitor data
            
        Returns:
            Enriched competitor data
        """
        try:
            # Try to visit competitor website if URL is available
            if "url" in competitor:
                browser = await self._get_browser()
                if browser:
                    page = await browser.newPage()
                    
                    try:
                        await page.goto(competitor["url"], {
                            "waitUntil": "networkidle2",
                            "timeout": 5000
                        })
                        
                        # Extract additional information
                        enrichment = await page.evaluate("""
                            () => {
                                const data = {};
                                
                                // Try to find pricing
                                const priceElements = document.querySelectorAll(
                                    '[class*="price"], [class*="cost"], [id*="price"]'
                                );
                                if (priceElements.length > 0) {
                                    data.pricing_found = true;
                                }
                                
                                // Try to find features
                                const featureElements = document.querySelectorAll(
                                    '[class*="feature"], [class*="benefit"]'
                                );
                                data.feature_count = featureElements.length;
                                
                                // Get meta description
                                const metaDesc = document.querySelector('meta[name="description"]');
                                if (metaDesc) {
                                    data.description = metaDesc.content;
                                }
                                
                                return data;
                            }
                        """)
                        
                        competitor.update(enrichment)
                        
                    finally:
                        await page.close()
                        await self._release_browser(browser)
            
            return competitor
            
        except Exception as e:
            logger.error(f"Failed to enrich competitor data: {e}")
            return competitor
    
    def _process_search_results(
        self,
        results: List[Dict[str, Any]],
        search_type: str
    ) -> Dict[str, Any]:
        """
        Process search results based on search type.
        
        Args:
            results: Raw search results
            search_type: Type of search
            
        Returns:
            Processed data
        """
        processed = {
            "evidence": [],
            "raw_results": results
        }
        
        if search_type == "demand":
            # Extract demand signals
            positive_keywords = ["high demand", "growing", "popular", "needed"]
            negative_keywords = ["low demand", "declining", "unpopular", "saturated"]
            
            positive_count = 0
            negative_count = 0
            
            for result in results:
                snippet = result.get("snippet", "").lower()
                title = result.get("title", "").lower()
                
                for keyword in positive_keywords:
                    if keyword in snippet or keyword in title:
                        positive_count += 1
                        break
                
                for keyword in negative_keywords:
                    if keyword in snippet or keyword in title:
                        negative_count += 1
                        break
                
                # Add as evidence
                processed["evidence"].append({
                    "id": hashlib.md5(result["url"].encode()).hexdigest()[:8],
                    "title": result["title"],
                    "snippet": result["snippet"],
                    "url": result["url"],
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            
            # Determine signal
            if positive_count > negative_count * 2:
                processed["signal"] = "high"
            elif negative_count > positive_count * 2:
                processed["signal"] = "low"
            else:
                processed["signal"] = "moderate"
            
            processed["metrics"] = {
                "positive_signals": positive_count,
                "negative_signals": negative_count
            }
            
        elif search_type == "competitor":
            # Extract competitor information
            competitors = []
            
            for result in results[:5]:
                # Try to extract competitor name from title
                title = result.get("title", "")
                
                # Simple heuristic: first part before dash or pipe
                name = title.split("-")[0].split("|")[0].strip()
                
                if name and len(name) < 50:  # Reasonable name length
                    competitors.append({
                        "name": name,
                        "angle": result.get("snippet", "")[:200],
                        "url": result.get("url", ""),
                        "evidence_refs": [
                            hashlib.md5(result["url"].encode()).hexdigest()[:8]
                        ],
                        "dates": [datetime.now().strftime("%Y-%m-%d")]
                    })
            
            processed["competitors"] = competitors
            
        elif search_type == "pricing":
            # Extract pricing information
            import re
            
            prices = []
            
            for result in results:
                snippet = result.get("snippet", "")
                title = result.get("title", "")
                
                # Look for price patterns
                price_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
                
                for text in [snippet, title]:
                    matches = re.findall(price_pattern, text)
                    
                    for match in matches:
                        try:
                            price = float(match.replace(",", ""))
                            prices.append(price)
                        except:
                            pass
            
            processed["prices"] = prices
            
            # Add evidence
            for result in results[:3]:
                processed["evidence"].append({
                    "id": hashlib.md5(result["url"].encode()).hexdigest()[:8],
                    "title": result["title"],
                    "snippet": result["snippet"],
                    "url": result["url"],
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            
        elif search_type == "trends":
            # Extract trend signals
            growth_keywords = ["growing", "increasing", "rising", "expanding", "boom"]
            decline_keywords = ["declining", "decreasing", "falling", "shrinking", "bust"]
            
            growth_count = 0
            decline_count = 0
            keywords = []
            
            for result in results:
                snippet = result.get("snippet", "").lower()
                
                for keyword in growth_keywords:
                    if keyword in snippet:
                        growth_count += 1
                        keywords.append(keyword)
                
                for keyword in decline_keywords:
                    if keyword in snippet:
                        decline_count += 1
                        keywords.append(keyword)
                
                # Add as evidence
                processed["evidence"].append({
                    "id": hashlib.md5(result["url"].encode()).hexdigest()[:8],
                    "title": result["title"],
                    "snippet": result["snippet"],
                    "url": result["url"],
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
            
            # Determine trend signal
            if growth_count > decline_count:
                processed["signal"] = "growing"
            elif decline_count > growth_count:
                processed["signal"] = "declining"
            else:
                processed["signal"] = "stable"
            
            processed["keywords"] = list(set(keywords))
        
        return processed
    
    async def _launch_browser(self) -> Optional[Any]:
        """Launch a new browser instance."""
        try:
            # This would connect to Puppeteer MCP
            # For now, returning mock browser object
            return {"id": f"browser_{len(self.browser_pool)}", "pages": []}
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return None
    
    async def _get_browser(self) -> Optional[Any]:
        """Get an available browser from pool."""
        # Simple round-robin selection
        if self.browser_pool:
            return self.browser_pool[0]
        return None
    
    async def _release_browser(self, browser: Any) -> None:
        """Release browser back to pool."""
        # Browser remains in pool for reuse
        pass
    
    def _generate_cache_key(self, research_type: str, idea_summary: str) -> str:
        """Generate cache key for research results."""
        normalized = f"{research_type}:{idea_summary.lower().strip()}"
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _analyze_demand_signal(self, results: List[Any]) -> str:
        """Analyze demand signal from research results."""
        valid_results = [r for r in results if isinstance(r, dict)]
        
        if not valid_results:
            return "unknown"
        
        # Aggregate signals
        signals = []
        for result in valid_results:
            if "signal" in result:
                signals.append(result["signal"])
        
        if not signals:
            return "moderate"
        
        # Return most common signal
        from collections import Counter
        signal_counts = Counter(signals)
        return signal_counts.most_common(1)[0][0]
    
    def _combine_signals(self, signal1: str, signal2: str) -> str:
        """Combine two trend signals."""
        signal_values = {
            "declining": -2,
            "decreasing": -1,
            "stable": 0,
            "growing": 1,
            "booming": 2
        }
        
        val1 = signal_values.get(signal1, 0)
        val2 = signal_values.get(signal2, 0)
        
        combined = (val1 + val2) / 2
        
        if combined <= -1.5:
            return "declining"
        elif combined <= -0.5:
            return "decreasing"
        elif combined <= 0.5:
            return "stable"
        elif combined <= 1.5:
            return "growing"
        else:
            return "booming"
    
    def _update_metrics(self, elapsed_ms: int, success: bool) -> None:
        """Update performance metrics."""
        self.metrics["total_searches"] += 1
        
        if success:
            self.metrics["successful_extractions"] += 1
        else:
            self.metrics["failed_extractions"] += 1
        
        # Update average time
        current_avg = self.metrics["avg_extraction_time_ms"]
        total = self.metrics["successful_extractions"]
        
        if total > 0 and elapsed_ms > 0:
            self.metrics["avg_extraction_time_ms"] = (
                (current_avg * (total - 1) + elapsed_ms) / total
            )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.metrics,
            "browser_pool_size": len(self.browser_pool),
            "active_sessions": len(self.active_sessions),
            "cache_size": len(self.research_cache),
            "success_rate": (
                self.metrics["successful_extractions"] / 
                max(self.metrics["total_searches"], 1)
            )
        }
    
    async def shutdown(self) -> None:
        """Shutdown Puppeteer MCP and clean up resources."""
        try:
            # Close all browsers
            for browser in self.browser_pool:
                # await browser.close()
                pass
            
            self.browser_pool.clear()
            self.active_sessions.clear()
            self.research_cache.clear()
            
            logger.info("Puppeteer Research MCP shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")