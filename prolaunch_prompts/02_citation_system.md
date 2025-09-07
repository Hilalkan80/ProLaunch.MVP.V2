# Citation System Specification
_Version 1.0 - ProLaunch MVP_

## Overview
The ProLaunch Citation System provides comprehensive source tracking, verification, and accuracy monitoring for all AI-generated content. This system ensures transparency, credibility, and compliance with a target accuracy rate of 95%.

## System Architecture

### Core Components

1. **Citation Engine**
   - Automatic citation extraction and formatting
   - Real-time source validation
   - Multi-format support (web, academic, API, database)
   - Deduplication and normalization

2. **Verification Service**
   - Puppeteer-based web scraping for source verification
   - Content hash comparison for change detection
   - Availability checking with retry logic
   - Screenshot capture for visual proof

3. **Storage Layer**
   - PostgreSQL with pgvector for semantic search
   - Redis caching for frequently accessed citations
   - Full-text search capabilities
   - Version history tracking

4. **Accuracy Tracking**
   - Real-time accuracy metrics calculation
   - User feedback integration
   - Automated accuracy reports
   - Alert system for accuracy drops below 95%

## Data Models

### Citation Schema
```json
{
  "id": "uuid",
  "reference_id": "string",
  "source_type": "web|academic|api|database|document",
  "url": "string",
  "title": "string",
  "authors": ["string"],
  "publication_date": "datetime",
  "access_date": "datetime",
  "content_hash": "string",
  "excerpt": "text",
  "context": "text",
  "metadata": {
    "doi": "string",
    "isbn": "string",
    "journal": "string",
    "volume": "string",
    "issue": "string",
    "pages": "string",
    "publisher": "string"
  },
  "verification_status": "pending|verified|failed|stale",
  "last_verified": "datetime",
  "accuracy_score": "float",
  "usage_count": "integer",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Citation Usage Schema
```json
{
  "id": "uuid",
  "citation_id": "uuid",
  "content_id": "uuid",
  "content_type": "research|analysis|recommendation",
  "position": "integer",
  "context": "text",
  "user_id": "uuid",
  "created_at": "datetime"
}
```

### Accuracy Tracking Schema
```json
{
  "id": "uuid",
  "citation_id": "uuid",
  "metric_type": "relevance|accuracy|availability",
  "score": "float",
  "feedback_type": "user|automated|expert",
  "feedback_data": "json",
  "evaluated_at": "datetime",
  "evaluator_id": "uuid"
}
```

## API Endpoints

### Citation Management
- `POST /api/v1/citations` - Create new citation
- `GET /api/v1/citations/{id}` - Get citation details
- `PUT /api/v1/citations/{id}` - Update citation
- `DELETE /api/v1/citations/{id}` - Delete citation
- `GET /api/v1/citations/search` - Search citations
- `POST /api/v1/citations/batch` - Batch create citations

### Verification
- `POST /api/v1/citations/{id}/verify` - Trigger verification
- `GET /api/v1/citations/{id}/verification-status` - Check verification status
- `POST /api/v1/citations/verify-batch` - Batch verification
- `GET /api/v1/citations/stale` - Get citations needing reverification

### Accuracy Tracking
- `POST /api/v1/citations/{id}/feedback` - Submit accuracy feedback
- `GET /api/v1/citations/{id}/accuracy` - Get accuracy metrics
- `GET /api/v1/citations/accuracy-report` - System-wide accuracy report
- `GET /api/v1/citations/accuracy-alerts` - Get accuracy alerts

### Usage Analytics
- `GET /api/v1/citations/{id}/usage` - Get citation usage stats
- `GET /api/v1/citations/top-used` - Most used citations
- `GET /api/v1/citations/by-content/{content_id}` - Citations for specific content

## Citation Formats

### Inline Format
`[[ref_xxx - YYYY-MM-DD]]`

### Full Format (JSON-LD)
```json
{
  "@context": "https://schema.org",
  "@type": "CreativeWork",
  "citation": {
    "@type": "WebPage|ScholarlyArticle|Book|Dataset",
    "url": "...",
    "headline": "...",
    "datePublished": "...",
    "author": {...}
  }
}
```

### Display Formats
- **APA**: Author, A. A. (Year). Title. Source.
- **MLA**: Author. "Title." Source, Date.
- **Chicago**: Author. "Title." Source (Date).
- **Harvard**: Author Year, Title, Source.

## Verification Process

### Initial Verification
1. URL validation and normalization
2. Content fetch via Puppeteer
3. Extract metadata (title, author, date)
4. Generate content hash
5. Store screenshot
6. Calculate initial accuracy score

### Periodic Reverification
- Daily: High-usage citations (>100 uses)
- Weekly: Medium-usage citations (10-100 uses)
- Monthly: Low-usage citations (<10 uses)
- On-demand: User-triggered verification

### Verification Statuses
- **Pending**: Awaiting initial verification
- **Verified**: Successfully verified within last check period
- **Failed**: Source unavailable or content mismatch
- **Stale**: Needs reverification based on schedule

## Accuracy Tracking System

### Metrics
1. **Relevance Score** (0-1)
   - Semantic similarity to context
   - Topic alignment
   - Time relevance

2. **Factual Accuracy** (0-1)
   - Content verification
   - Cross-reference validation
   - Expert review scores

3. **Availability Score** (0-1)
   - Source accessibility
   - Link validity
   - Content persistence

### Calculation Formula
```
Overall Accuracy = (0.4 * Relevance + 0.4 * Factual + 0.2 * Availability) * 100
```

### Monitoring Thresholds
- **Green**: >= 95% accuracy
- **Yellow**: 90-94% accuracy (warning)
- **Red**: < 90% accuracy (alert)

### Feedback Integration
- User upvotes/downvotes
- Expert review submissions
- Automated fact-checking
- Community corrections

## MCP Integration

### PostgreSQL MCP
```python
# Connection configuration
MCP_CONFIG = {
    "host": "postgres-mcp",
    "port": 5432,
    "database": "citations",
    "pool_size": 20,
    "max_overflow": 10
}

