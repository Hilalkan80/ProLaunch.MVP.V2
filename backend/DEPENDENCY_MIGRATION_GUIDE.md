# Dependency Migration Guide

## Overview
This guide helps migrate the codebase to the updated dependencies in requirements.txt.

## Critical Breaking Changes

### 1. Pydantic v1 → v2 Migration

#### Model Definition Changes
```python
# OLD (Pydantic v1)
from pydantic import BaseModel, validator

class User(BaseModel):
    email: str
    age: int
    
    @validator('email')
    def validate_email(cls, v):
        # validation logic
        return v
    
    class Config:
        orm_mode = True
        schema_extra = {...}

# NEW (Pydantic v2)
from pydantic import BaseModel, field_validator, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # replaces orm_mode
        json_schema_extra={...}  # replaces schema_extra
    )
    
    email: str
    age: int
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # validation logic
        return v
```

#### Key Changes:
- `Config` class → `model_config` with `ConfigDict`
- `orm_mode=True` → `from_attributes=True`
- `@validator` → `@field_validator` with `@classmethod`
- `schema_extra` → `json_schema_extra`
- `.dict()` → `.model_dump()`
- `.json()` → `.model_dump_json()`
- `parse_obj()` → `model_validate()`
- `parse_raw()` → `model_validate_json()`

### 2. FastAPI Updates

#### Response Model Changes
```python
# OLD
@app.post("/users/", response_model=User)
async def create_user(user: User):
    return user

# NEW - No changes needed for basic usage
# But if using Pydantic v2 features:
@app.post("/users/")
async def create_user(user: User) -> User:
    return user
```

### 3. SQLAlchemy v1 → v2 Migration

#### Async Session Changes
```python
# OLD (SQLAlchemy 1.4)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# NEW (SQLAlchemy 2.0)
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

async_session = async_sessionmaker(
    engine, expire_on_commit=False
)
```

#### Query Syntax
```python
# OLD
result = await session.execute(
    select(User).filter(User.email == email)
)

# NEW
result = await session.execute(
    select(User).where(User.email == email)
)
```

### 4. Redis Client Updates

The Redis client is now at v5.0.0 with improved async support:
```python
# Ensure using async methods
import redis.asyncio as redis

# Create client
client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# Use async context manager
async with client as conn:
    await conn.set('key', 'value')
    value = await conn.get('key')
```

## Migration Steps

### Step 1: Update Models
1. Search for all Pydantic models: `grep -r "from pydantic import" --include="*.py"`
2. Update each model following the Pydantic v2 syntax
3. Update validators and config classes

### Step 2: Update Database Code
1. Search for SQLAlchemy usage: `grep -r "from sqlalchemy" --include="*.py"`
2. Update session makers and query syntax
3. Test database operations thoroughly

### Step 3: Update Redis Integration
1. Verify Redis connection code uses v5.0 compatible syntax
2. Update any deprecated Redis methods
3. Test caching and real-time features

### Step 4: Test Integration
1. Run unit tests: `pytest tests/unit/ -v`
2. Run integration tests: `pytest tests/integration/ -v`
3. Test API endpoints manually or with Postman/curl

## Rollback Plan

If issues occur:
1. Keep the old requirements.txt as requirements.txt.backup
2. Revert: `cp requirements.txt.backup requirements.txt`
3. Reinstall: `pip install -r requirements.txt --force-reinstall`

## Common Issues and Solutions

### Issue: ImportError with Pydantic
**Solution**: Update imports from `pydantic` to `pydantic.v1` for compatibility mode, or fully migrate to v2.

### Issue: SQLAlchemy query failures
**Solution**: Replace `.filter()` with `.where()` in all queries.

### Issue: Redis connection errors
**Solution**: Ensure using `redis.asyncio` for async operations, not the sync client.

### Issue: FastAPI validation errors
**Solution**: Check that all Pydantic models are properly migrated to v2 syntax.

## Testing Checklist

- [ ] All Pydantic models updated to v2
- [ ] All database queries use SQLAlchemy v2 syntax
- [ ] Redis client connections work
- [ ] All API endpoints return expected responses
- [ ] Authentication and authorization work
- [ ] Background tasks and workers function
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Performance is acceptable

## Resources

- [Pydantic v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [SQLAlchemy 2.0 Migration](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [FastAPI with Pydantic v2](https://fastapi.tiangolo.com/tutorial/body/)
- [Redis-py v5.0 Changelog](https://github.com/redis/redis-py/releases/tag/v5.0.0)