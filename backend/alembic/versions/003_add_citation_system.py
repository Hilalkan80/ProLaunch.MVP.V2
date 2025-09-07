"""Add citation system tables

Revision ID: 003
Revises: 002
Create Date: 2025-09-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create citation system tables."""
    
    # Create citations table
    op.create_table(
        'citations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reference_id', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('authors', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('publication_date', sa.DateTime(), nullable=True),
        sa.Column('access_date', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('verification_status', sa.String(20), nullable=False, default='pending'),
        sa.Column('last_verified', sa.DateTime(), nullable=True),
        sa.Column('verification_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('verification_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=[]),
        sa.Column('screenshot_url', sa.Text(), nullable=True),
        sa.Column('accuracy_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('relevance_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('availability_score', sa.Float(), nullable=False, default=1.0),
        sa.Column('overall_quality_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, default=False),
        sa.Column('requires_reverification', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_id')
    )
    
    # Create indexes for citations table
    op.create_index('idx_citation_reference', 'citations', ['reference_id'])
    op.create_index('idx_citation_url', 'citations', ['url'])
    op.create_index('idx_citation_verification', 'citations', ['verification_status', 'last_verified'])
    op.create_index('idx_citation_quality', 'citations', ['overall_quality_score'])
    op.create_index('idx_citation_usage', 'citations', ['usage_count', 'last_used'])
    
    # Add check constraints
    op.create_check_constraint(
        'check_accuracy_range',
        'citations',
        'accuracy_score >= 0 AND accuracy_score <= 1'
    )
    op.create_check_constraint(
        'check_relevance_range',
        'citations',
        'relevance_score >= 0 AND relevance_score <= 1'
    )
    op.create_check_constraint(
        'check_availability_range',
        'citations',
        'availability_score >= 0 AND availability_score <= 1'
    )
    
    # Create citation_usages table
    op.create_table(
        'citation_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('citation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_type', sa.String(20), nullable=False, default='research'),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('section', sa.String(100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, default=0.5),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['citation_id'], ['citations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('citation_id', 'content_id', 'position', name='uq_citation_content_position')
    )
    
    # Create indexes for citation_usages table
    op.create_index('idx_usage_citation', 'citation_usages', ['citation_id'])
    op.create_index('idx_usage_content', 'citation_usages', ['content_id'])
    op.create_index('idx_usage_user', 'citation_usages', ['user_id'])
    
    # Create accuracy_tracking table
    op.create_table(
        'accuracy_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('citation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evaluator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_type', sa.String(20), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False, default='user'),
        sa.Column('feedback_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('evaluated_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('evaluation_method', sa.String(50), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=False, default=0.5),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['citation_id'], ['citations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evaluator_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for accuracy_tracking table
    op.create_index('idx_accuracy_citation', 'accuracy_tracking', ['citation_id'])
    op.create_index('idx_accuracy_evaluator', 'accuracy_tracking', ['evaluator_id'])
    op.create_index('idx_accuracy_type', 'accuracy_tracking', ['metric_type', 'feedback_type'])
    
    # Add check constraints for accuracy_tracking
    op.create_check_constraint(
        'check_score_range',
        'accuracy_tracking',
        'score >= 0 AND score <= 1'
    )
    op.create_check_constraint(
        'check_confidence_range',
        'accuracy_tracking',
        'confidence_level >= 0 AND confidence_level <= 1'
    )
    
    # Create verification_logs table
    op.create_table(
        'verification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('citation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('content_matched', sa.Boolean(), nullable=True),
        sa.Column('new_content_hash', sa.String(64), nullable=True),
        sa.Column('changes_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('error_type', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('screenshot_url', sa.Text(), nullable=True),
        sa.Column('archived_content_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['citation_id'], ['citations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for verification_logs table
    op.create_index('idx_verification_citation', 'verification_logs', ['citation_id'])
    op.create_index('idx_verification_status', 'verification_logs', ['status', 'completed_at'])
    
    # Create citation_collections table
    op.create_table(
        'citation_collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, default=[]),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('citation_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True, default=[]),
        sa.Column('citation_count', sa.Integer(), nullable=False, default=0),
        sa.Column('average_quality_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for citation_collections table
    op.create_index('idx_collection_owner', 'citation_collections', ['owner_id'])
    op.create_index('idx_collection_public', 'citation_collections', ['is_public'])
    
    # Create a trigger to update citation usage count
    op.execute("""
        CREATE OR REPLACE FUNCTION update_citation_usage_count()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                UPDATE citations SET 
                    usage_count = usage_count + 1,
                    last_used = NOW()
                WHERE id = NEW.citation_id;
            ELSIF TG_OP = 'DELETE' THEN
                UPDATE citations SET 
                    usage_count = GREATEST(usage_count - 1, 0)
                WHERE id = OLD.citation_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_citation_usage_count_trigger
        AFTER INSERT OR DELETE ON citation_usages
        FOR EACH ROW
        EXECUTE FUNCTION update_citation_usage_count();
    """)
    
    # Create a trigger to update overall quality score
    op.execute("""
        CREATE OR REPLACE FUNCTION update_overall_quality_score()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.overall_quality_score = (
                0.4 * NEW.relevance_score +
                0.4 * NEW.accuracy_score +
                0.2 * NEW.availability_score
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER update_overall_quality_score_trigger
        BEFORE INSERT OR UPDATE OF relevance_score, accuracy_score, availability_score
        ON citations
        FOR EACH ROW
        EXECUTE FUNCTION update_overall_quality_score();
    """)
    
    # Add pgvector extension if not exists (for semantic search)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Add embedding column to citations for semantic search
    op.add_column(
        'citations',
        sa.Column('title_embedding', postgresql.ARRAY(sa.Float), nullable=True)
    )
    op.add_column(
        'citations',
        sa.Column('content_embedding', postgresql.ARRAY(sa.Float), nullable=True)
    )


def downgrade() -> None:
    """Drop citation system tables."""
    
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_citation_usage_count_trigger ON citation_usages;")
    op.execute("DROP FUNCTION IF EXISTS update_citation_usage_count();")
    op.execute("DROP TRIGGER IF EXISTS update_overall_quality_score_trigger ON citations;")
    op.execute("DROP FUNCTION IF EXISTS update_overall_quality_score();")
    
    # Drop tables in reverse order of dependencies
    op.drop_table('citation_collections')
    op.drop_table('verification_logs')
    op.drop_table('accuracy_tracking')
    op.drop_table('citation_usages')
    op.drop_table('citations')