# Vector similarity search
VECTOR_SEARCH_QUERY = """
SELECT id, reference_id, title, 
       excerpt <-> %s AS distance
FROM citations
ORDER BY distance
LIMIT %s
"""
```

### Puppeteer MCP
```javascript
// Verification configuration
const PUPPETEER_CONFIG = {
  headless: true,
  timeout: 30000,
  waitUntil: 'networkidle2',
  screenshot: {
    type: 'png',
    fullPage: true
  },
  userAgent: 'ProLaunch-Citation-Verifier/1.0'
}

// Verification script
async function verifyCitation(url) {
  const page = await browser.newPage();
  await page.goto(url, PUPPETEER_CONFIG);
  const content = await page.content();
  const screenshot = await page.screenshot();
  return { content, screenshot };
}
```

## Error Handling

### Retry Logic
- Initial attempt + 3 retries with exponential backoff
- Retry delays: 1s, 5s, 30s
- Circuit breaker after 5 consecutive failures

### Error Categories
1. **Network Errors**: Connection timeouts, DNS failures
2. **Content Errors**: 404, 403, parsing failures
3. **Validation Errors**: Invalid format, missing fields
4. **System Errors**: Database failures, service unavailable

### Error Responses
```json
{
  "error": {
    "code": "CITATION_VERIFICATION_FAILED",
    "message": "Unable to verify citation",
    "details": {
      "citation_id": "...",
      "reason": "source_unavailable",
      "retry_after": 3600
    }
  }
}
```

## Performance Requirements

### Response Times
- Citation creation: < 200ms
- Citation retrieval: < 50ms
- Search: < 500ms
- Verification: < 30s
- Batch operations: < 100ms per item

### Throughput
- 1000 citations/minute creation
- 10000 citations/minute retrieval
- 100 concurrent verifications
- 95% cache hit rate for popular citations

### Storage
- 10GB initial allocation
- Auto-scaling enabled
- 90-day retention for unused citations
- Infinite retention for high-usage citations

## Security Considerations

### Access Control
- Role-based permissions (admin, editor, viewer)
- API key authentication for external access
- Rate limiting per user/API key
- IP allowlisting for admin operations

### Data Protection
- Encryption at rest (AES-256)
- TLS 1.3 for data in transit
- PII redaction in logs
- GDPR compliance for EU sources

### Audit Trail
- All citation modifications logged
- User actions tracked
- Verification history maintained
- Accuracy feedback attributed

## Testing Requirements

### Unit Tests
- Model validation
- Service logic
- Utility functions
- Error handling

### Integration Tests
- Database operations
- API endpoints
- MCP integrations
- Cache operations

### Performance Tests
- Load testing (1000 concurrent users)
- Stress testing (10000 citations/minute)
- Endurance testing (24-hour run)
- Spike testing (5x normal load)

### Accuracy Tests
- Verification accuracy validation
- Scoring algorithm verification
- Feedback integration testing
- Alert threshold testing

## Monitoring and Alerting

### Metrics to Track
- Citation creation rate
- Verification success rate
- Average accuracy score
- Cache hit rate
- API response times
- Error rates by category

### Dashboards
- Real-time accuracy metrics
- Citation usage heatmap
- Verification queue status
- System health indicators

### Alerts
- Accuracy below 95%
- Verification failures > 10%
- Response time > SLA
- Database connection pool exhaustion
- Cache miss rate > 20%

## Deployment Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/citations
REDIS_URL=redis://host:6379/0

# MCP Services
PUPPETEER_MCP_URL=http://puppeteer-mcp:3000
POSTGRES_MCP_URL=http://postgres-mcp:5432

# Monitoring
SENTRY_DSN=https://...
DATADOG_API_KEY=...

# Features
ENABLE_AUTO_VERIFICATION=true
ACCURACY_THRESHOLD=0.95
MAX_RETRY_ATTEMPTS=3
```

### Docker Compose
```yaml
services:
  citation-service:
    image: prolaunch/citation-service:latest
    environment:
      - DATABASE_URL
      - REDIS_URL
    depends_on:
      - postgres
      - redis
      - puppeteer-mcp
    ports:
      - "8002:8000"
```

## Migration Plan

### Phase 1: Core Implementation (Week 1)
- Database schema creation
- Basic CRUD operations
- Simple verification

### Phase 2: MCP Integration (Week 2)
- PostgreSQL MCP setup
- Puppeteer MCP integration
- Batch operations

### Phase 3: Accuracy Tracking (Week 3)
- Scoring algorithms
- Feedback system
- Reporting dashboards

### Phase 4: Optimization (Week 4)
- Performance tuning
- Caching strategy
- Load testing

## Success Criteria

1. **Accuracy**: Maintain 95% citation accuracy
2. **Performance**: Meet all response time SLAs
3. **Reliability**: 99.9% uptime
4. **Coverage**: 100% of content has citations
5. **Verification**: 90% of citations verified within 24 hours