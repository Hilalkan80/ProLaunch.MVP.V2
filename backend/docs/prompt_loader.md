# PromptLoader System Documentation

## Overview

The PromptLoader system is a comprehensive prompt management solution that provides dynamic loading, optimization, and context injection for AI prompts. It integrates with MCP (Model Context Protocol) servers for advanced features like content optimization and persistent memory.

## Key Features

- **Dynamic Prompt Loading**: Load prompts from the `/prolaunch_prompts/` directory
- **Variable Interpolation**: Support for multiple variable placeholder styles
- **Context Injection**: Integrate context from Memory Bank MCP
- **Content Optimization**: Use Ref MCP for intelligent content compression
- **Token Budget Management**: Sophisticated token allocation strategies
- **Prompt Chains**: Load and optimize sequences of prompts
- **Caching**: Improve performance with configurable caching
- **Export/Import**: Multiple export formats (JSON, YAML, Markdown)

## Architecture

### Components

1. **PromptLoader**: Main class managing prompt templates
2. **RefMCP Integration**: Content optimization and reference extraction
3. **MemoryBankMCP Integration**: Persistent context storage and retrieval
4. **TokenOptimizer**: Token budget management and optimization
5. **Cache Layer**: Performance optimization through caching

### Directory Structure

```
prolaunch_prompts/
├── system/          # System prompts
├── chat/            # Chat interaction prompts
├── milestones/      # Milestone generation prompts
└── style/           # Style and formatting prompts
```

## Usage Examples

### Basic Prompt Loading

```python
from backend.src.ai import get_prompt_loader, PromptType

# Get the singleton instance
prompt_loader = get_prompt_loader()

# Load a prompt
result = await prompt_loader.load_prompt(
    prompt_name="greeting",
    prompt_type=PromptType.CHAT,
    variables={"user_name": "Alice"},
    inject_context=True,
    optimize=True,
    max_tokens=2000
)

print(result["prompt"])  # The processed prompt
print(result["token_count"])  # Token count
```

### Loading Prompt Chains

```python
# Load multiple prompts with shared context
results = await prompt_loader.load_prompt_chain(
    prompt_names=["initialization", "analysis", "summary"],
    shared_context={
        "project_name": "AI Assistant",
        "requirements": ["scalability", "security"]
    },
    optimize_chain=True,
    max_tokens=8000
)

for result in results:
    print(f"Prompt: {result['metadata']['name']}")
    print(f"Tokens: {result['token_count']}")
```

### Token Budget Optimization

```python
from backend.src.ai import TokenBudgetStrategy

# Optimize token allocation across prompts
allocations = await prompt_loader.optimize_token_budget(
    prompts=["system_prompt", "user_context", "task_prompt"],
    total_budget=4000,
    strategy=TokenBudgetStrategy.ADAPTIVE
)

print(allocations)
# Output: {'system_prompt': 1500, 'user_context': 1200, 'task_prompt': 1300}
```

### Prompt Validation

```python
# Validate a prompt before use
validation = await prompt_loader.validate_prompt(
    prompt_name="m1",
    prompt_type=PromptType.MILESTONE
)

if validation["valid"]:
    print("Prompt is valid")
    print(f"Required variables: {validation['info']['required_variables']}")
else:
    print(f"Errors: {validation['errors']}")
```

## API Endpoints

The PromptLoader system exposes the following API endpoints:

### Load Prompt
```http
POST /api/v1/prompts/load
Content-Type: application/json

{
    "prompt_name": "greeting",
    "prompt_type": "chat",
    "variables": {
        "user_name": "Alice"
    },
    "inject_context": true,
    "optimize": true,
    "max_tokens": 2000
}
```

### Load Prompt Chain
```http
POST /api/v1/prompts/load-chain
Content-Type: application/json

{
    "prompt_names": ["init", "process", "summary"],
    "shared_context": {
        "session_id": "123"
    },
    "optimize_chain": true,
    "max_tokens": 8000
}
```

### Validate Prompt
```http
POST /api/v1/prompts/validate
Content-Type: application/json

{
    "prompt_name": "m1",
    "prompt_type": "milestones"
}
```

### List Available Prompts
```http
GET /api/v1/prompts/list
```

### Get Prompt Metadata
```http
GET /api/v1/prompts/metadata/{prompt_type}/{prompt_name}
```

### Export Prompts
```http
POST /api/v1/prompts/export
Content-Type: application/json

{
    "output_format": "json",
    "include_metadata": true
}
```

## Prompt File Formats

### Markdown Format (.md)

