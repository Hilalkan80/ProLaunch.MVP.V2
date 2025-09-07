"""Add context management tables

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

def upgrade():
    # Memory Bank table
    op.create_table(
        'memory_bank',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(), sa.ForeignKey('users.id')),
        sa.Column('context_type', sa.String(50)),
        sa.Column('data', sa.JSON()),
        sa.Column('timestamp', sa.DateTime()),
        sa.Column('relevance_score', sa.Float(), default=1.0),
    )
    
    # Knowledge embeddings table with pgvector
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'knowledge_embeddings',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('content', sa.Text()),
        sa.Column('embedding', Vector(1536)),  # OpenAI embedding dimension
        sa.Column('metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )
    
    # Session context table
    op.create_table(
        'session_contexts',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(), sa.ForeignKey('users.id')),
        sa.Column('session_id', sa.String(100)),
        sa.Column('messages', sa.JSON()),
        sa.Column('token_count', sa.Integer()),
        sa.Column('updated_at', sa.DateTime()),
    )
    
    # Create indexes
    op.create_index('idx_memory_bank_user_type', 'memory_bank', ['user_id', 'context_type'])
    op.create_index('idx_session_context_session', 'session_contexts', ['session_id'])
    op.execute('CREATE INDEX idx_embedding_vector ON knowledge_embeddings USING ivfflat (embedding vector_l2_ops)')

def downgrade():
    op.drop_table('session_contexts')
    op.drop_table('knowledge_embeddings')
    op.drop_table('memory_bank')