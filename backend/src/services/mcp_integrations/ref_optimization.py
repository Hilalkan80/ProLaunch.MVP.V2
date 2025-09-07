"""
Ref MCP Integration

Provides content optimization and reference management.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
import hashlib
import re

logger = logging.getLogger(__name__)


class RefMCP:
    """
    Integration with Ref MCP for content optimization.
    
    Ref MCP provides:
    - Content summarization
    - Reference extraction
    - Deduplication
    - Content compression
    """
    
    def __init__(self):
        self.compression_strategies = {
            "summarize": self._summarize_content,
            "extract_key_points": self._extract_key_points,
            "remove_redundancy": self._remove_redundancy,
            "compress_whitespace": self._compress_whitespace
        }
        
    async def optimize_content(
        self,
        content: str,
        max_tokens: int,
        strategy: str = "auto"
    ) -> str:
        """
        Optimize content to fit within token budget.
        
        Args:
            content: Content to optimize
            max_tokens: Maximum token count
            strategy: Optimization strategy
            
        Returns:
            Optimized content
        """
        try:
            current_tokens = self._estimate_tokens(content)
            
            # If already within budget, return as is
            if current_tokens <= max_tokens:
                return content
            
            # Choose strategy
            if strategy == "auto":
                strategy = self._select_strategy(content, current_tokens, max_tokens)
            
            # Apply strategy
            if strategy in self.compression_strategies:
                optimized = await self.compression_strategies[strategy](
                    content,
                    max_tokens
                )
                return optimized
            
            # Fallback to truncation
            return self._truncate_content(content, max_tokens)
            
        except Exception as e:
            logger.error(f"Error optimizing content: {e}")
            return content[:max_tokens * 4]  # Rough truncation
    
    async def extract_references(
        self,
        content: str
    ) -> Dict[str, List[str]]:
        """
        Extract references from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary of reference types and values
        """
        try:
            references = {
                "urls": [],
                "files": [],
                "functions": [],
                "variables": [],
                "entities": []
            }
            
            # Extract URLs
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+' 
            references["urls"] = re.findall(url_pattern, content)
            
            # Extract file paths
            file_pattern = r'[/\\][\w\-./\\]+\.\w+'
            references["files"] = re.findall(file_pattern, content)
            
            # Extract function calls (simple pattern)
            func_pattern = r'\b(\w+)\s*\('
            references["functions"] = re.findall(func_pattern, content)
            
            # Extract variable names (camelCase and snake_case)
            var_pattern = r'\b[a-z_][a-zA-Z0-9_]*\b'
            potential_vars = re.findall(var_pattern, content)
            # Filter common words
            common_words = {"the", "and", "or", "if", "else", "for", "while", "return"}
            references["variables"] = [
                v for v in potential_vars 
                if v not in common_words and len(v) > 2
            ][:20]  # Limit to 20
            
            # Extract named entities (simple approach)
            entity_pattern = r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b'
            references["entities"] = re.findall(entity_pattern, content)[:10]
            
            return references
            
        except Exception as e:
            logger.error(f"Error extracting references: {e}")
            return {}
    
    async def deduplicate_content(
        self,
        contents: List[str],
        similarity_threshold: float = 0.8
    ) -> List[str]:
        """
        Deduplicate similar content.
        
        Args:
            contents: List of content strings
            similarity_threshold: Similarity threshold for deduplication
            
        Returns:
            Deduplicated content list
        """
        try:
            if len(contents) <= 1:
                return contents
            
            # Calculate hashes and similarities
            hashes = [self._content_hash(c) for c in contents]
            unique_contents = []
            seen_hashes = set()
            
            for i, content in enumerate(contents):
                content_hash = hashes[i]
                
                # Check for exact duplicates
                if content_hash in seen_hashes:
                    continue
                
                # Check for similar content
                is_similar = False
                for unique_content in unique_contents:
                    similarity = self._calculate_similarity(content, unique_content)
                    if similarity >= similarity_threshold:
                        is_similar = True
                        break
                
                if not is_similar:
                    unique_contents.append(content)
                    seen_hashes.add(content_hash)
            
            logger.info(f"Deduplicated {len(contents)} to {len(unique_contents)} items")
            return unique_contents
            
        except Exception as e:
            logger.error(f"Error deduplicating content: {e}")
            return contents
    
    async def create_content_index(
        self,
        contents: List[Tuple[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Create an index of content for fast retrieval.
        
        Args:
            contents: List of (content, metadata) tuples
            
        Returns:
            Content index
        """
        try:
            index = {
                "entries": [],
                "keywords": {},
                "references": {},
                "statistics": {
                    "total_entries": len(contents),
                    "total_tokens": 0,
                    "unique_keywords": 0
                }
            }
            
            for content, metadata in contents:
                # Create entry
                entry_id = self._content_hash(content)
                entry = {
                    "id": entry_id,
                    "summary": content[:200],
                    "metadata": metadata,
                    "tokens": self._estimate_tokens(content),
                    "keywords": []
                }
                
                # Extract keywords
                keywords = self._extract_keywords(content)
                entry["keywords"] = keywords
                
                # Update keyword index
                for keyword in keywords:
                    if keyword not in index["keywords"]:
                        index["keywords"][keyword] = []
                    index["keywords"][keyword].append(entry_id)
                
                # Extract and index references
                refs = await self.extract_references(content)
                for ref_type, ref_values in refs.items():
                    if ref_type not in index["references"]:
                        index["references"][ref_type] = {}
                    for ref_value in ref_values:
                        if ref_value not in index["references"][ref_type]:
                            index["references"][ref_type][ref_value] = []
                        index["references"][ref_type][ref_value].append(entry_id)
                
                index["entries"].append(entry)
                index["statistics"]["total_tokens"] += entry["tokens"]
            
            index["statistics"]["unique_keywords"] = len(index["keywords"])
            
            return index
            
        except Exception as e:
            logger.error(f"Error creating content index: {e}")
            return {}
    
    async def merge_contexts(
        self,
        contexts: List[str],
        max_tokens: int
    ) -> str:
        """
        Merge multiple contexts intelligently.
        
        Args:
            contexts: List of context strings
            max_tokens: Maximum token budget
            
        Returns:
            Merged context
        """
        try:
            if not contexts:
                return ""
            
            if len(contexts) == 1:
                return await self.optimize_content(contexts[0], max_tokens)
            
            # Deduplicate first
            unique_contexts = await self.deduplicate_content(contexts)
            
            # Calculate token budget per context
            budget_per_context = max_tokens // len(unique_contexts)
            
            # Optimize each context
            optimized_contexts = []
            remaining_tokens = max_tokens
            
            for i, context in enumerate(unique_contexts):
                # Give more tokens to earlier contexts
                context_budget = budget_per_context
                if i == 0:
                    context_budget = int(budget_per_context * 1.5)
                
                context_budget = min(context_budget, remaining_tokens)
                
                optimized = await self.optimize_content(
                    context,
                    context_budget
                )
                optimized_contexts.append(optimized)
                
                remaining_tokens -= self._estimate_tokens(optimized)
                
                if remaining_tokens <= 0:
                    break
            
            # Join with separators
            return "\n---\n".join(optimized_contexts)
            
        except Exception as e:
            logger.error(f"Error merging contexts: {e}")
            return "\n".join(contexts)[:max_tokens * 4]
    
    async def _summarize_content(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Summarize content to fit token budget."""
        try:
            # Split into sentences
            sentences = re.split(r'[.!?]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return content
            
            # Calculate importance scores (simple: length and position)
            scored_sentences = []
            for i, sentence in enumerate(sentences):
                score = len(sentence) * (1 - i / len(sentences))  # Prefer longer, earlier sentences
                scored_sentences.append((score, sentence))
            
            # Sort by score and select top sentences
            scored_sentences.sort(reverse=True)
            
            summary = []
            current_tokens = 0
            
            for score, sentence in scored_sentences:
                sentence_tokens = self._estimate_tokens(sentence)
                if current_tokens + sentence_tokens <= max_tokens:
                    summary.append(sentence)
                    current_tokens += sentence_tokens
                else:
                    break
            
            # Restore original order
            summary_text = ". ".join(summary)
            if summary_text and not summary_text.endswith("."):
                summary_text += "."
            
            return summary_text
            
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            return self._truncate_content(content, max_tokens)
    
    async def _extract_key_points(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Extract key points from content."""
        try:
            # Look for bullet points, numbered lists, or key phrases
            patterns = [
                r'^\s*[-*•]\s*(.+)$',  # Bullet points
                r'^\s*\d+[.)]\s*(.+)$',  # Numbered lists
                r'^((?:Key|Important|Note|Summary|Result):.+)$',  # Key phrases
            ]
            
            key_points = []
            lines = content.split('\n')
            
            for line in lines:
                for pattern in patterns:
                    match = re.match(pattern, line, re.MULTILINE)
                    if match:
                        key_points.append(match.group(1) if match.groups() else line)
                        break
            
            # If no structured points found, extract first sentence of each paragraph
            if not key_points:
                paragraphs = content.split('\n\n')
                for para in paragraphs[:5]:  # Limit to 5 paragraphs
                    sentences = re.split(r'[.!?]+', para)
                    if sentences and sentences[0].strip():
                        key_points.append(sentences[0].strip())
            
            # Join and optimize
            result = "\n• " + "\n• ".join(key_points)
            
            if self._estimate_tokens(result) > max_tokens:
                return await self._summarize_content(result, max_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            return self._truncate_content(content, max_tokens)
    
    async def _remove_redundancy(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Remove redundant information from content."""
        try:
            # Split into sentences
            sentences = re.split(r'[.!?]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            # Remove duplicate or very similar sentences
            unique_sentences = []
            seen_hashes = set()
            
            for sentence in sentences:
                # Create normalized hash
                normalized = re.sub(r'\s+', ' ', sentence.lower())
                sentence_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
                
                if sentence_hash not in seen_hashes:
                    unique_sentences.append(sentence)
                    seen_hashes.add(sentence_hash)
            
            result = ". ".join(unique_sentences)
            if result and not result.endswith("."):
                result += "."
            
            if self._estimate_tokens(result) > max_tokens:
                return await self._summarize_content(result, max_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Error removing redundancy: {e}")
            return self._truncate_content(content, max_tokens)
    
    async def _compress_whitespace(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Compress whitespace in content."""
        try:
            # Remove extra whitespace
            compressed = re.sub(r'\s+', ' ', content)
            compressed = re.sub(r'\n\s*\n', '\n', compressed)
            compressed = compressed.strip()
            
            if self._estimate_tokens(compressed) > max_tokens:
                return self._truncate_content(compressed, max_tokens)
            
            return compressed
            
        except Exception as e:
            logger.error(f"Error compressing whitespace: {e}")
            return content
    
    def _select_strategy(
        self,
        content: str,
        current_tokens: int,
        max_tokens: int
    ) -> str:
        """Select best optimization strategy based on content."""
        compression_ratio = max_tokens / current_tokens
        
        # Heavy compression needed
        if compression_ratio < 0.3:
            return "extract_key_points"
        
        # Moderate compression
        elif compression_ratio < 0.6:
            return "summarize"
        
        # Light compression
        elif compression_ratio < 0.8:
            return "remove_redundancy"
        
        # Very light compression
        else:
            return "compress_whitespace"
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (1 token ≈ 4 characters)."""
        return len(text) // 4
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token budget."""
        max_chars = max_tokens * 4
        if len(content) <= max_chars:
            return content
        
        # Try to truncate at sentence boundary
        truncated = content[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.8:
            return truncated[:last_period + 1]
        
        return truncated + "..."
    
    def _content_hash(self, content: str) -> str:
        """Generate hash for content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two contents (simple approach)."""
        # Normalize
        norm1 = set(re.sub(r'\s+', ' ', content1.lower()).split())
        norm2 = set(re.sub(r'\s+', ' ', content2.lower()).split())
        
        # Jaccard similarity
        if not norm1 or not norm2:
            return 0.0
        
        intersection = norm1.intersection(norm2)
        union = norm1.union(norm2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        
        # Count frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Filter common words
        common_words = {
            "this", "that", "these", "those", "with", "from", 
            "have", "been", "will", "would", "could", "should"
        }
        
        keywords = [
            word for word, freq in word_freq.items()
            if word not in common_words and freq > 1
        ]
        
        # Sort by frequency and return top keywords
        keywords.sort(key=lambda w: word_freq[w], reverse=True)
        
        return keywords[:max_keywords]