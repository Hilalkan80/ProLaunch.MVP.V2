"""Add milestone system tables

Revision ID: 001_milestone_system
Revises: 
Create Date: 2025-09-06

This migration creates the complete milestone tracking system including:
- Core milestone definitions
- User milestone progress tracking
- Milestone dependencies (DAG structure)
- Artifacts and progress logs
- Caching and analytics tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = '001_milestone_system'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create milestone system tables with proper indexes and constraints.
    """
    
    # Create milestones table (core milestone definitions)
    op.create_table(
        'milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('code', sa.String(10), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('milestone_type', sa.String(20), nullable=True, default='paid'),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True, default=30),
        sa.Column('processing_time_limit', sa.Integer(), nullable=True, default=300),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('requires_payment', sa.Boolean(), nullable=True, default=True),
        sa.Column('auto_unlock', sa.Boolean(), nullable=True, default=False),
        sa.Column('prompt_template', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    
    # Create indexes for milestones
    op.create_index('idx_milestone_code', 'milestones', ['code'])
    op.create_index('idx_milestone_order', 'milestones', ['order_index'])
    op.create_index('idx_milestone_active', 'milestones', ['is_active'])
    
    # Create milestone_dependencies table (DAG structure)
    op.create_table(
        'milestone_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dependency_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=True, default=True),
        sa.Column('minimum_completion_percentage', sa.Float(), nullable=True, default=100.0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dependency_id'], ['milestones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('milestone_id', 'dependency_id', name='uq_milestone_dependency'),
        sa.CheckConstraint('milestone_id != dependency_id', name='check_no_self_dependency')
    )
    
    # Create indexes for dependencies
    op.create_index('idx_dependency_milestone', 'milestone_dependencies', ['milestone_id'])
    op.create_index('idx_dependency_dep', 'milestone_dependencies', ['dependency_id'])
    
    # Create user_milestones table (user progress tracking)
    op.create_table(
        'user_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, default='locked'),
        sa.Column('completion_percentage', sa.Float(), nullable=True, default=0.0),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True, default=0),
        sa.Column('current_step', sa.Integer(), nullable=True, default=0),
        sa.Column('total_steps', sa.Integer(), nullable=True, default=1),
        sa.Column('checkpoint_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('user_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('feedback_rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('processing_attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'milestone_id', name='uq_user_milestone')
    )
    
    # Create indexes for user_milestones
    op.create_index('idx_user_milestone_user', 'user_milestones', ['user_id'])
    op.create_index('idx_user_milestone_status', 'user_milestones', ['status'])
    op.create_index('idx_user_milestone_completed', 'user_milestones', ['completed_at'])
    
    # Create milestone_artifacts table (template artifacts)
    op.create_table(
        'milestone_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_path', sa.String(500), nullable=True),
        sa.Column('output_format', sa.String(50), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=True, default=True),
        sa.Column('display_order', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_artifact_milestone', 'milestone_artifacts', ['milestone_id'])
    
    # Create user_milestone_artifacts table (user-generated artifacts)
    op.create_table(
        'user_milestone_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('user_milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preview_text', sa.Text(), nullable=True),
        sa.Column('generation_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('citations_used', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=False),
        sa.Column('share_token', sa.String(100), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_milestone_id'], ['user_milestones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['artifact_id'], ['milestone_artifacts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token')
    )
    
    op.create_index('idx_user_artifact_milestone', 'user_milestone_artifacts', ['user_milestone_id'])
    op.create_index('idx_user_artifact_share', 'user_milestone_artifacts', ['share_token'])
    
    # Create milestone_progress_logs table (detailed progress tracking)
    op.create_table(
        'milestone_progress_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('user_milestone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('step_number', sa.Integer(), nullable=True),
        sa.Column('completion_percentage', sa.Float(), nullable=True),
        sa.Column('time_elapsed_seconds', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_milestone_id'], ['user_milestones.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_progress_log_milestone', 'milestone_progress_logs', ['user_milestone_id'])
    op.create_index('idx_progress_log_event', 'milestone_progress_logs', ['event_type'])
    op.create_index('idx_progress_log_created', 'milestone_progress_logs', ['created_at'])
    
    # Create milestone_cache table (for optimized reads)
    op.create_table(
        'milestone_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('cache_key', sa.String(200), nullable=False),
        sa.Column('cache_type', sa.String(50), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ttl_seconds', sa.Integer(), nullable=True, default=3600),
        sa.Column('hit_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    
    op.create_index('idx_cache_key', 'milestone_cache', ['cache_key'])
    op.create_index('idx_cache_expires', 'milestone_cache', ['expires_at'])
    op.create_index('idx_cache_type', 'milestone_cache', ['cache_type'])
    
    # Insert initial milestone data
    op.execute("""
        INSERT INTO milestones (id, code, name, description, milestone_type, order_index, 
                                estimated_minutes, processing_time_limit, is_active, 
                                requires_payment, auto_unlock, prompt_template)
        VALUES 
        (gen_random_uuid(), 'M0', 'Feasibility Snapshot', 
         'Quick validation of your product idea with market viability assessment', 
         'free', 0, 5, 60, true, false, true, 
         '{"steps": ["idea_intake", "market_analysis", "viability_score"]}'::jsonb),
         
        (gen_random_uuid(), 'M1', 'Unit Economics Lite', 
         'Basic profitability analysis and cost breakdown', 
         'gateway', 1, 15, 300, true, true, false,
         '{"steps": ["cost_inputs", "pricing_analysis", "margin_calculation"]}'::jsonb),
         
        (gen_random_uuid(), 'M2', 'Deep Research Pack', 
         'Comprehensive market research with competitive analysis', 
         'paid', 2, 30, 900, true, true, false,
         '{"steps": ["competitor_research", "market_trends", "positioning"]}'::jsonb),
         
        (gen_random_uuid(), 'M3', 'Supplier Shortlist', 
         'Vetted supplier contacts with pricing and MOQ', 
         'paid', 3, 20, 600, true, true, false,
         '{"steps": ["product_specs", "supplier_search", "contact_generation"]}'::jsonb),
         
        (gen_random_uuid(), 'M4', 'Full Financial Model', 
         '36-month financial projections with scenario planning', 
         'paid', 4, 45, 1200, true, true, false,
         '{"steps": ["assumptions", "projections", "scenarios"]}'::jsonb),
         
        (gen_random_uuid(), 'M5', 'Positioning & Brand', 
         'Brand strategy and positioning framework', 
         'paid', 5, 25, 600, true, true, false,
         '{"steps": ["brand_values", "positioning", "messaging"]}'::jsonb),
         
        (gen_random_uuid(), 'M6', 'Go-to-Market Plan', 
         'Channel strategy and launch campaign planning', 
         'paid', 6, 30, 900, true, true, false,
         '{"steps": ["channel_selection", "campaign_planning", "budget_allocation"]}'::jsonb),
         
        (gen_random_uuid(), 'M7', 'Website Brief', 
         'Technical specifications and conversion optimization', 
         'paid', 7, 25, 600, true, true, false,
         '{"steps": ["site_structure", "conversion_optimization", "technical_specs"]}'::jsonb),
         
        (gen_random_uuid(), 'M8', 'Legal & Compliance', 
         'Business structure and compliance requirements', 
         'paid', 8, 20, 600, true, true, false,
         '{"steps": ["entity_selection", "compliance_review", "document_generation"]}'::jsonb),
         
        (gen_random_uuid(), 'M9', 'Launch Readiness', 
         'Final checklist and launch validation', 
         'free', 9, 10, 300, true, false, false,
         '{"steps": ["checklist_review", "gap_analysis", "launch_approval"]}'::jsonb)
    """)
    
    # Set up milestone dependencies (M1 depends on M0, M2-M8 depend on M1, M9 depends on all)
    op.execute("""
        INSERT INTO milestone_dependencies (id, milestone_id, dependency_id, is_required)
        SELECT 
            gen_random_uuid(),
            m1.id,
            m2.id,
            true
        FROM milestones m1, milestones m2
        WHERE 
            (m1.code = 'M1' AND m2.code = 'M0') OR
            (m1.code IN ('M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8') AND m2.code = 'M1') OR
            (m1.code = 'M9' AND m2.code IN ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'))
    """)


def downgrade() -> None:
    """
    Drop all milestone system tables in reverse order.
    """
    # Drop indexes first
    op.drop_index('idx_cache_type', table_name='milestone_cache')
    op.drop_index('idx_cache_expires', table_name='milestone_cache')
    op.drop_index('idx_cache_key', table_name='milestone_cache')
    
    op.drop_index('idx_progress_log_created', table_name='milestone_progress_logs')
    op.drop_index('idx_progress_log_event', table_name='milestone_progress_logs')
    op.drop_index('idx_progress_log_milestone', table_name='milestone_progress_logs')
    
    op.drop_index('idx_user_artifact_share', table_name='user_milestone_artifacts')
    op.drop_index('idx_user_artifact_milestone', table_name='user_milestone_artifacts')
    
    op.drop_index('idx_artifact_milestone', table_name='milestone_artifacts')
    
    op.drop_index('idx_user_milestone_completed', table_name='user_milestones')
    op.drop_index('idx_user_milestone_status', table_name='user_milestones')
    op.drop_index('idx_user_milestone_user', table_name='user_milestones')
    
    op.drop_index('idx_dependency_dep', table_name='milestone_dependencies')
    op.drop_index('idx_dependency_milestone', table_name='milestone_dependencies')
    
    op.drop_index('idx_milestone_active', table_name='milestones')
    op.drop_index('idx_milestone_order', table_name='milestones')
    op.drop_index('idx_milestone_code', table_name='milestones')
    
    # Drop tables in reverse dependency order
    op.drop_table('milestone_cache')
    op.drop_table('milestone_progress_logs')
    op.drop_table('user_milestone_artifacts')
    op.drop_table('milestone_artifacts')
    op.drop_table('user_milestones')
    op.drop_table('milestone_dependencies')
    op.drop_table('milestones')