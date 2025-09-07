markdown# ProLaunch.AI Context Management System Architecture
_Last updated: 2025-01-15_

## System Overview

The Context Management System (CMS) orchestrates data flow across all milestones, maintaining continuity and personalization throughout the user journey. It implements a three-layer context architecture with intelligent aggregation and token optimization.

## Architecture Components

### 1. Context Layers

#### Session Context (Immediate)
- **Purpose**: Maintain conversation continuity within current session
- **Scope**: Last 10 chat messages
- **Storage**: Redis with 1-hour TTL
- **Token Budget**: 800 tokens (20% of 4000 total)
- **Update Frequency**: Real-time

```python
class SessionContext:
    def __init__(self, user_id, session_id):
        self.redis_key = f"session:{user_id}:{session_id}"
        self.max_messages = 10
        self.token_limit = 800
    
    def add_message(self, message):
        # FIFO queue with token counting
        messages = self.get_messages()
        messages.append(message)
        if len(messages) > self.max_messages:
            messages.pop(0)
        self.trim_to_token_limit(messages)
        redis.set(self.redis_key, messages, ex=3600)
Journey Context (Historical)

Purpose: Aggregate milestone data and key decisions
Scope: All completed milestones, business DNA
Storage: PostgreSQL with Memory Bank MCP
Token Budget: 2000 tokens (50% of 4000 total)
Update Frequency: On milestone completion

pythonclass JourneyContext:
    def __init__(self, user_id):
        self.user_id = user_id
        self.token_limit = 2000
        
    def get_context(self, current_milestone):
        # Retrieve from Memory Bank MCP
        journey_data = memory_bank_mcp.retrieve(
            user_id=self.user_id,
            context_type="journey",
            relevant_to=current_milestone
        )
        return self.prioritize_by_relevance(journey_data)
Knowledge Context (Reference)

Purpose: Industry benchmarks, research data, supplier info
Scope: External data relevant to current milestone
Storage: PostgreSQL with vector embeddings
Token Budget: 1200 tokens (30% of 4000 total)
Update Frequency: On research completion

pythonclass KnowledgeContext:
    def __init__(self):
        self.token_limit = 1200
        
    def get_relevant_knowledge(self, query_embedding, milestone):
        # Vector similarity search
        results = postgresql_mcp.vector_search(
            embedding=query_embedding,
            similarity_threshold=0.7,
            limit=10,
            filter={"milestone": milestone}
        )
        return self.rank_by_relevance(results)
2. Context Aggregation Engine
pythonclass ContextAggregator:
    def __init__(self):
        self.total_token_budget = 4000
        self.weights = {
            "session": 0.2,    # 20% - 800 tokens
            "journey": 0.5,    # 50% - 2000 tokens
            "knowledge": 0.3   # 30% - 1200 tokens
        }
    
    def aggregate_context(self, user_id, session_id, milestone, query):
        # 1. Get all context layers
        session_ctx = SessionContext(user_id, session_id).get_messages()
        journey_ctx = JourneyContext(user_id).get_context(milestone)
        knowledge_ctx = KnowledgeContext().get_relevant_knowledge(
            query_embedding=embed(query),
            milestone=milestone
        )
        
        # 2. Apply recency weighting
        weighted_context = self.apply_recency_weights({
            "session": session_ctx,
            "journey": journey_ctx,
            "knowledge": knowledge_ctx
        })
        
        # 3. Optimize for token budget
        final_context = self.optimize_tokens(weighted_context)
        
        # 4. Cache aggregated context
        redis_mcp.cache_set(
            key=f"context:{user_id}:{milestone}",
            data=final_context,
            ttl_seconds=300
        )
        
        return final_context
    
    def apply_recency_weights(self, context):
        # Recent items get 2x weight
        for layer in context:
            for item in context[layer]:
                age_hours = (now() - item.timestamp).hours
                item.weight = 2.0 if age_hours < 24 else 1.0
        return context
3. Milestone Transition Handler
pythonclass MilestoneTransition:
    def __init__(self):
        self.dependency_map = {
            "M1": ["M0"],
            "M2": ["M0", "M1"],
            "M3": ["M0", "M1", "M2"],
            "M4": ["M1", "M3"],
            "M5": ["M2"],
            "M6": ["M5"],
            "M7": ["M5", "M6"],
            "M8": [],
            "M9": ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"]
        }
    
    def prepare_transition(self, user_id, from_milestone, to_milestone):
        # 1. Get dependencies
        required_data = self.dependency_map.get(to_milestone, [])
        
        # 2. Aggregate required context
        transition_context = {}
        for milestone in required_data:
            milestone_data = self.get_milestone_data(user_id, milestone)
            transition_context[milestone] = self.extract_key_data(milestone_data)
        
        # 3. Store in Memory Bank MCP
        memory_bank_mcp.store(
            user_id=user_id,
            context_type="transition",
            data={
                "from": from_milestone,
                "to": to_milestone,
                "context": transition_context,
                "timestamp": now()
            }
        )
        
        return transition_context
4. MCP Server Integration Points
Memory Bank MCP Integration
pythonclass MemoryBankIntegration:
    def store_milestone_completion(self, user_id, milestone, data):
        return memory_bank_mcp.store(
            action="store",
            context_type="milestone_data",
            data={
                "user_id": user_id,
                "milestone": milestone,
                "completion_data": data,
                "timestamp": now()
            }
        )
    
    def retrieve_business_dna(self, user_id):
        return memory_bank_mcp.retrieve(
            action="retrieve",
            context_type="business_dna",
            user_id=user_id
        )
PostgreSQL MCP Integration
pythonclass PostgreSQLMCPIntegration:
    def store_with_embedding(self, content, metadata):
        embedding = generate_embedding(content)
        return postgresql_mcp.execute(
            action="store_embedding",
            embedding=embedding,
            content=content,
            metadata=metadata
        )
    
    def semantic_search(self, query, filters=None):
        query_embedding = generate_embedding(query)
        return postgresql_mcp.execute(
            action="vector_search",
            query=query_embedding,
            similarity_threshold=0.7,
            limit=20,
            filters=filters
        )
Redis MCP Integration
pythonclass RedisMCPIntegration:
    def cache_context(self, key, context, ttl=300):
        return redis_mcp.execute(
            action="cache_set",
            key=key,
            data=context,
            ttl_seconds=ttl
        )
    
    def get_cached_context(self, key):
        return redis_mcp.execute(
            action="cache_get",
            key=key
        )
    
    def publish_progress(self, user_id, milestone, progress):
        return redis_mcp.execute(
            action="publish",
            channel=f"progress:{user_id}",
            data={
                "milestone": milestone,
                "progress": progress,
                "timestamp": now()
            }
        )
5. Context Flow Diagram
mermaidgraph TD
    A[User Input] --> B[Context Aggregator]
    B --> C[Session Context]
    B --> D[Journey Context]
    B --> E[Knowledge Context]
    
    C --> F[Redis MCP]
    D --> G[Memory Bank MCP]
    E --> H[PostgreSQL MCP]
    
    F --> I[Aggregated Context]
    G --> I
    H --> I
    
    I --> J[Token Optimizer]
    J --> K[Final Context]
    K --> L[LLM Prompt]
    
    L --> M[Response Generation]
    M --> N[Update Contexts]
    N --> C
    N --> D
    N --> E
6. Implementation in Architecture
Integration with Chat System
python# In /backend/src/websocket/chat_handler.py
async def handle_chat_message(user_id, session_id, message):
    # 1. Get current milestone
    milestone = get_user_current_milestone(user_id)
    
    # 2. Aggregate context
    context = ContextAggregator().aggregate_context(
        user_id=user_id,
        session_id=session_id,
        milestone=milestone,
        query=message
    )
    
    # 3. Generate response with context
    response = await generate_ai_response(
        message=message,
        context=context,
        milestone=milestone
    )
    
    # 4. Update session context
    SessionContext(user_id, session_id).add_message({
        "user": message,
        "assistant": response,
        "timestamp": now()
    })
    
    return response
Integration with Milestone System
python# In /backend/src/milestones/manager.py
def complete_milestone(user_id, milestone, data):
    # 1. Store completion data
    MemoryBankIntegration().store_milestone_completion(
        user_id=user_id,
        milestone=milestone,
        data=data
    )
    
    # 2. Update journey context
    JourneyContext(user_id).update_milestone_data(milestone, data)
    
    # 3. Prepare next milestone transition
    next_milestone = get_next_milestone(milestone)
    transition_context = MilestoneTransition().prepare_transition(
        user_id=user_id,
        from_milestone=milestone,
        to_milestone=next_milestone
    )
    
    # 4. Publish progress update
    RedisMCPIntegration().publish_progress(
        user_id=user_id,
        milestone=milestone,
        progress=100
    )
    
    return {
        "completed": milestone,
        "next": next_milestone,
        "context": transition_context
    }
7. Performance Optimizations
Caching Strategy

L1 Cache: Redis MCP for hot data (5-minute TTL)
L2 Cache: PostgreSQL for warm data
L3 Storage: S3 for cold data archival

Token Optimization
pythonclass TokenOptimizer:
    def optimize(self, context, budget=4000):
        # 1. Count current tokens
        current_tokens = count_tokens(context)
        
        if current_tokens <= budget:
            return context
        
        # 2. Prioritize by relevance scores
        prioritized = sorted(context.items(), 
                           key=lambda x: x.relevance_score, 
                           reverse=True)
        
        # 3. Truncate to budget
        optimized = []
        token_count = 0
        for item in prioritized:
            item_tokens = count_tokens(item)
            if token_count + item_tokens <= budget:
                optimized.append(item)
                token_count += item_tokens
            else:
                break
        
        return optimized
8. Monitoring & Analytics
pythonclass ContextMetrics:
    def track_context_usage(self, user_id, milestone):
        metrics = {
            "session_tokens": SessionContext(user_id).get_token_count(),
            "journey_tokens": JourneyContext(user_id).get_token_count(),
            "knowledge_tokens": KnowledgeContext().get_token_count(),
            "cache_hit_rate": self.calculate_cache_hit_rate(),
            "avg_response_time": self.calculate_avg_response_time()
        }
        
        # Send to Sentry MCP
        sentry_mcp.track_metrics(
            user_id=user_id,
            milestone=milestone,
            metrics=metrics
        )
        
        return metrics
Implementation Priority

Phase 1: Implement basic three-layer context
Phase 2: Add MCP server integrations
Phase 3: Implement token optimization
Phase 4: Add monitoring and analytics
Phase 5: Performance tuning and caching

This context management system ensures seamless data flow across all milestones while optimizing for token limits and performance.