```markdown
---
version: 1.0.0
priority: 8
tags: [milestone, generator]
---

# Prompt Title
_Last updated: 2025-01-15_

## Purpose
Description of the prompt

## Content
The actual prompt content with {variables}
```

### JSON Format (.json)

```json
{
    "prompt": "The prompt content with ${variables}",
    "metadata": {
        "version": "1.0.0",
        "priority": 7,
        "tags": ["chat", "interactive"]
    }
}
```

### YAML Format (.yaml)

```yaml
prompt: |
  Multi-line prompt content
  with ${variables}
metadata:
  version: 1.0.0
  priority: 9
  tags:
    - system
    - core
```

## Token Budget Management

The system provides sophisticated token budget management with multiple strategies:

### Strategies

1. **PROPORTIONAL**: Allocate based on estimated token counts
2. **PRIORITY_BASED**: Allocate based on prompt priority scores
3. **ADAPTIVE**: Dynamic adjustment based on usage patterns
4. **FIXED**: Equal allocation across all prompts

### TokenBudget Configuration

```python
from backend.src.ai import TokenBudget

# Custom token budget
budget = TokenBudget(
    total_budget=16384,      # Total available tokens
    system_reserve=2000,      # Reserved for system prompts
    context_allocation=6000,  # For context injection
    prompt_allocation=4000,   # For prompt templates
    response_reserve=4384     # Reserved for response
)

prompt_loader = PromptLoader(token_budget=budget)
```

## MCP Integrations

### Ref MCP Features

- **Content Optimization**: Compress content to fit token budgets
- **Reference Extraction**: Extract URLs, files, functions, variables
- **Deduplication**: Remove redundant content
- **Context Merging**: Intelligently merge multiple contexts

### Memory Bank MCP Features

- **Memory Storage**: Persist important context
- **Semantic Search**: Find relevant memories
- **Memory Consolidation**: Combine related memories
- **Import/Export**: Backup and restore memories

## Performance Optimization

### Caching

```python
# Configure caching
prompt_loader = PromptLoader(
    cache_enabled=True,
    cache_ttl=3600  # Cache for 1 hour
)
```

### Best Practices

1. **Use Caching**: Enable caching for frequently used prompts
2. **Optimize Chains**: Use chain optimization for multi-prompt workflows
3. **Set Token Budgets**: Define appropriate token budgets upfront
4. **Validate First**: Always validate prompts before production use
5. **Monitor Usage**: Track token usage for cost optimization

## Error Handling

The system provides comprehensive error handling:

```python
try:
    result = await prompt_loader.load_prompt("my_prompt")
except ValueError as e:
    # Prompt not found
    print(f"Error: {e}")
except Exception as e:
    # Other errors
    logger.error(f"Unexpected error: {e}")
```

## Testing

### Unit Tests

```bash
# Run unit tests
pytest backend/tests/unit/test_prompt_loader.py -v
```

### Integration Tests

```bash
# Run integration tests with MCP
pytest backend/tests/integration/test_prompt_loader_integration.py -v
```

## Configuration

### Environment Variables

```bash
# .env file
PROMPT_CACHE_TTL=3600
PROMPT_MAX_TOKENS=16384
PROMPT_CACHE_ENABLED=true
```

### Programmatic Configuration

```python
from backend.src.ai import get_prompt_loader

prompt_loader = get_prompt_loader(
    prompts_dir="custom_prompts",
    cache_enabled=True,
    cache_ttl=7200,
    token_budget=TokenBudget(total_budget=32000)
)
```

## Troubleshooting

### Common Issues

1. **Prompt Not Found**
   - Verify prompt exists in the correct directory
   - Check prompt type is correct
   - Ensure file has valid extension (.md, .txt, .json, .yaml)

2. **Token Budget Exceeded**
   - Increase max_tokens parameter
   - Enable optimization
   - Use more aggressive optimization strategy

3. **Context Injection Failed**
   - Check Memory Bank MCP connection
   - Verify memories exist for the query
   - Review memory search filters

4. **Optimization Not Working**
   - Ensure Ref MCP is properly initialized
   - Check content length exceeds target tokens
   - Verify optimization strategy is appropriate

## Future Enhancements

- **Prompt Versioning**: Track and manage prompt versions
- **A/B Testing**: Test different prompt variations
- **Analytics**: Detailed usage analytics and insights
- **Template Inheritance**: Support for prompt template inheritance
- **Dynamic Loading**: Hot-reload prompts without restart
- **Collaborative Editing**: Multi-user prompt management
- **Prompt Marketplace**: Share and discover prompts

## Support

For issues or questions:
1. Check the documentation
2. Review test cases for examples
3. Check logs for detailed error messages
4. Open an issue with reproduction steps