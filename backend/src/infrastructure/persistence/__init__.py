"""
PostgreSQL Persistence Layer for Milestone System

This package provides robust database persistence with:
- Connection pooling and management
- Transaction handling with savepoints
- Optimized query patterns
- Automatic retry logic
- Performance monitoring
"""

from .milestone_persistence import (
    MilestonePersistence,
    ConnectionPoolManager,
    TransactionManager,
    create_milestone_persistence
)

from .persistence_service import (
    PersistenceService,
    create_persistence_service
)

__all__ = [
    # Core persistence
    "MilestonePersistence",
    "ConnectionPoolManager",
    "TransactionManager",
    "create_milestone_persistence",
    
    # High-level service
    "PersistenceService",
    "create_persistence_service"
]