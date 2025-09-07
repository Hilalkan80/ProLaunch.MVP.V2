import pytest
import uuid
from datetime import datetime, timedelta
import json
from typing import Dict, Any

pytestmark = pytest.mark.asyncio

async def test_gdpr_compliance(
    context_manager,
    sample_user,
    sample_message,
    sample_knowledge
):
    """Test GDPR compliance requirements"""
    
    user_id = sample_user['id']
    
    # 1. Add various types of data
    await context_manager.add_message(
        sample_message,
        metadata={'user_id': user_id}
    )
    
    await context_manager.add_knowledge(
        sample_knowledge['content'],
        metadata={
            'user_id': user_id,
            'personal_data': True
        }
    )
    
    # 2. Verify data access is restricted by user_id
    other_user_id = str(uuid.uuid4())
    contexts = await context_manager.get_context(
        user_id=other_user_id
    )
    
    # Should not see other user's data
    assert not any(
        user_id in str(item)
        for items in contexts.values()
        for item in items
    )
    
    # 3. Test right to be forgotten
    await context_manager.clear_user_data(user_id)
    
    # Verify data is gone
    contexts = await context_manager.get_context(
        user_id=user_id
    )
    assert not any(contexts.values())

async def test_data_retention_limits(
    context_manager,
    sample_user
):
    """Test enforcement of data retention policies"""
    
    # Add data with different retention periods
    old_date = datetime.now() - timedelta(days=100)
    
    # Session data (2 hour retention)
    old_session = {
        'timestamp': old_date.isoformat(),
        'content': 'Old session data'
    }
    await context_manager.add_message(
        old_session,
        metadata={
            'user_id': sample_user['id'],
            'timestamp': old_date
        }
    )
    
    # Journey data (7 day retention)
    old_milestone = {
        'timestamp': old_date.isoformat(),
        'content': 'Old milestone'
    }
    await context_manager.add_milestone(
        old_milestone,
        milestone='old_milestone',
        metadata={
            'user_id': sample_user['id'],
            'timestamp': old_date
        }
    )
    
    # Get current context
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    
    # Old data should be automatically pruned
    assert not any(
        'Old session data' in str(msg)
        for msg in contexts['session']
    )
    assert not any(
        'Old milestone' in str(item)
        for item in contexts['journey']
    )

async def test_data_encryption(
    context_manager,
    sample_user,
    sample_message
):
    """Test proper encryption of sensitive data"""
    
    # Add message with sensitive data
    sensitive_data = {
        **sample_message,
        'sensitive': True,
        'api_key': 'test_api_key_12345'
    }
    
    await context_manager.add_message(
        sensitive_data,
        metadata={
            'user_id': sample_user['id'],
            'sensitive': True
        }
    )
    
    # Verify data is encrypted in storage
    # Note: This requires direct database access which should be
    # done through a secure admin interface in production
    raw_data = await context_manager._get_raw_storage_data(
        user_id=sample_user['id']
    )
    
    # API key should not be visible in raw storage
    assert 'test_api_key_12345' not in str(raw_data)
    
    # But should be accessible through proper channels
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    assert any(
        'test_api_key_12345' in str(msg)
        for msg in contexts['session']
    )

async def test_injection_prevention(
    context_manager,
    sample_user
):
    """Test prevention of injection attacks"""
    
    # Test SQL injection attempt
    sql_injection = {
        'content': "'; DROP TABLE users; --"
    }
    
    # Should sanitize input
    await context_manager.add_message(
        sql_injection,
        metadata={'user_id': sample_user['id']}
    )
    
    # Test NoSQL injection attempt
    nosql_injection = {
        '$gt': ''  # MongoDB injection
    }
    
    # Should handle without error
    await context_manager.add_message(
        nosql_injection,
        metadata={'user_id': sample_user['id']}
    )
    
    # Test vector store injection
    vector_injection = {
        'content': "'); DELETE FROM knowledge_embeddings; --"
    }
    
    # Should sanitize input
    await context_manager.add_knowledge(
        vector_injection,
        metadata={'user_id': sample_user['id']}
    )
    
    # Verify system is still functional
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    assert isinstance(contexts, dict)

async def test_access_control(
    context_manager,
    sample_user
):
    """Test role-based access control"""
    
    # Add data with different access levels
    public_data = {
        'content': 'Public information',
        'access_level': 'public'
    }
    
    private_data = {
        'content': 'Private information',
        'access_level': 'private'
    }
    
    await context_manager.add_message(
        public_data,
        metadata={
            'user_id': sample_user['id'],
            'access_level': 'public'
        }
    )
    
    await context_manager.add_message(
        private_data,
        metadata={
            'user_id': sample_user['id'],
            'access_level': 'private'
        }
    )
    
    # Test public access
    contexts = await context_manager.get_context(
        user_id=str(uuid.uuid4()),  # Different user
        access_level='public'
    )
    
    # Should only see public data
    assert any(
        'Public information' in str(msg)
        for msg in contexts['session']
    )
    assert not any(
        'Private information' in str(msg)
        for msg in contexts['session']
    )

async def test_audit_logging(
    context_manager,
    sample_user,
    sample_message
):
    """Test comprehensive audit logging"""
    
    # Perform various operations
    await context_manager.add_message(
        sample_message,
        metadata={'user_id': sample_user['id']}
    )
    
    await context_manager.get_context(
        user_id=sample_user['id']
    )
    
    # Get audit logs
    audit_logs = await context_manager.get_audit_logs(
        user_id=sample_user['id']
    )
    
    # Verify all operations are logged
    assert any(
        log['operation'] == 'add_message'
        for log in audit_logs
    )
    assert any(
        log['operation'] == 'get_context'
        for log in audit_logs
    )
    
    # Verify log contents
    for log in audit_logs:
        assert 'timestamp' in log
        assert 'user_id' in log
        assert 'operation' in log
        assert 'details' in log