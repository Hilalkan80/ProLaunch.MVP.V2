"""Add vector storage for context management

Revision ID: 003
Revises: 002
Create Date: 2025-09-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add pgvector extension and create vector storage tables.
    """
    
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create context_vectors table for storing embeddings
    op.create_table(
        'context_vectors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('vector_id', sa.String(255), unique=True, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),  # Will be converted to vector type
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Convert embedding column to vector type (1536 dimensions for OpenAI embeddings)
    op.execute("""
        ALTER TABLE context_vectors 
        ALTER COLUMN embedding TYPE vector(1536) 
        USING embedding::vector(1536)
    """)
    
    # Create indexes for efficient search
    op.create_index('idx_context_vectors_user_id', 'context_vectors', ['user_id'])
    op.create_index('idx_context_vectors_metadata_gin', 'context_vectors', ['metadata'], postgresql_using='gin')
    
    # Create IVF index for vector similarity search
    op.execute("""
        CREATE INDEX idx_context_vectors_embedding_ivfflat 
        ON context_vectors 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
    
    # Create memory_bank table for long-term memory storage
    op.create_table(
        'memory_bank',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('memory_key', sa.String(500), unique=True, nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('access_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes for memory_bank
    op.create_index('idx_memory_bank_user_id', 'memory_bank', ['user_id'])
    op.create_index('idx_memory_bank_content_hash', 'memory_bank', ['content_hash'])
    op.create_index('idx_memory_bank_metadata_gin', 'memory_bank', ['metadata'], postgresql_using='gin')
    op.create_index('idx_memory_bank_created_at', 'memory_bank', ['created_at'])
    
    # Create context_layers table for storing layer states
    op.create_table(
        'context_layers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('layer_type', sa.Enum('session', 'journey', 'knowledge', name='context_layer_type'), nullable=False),
        sa.Column('entries', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('current_tokens', sa.Integer(), default=0, nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('last_optimization', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'session_id', 'layer_type', name='uq_user_session_layer')
    )
    
    # Create indexes for context_layers
    op.create_index('idx_context_layers_user_id', 'context_layers', ['user_id'])
    op.create_index('idx_context_layers_session_id', 'context_layers', ['session_id'])
    op.create_index('idx_context_layers_layer_type', 'context_layers', ['layer_type'])
    
    # Create context_metrics table for tracking usage
    op.create_table(
        'context_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('layer_type', sa.String(20), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    
    # Create indexes for context_metrics
    op.create_index('idx_context_metrics_user_id', 'context_metrics', ['user_id'])
    op.create_index('idx_context_metrics_session_id', 'context_metrics', ['session_id'])
    op.create_index('idx_context_metrics_metric_type', 'context_metrics', ['metric_type'])
    op.create_index('idx_context_metrics_created_at', 'context_metrics', ['created_at'])
    
    # Create function for automatic updated_at trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Apply trigger to tables with updated_at
    for table in ['context_vectors', 'memory_bank', 'context_layers']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at 
            BEFORE UPDATE ON {table}
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """
    Remove vector storage tables and extension.
    """
    
    # Drop triggers
    for table in ['context_vectors', 'memory_bank', 'context_layers']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop tables
    op.drop_table('context_metrics')
    op.drop_table('context_layers')
    op.drop_table('memory_bank')
    op.drop_table('context_vectors')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS context_layer_type")
    
    # Note: We don't drop the pgvector extension as it might be used by other tables