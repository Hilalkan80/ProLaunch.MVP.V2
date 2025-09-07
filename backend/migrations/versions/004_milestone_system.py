"""
Add milestone tracking system tables

Revision ID: 004_milestone_system
Revises: 003_context_management
Create Date: 2025-09-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '004_milestone_system'
down_revision = '003_context_management'
branch_labels = None
depends_on = None


def upgrade():
    """Create milestone system tables"""
    
    # Create milestone status enum
    milestone_status_enum = postgresql.ENUM(
        'locked', 'available', 'in_progress', 'completed', 'skipped', 'failed',
        name='milestone_status',
        create_type=True
    )
    
    # Create milestone type enum
    milestone_type_enum = postgresql.ENUM(
        'free', 'paid', 'gateway',
        name='milestone_type',
        create_type=True
    )
    
    # Create milestones table
    op.create_table(
        'milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(10), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('milestone_type', sa.String(20), default='paid'),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), default=30),
        sa.Column('processing_time_limit', sa.Integer(), default=300),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('requires_payment', sa.Boolean(), default=True),
        sa.Column('auto_unlock', sa.Boolean(), default=False),
        sa.Column('prompt_template', postgresql.JSONB()),
        sa.Column('output_schema', postgresql.JSONB()),
        sa.Column('validation_rules', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes for milestones
    op.create_index('idx_milestone_code', 'milestones', ['code'])
    op.create_index('idx_milestone_order', 'milestones', ['order_index'])
    op.create_index('idx_milestone_active', 'milestones', ['is_active'])
    
    # Create milestone_dependencies table
    op.create_table(
        'milestone_dependencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestones.id'), nullable=False),
        sa.Column('dependency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestones.id'), nullable=False),
        sa.Column('is_required', sa.Boolean(), default=True),
        sa.Column('minimum_completion_percentage', sa.Float(), default=100.0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('milestone_id', 'dependency_id', name='uq_milestone_dependency'),
        sa.CheckConstraint('milestone_id != dependency_id', name='check_no_self_dependency')
    )
    
    # Create indexes for dependencies
    op.create_index('idx_dependency_milestone', 'milestone_dependencies', ['milestone_id'])
    op.create_index('idx_dependency_dep', 'milestone_dependencies', ['dependency_id'])
    
    # Create user_milestones table
    op.create_table(
        'user_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestones.id'), nullable=False),
        sa.Column('status', sa.String(20), default='locked'),
        sa.Column('completion_percentage', sa.Float(), default=0.0),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('last_accessed_at', sa.DateTime()),
        sa.Column('time_spent_seconds', sa.Integer(), default=0),
        sa.Column('current_step', sa.Integer(), default=0),
        sa.Column('total_steps', sa.Integer(), default=1),
        sa.Column('checkpoint_data', postgresql.JSONB()),
        sa.Column('user_inputs', postgresql.JSONB()),
        sa.Column('generated_output', postgresql.JSONB()),
        sa.Column('quality_score', sa.Float()),
        sa.Column('feedback_rating', sa.Integer()),
        sa.Column('feedback_text', sa.Text()),
        sa.Column('processing_attempts', sa.Integer(), default=0),
        sa.Column('last_error', sa.Text()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'milestone_id', name='uq_user_milestone')
    )
    
    # Create indexes for user_milestones
    op.create_index('idx_user_milestone_user', 'user_milestones', ['user_id'])
    op.create_index('idx_user_milestone_status', 'user_milestones', ['status'])
    op.create_index('idx_user_milestone_completed', 'user_milestones', ['completed_at'])
    
    # Create milestone_artifacts table
    op.create_table(
        'milestone_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestones.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('artifact_type', sa.String(50)),
        sa.Column('description', sa.Text()),
        sa.Column('template_path', sa.String(500)),
        sa.Column('output_format', sa.String(50)),
        sa.Column('is_required', sa.Boolean(), default=True),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create index for artifacts
    op.create_index('idx_artifact_milestone', 'milestone_artifacts', ['milestone_id'])
    
    # Create user_milestone_artifacts table
    op.create_table(
        'user_milestone_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_milestones.id'), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestone_artifacts.id')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('artifact_type', sa.String(50)),
        sa.Column('mime_type', sa.String(100)),
        sa.Column('storage_path', sa.String(500)),
        sa.Column('file_size', sa.Integer()),
        sa.Column('checksum', sa.String(64)),
        sa.Column('content', postgresql.JSONB()),
        sa.Column('preview_text', sa.Text()),
        sa.Column('generation_metadata', postgresql.JSONB()),
        sa.Column('citations_used', postgresql.ARRAY(sa.String())),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('share_token', sa.String(100), unique=True),
        sa.Column('access_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_accessed_at', sa.DateTime())
    )
    
    # Create indexes for user artifacts
    op.create_index('idx_user_artifact_milestone', 'user_milestone_artifacts', ['user_milestone_id'])
    op.create_index('idx_user_artifact_share', 'user_milestone_artifacts', ['share_token'])
    
    # Create milestone_progress_logs table
    op.create_table(
        'milestone_progress_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_milestone_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_milestones.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_data', postgresql.JSONB()),
        sa.Column('step_number', sa.Integer()),
        sa.Column('completion_percentage', sa.Float()),
        sa.Column('time_elapsed_seconds', sa.Integer()),
        sa.Column('session_id', sa.String(100)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Create indexes for progress logs
    op.create_index('idx_progress_log_milestone', 'milestone_progress_logs', ['user_milestone_id'])
    op.create_index('idx_progress_log_event', 'milestone_progress_logs', ['event_type'])
    op.create_index('idx_progress_log_created', 'milestone_progress_logs', ['created_at'])
    
    # Create milestone_cache table
    op.create_table(
        'milestone_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cache_key', sa.String(200), unique=True, nullable=False),
        sa.Column('cache_type', sa.String(50)),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('ttl_seconds', sa.Integer(), default=3600),
        sa.Column('hit_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime())
    )
    
    # Create indexes for cache
    op.create_index('idx_cache_key', 'milestone_cache', ['cache_key'])
    op.create_index('idx_cache_expires', 'milestone_cache', ['expires_at'])
    op.create_index('idx_cache_type', 'milestone_cache', ['cache_type'])
    
    # Insert initial milestone data
    op.execute("""
        INSERT INTO milestones (id, code, name, description, milestone_type, order_index, 
                                estimated_minutes, is_active, requires_payment, auto_unlock)
        VALUES 
        (gen_random_uuid(), 'M0', 'Business Foundation', 
         'Define your business idea, target market, and value proposition', 
         'free', 0, 45, true, false, true),
        
        (gen_random_uuid(), 'M1', 'Market Research & Validation', 
         'Conduct comprehensive market research and validate your business concept', 
         'paid', 1, 60, true, true, false),
        
        (gen_random_uuid(), 'M2', 'Business Model & Strategy', 
         'Develop your business model canvas and strategic roadmap', 
         'paid', 2, 90, true, true, false),
        
        (gen_random_uuid(), 'M3', 'Financial Planning', 
         'Create financial projections, budgets, and funding strategies', 
         'paid', 3, 120, true, true, false),
        
        (gen_random_uuid(), 'M4', 'Product Development Plan', 
         'Design your MVP and product development roadmap', 
         'paid', 4, 90, true, true, false),
        
        (gen_random_uuid(), 'M5', 'Marketing & Sales Strategy', 
         'Build your go-to-market strategy and sales funnel', 
         'paid', 5, 75, true, true, false),
        
        (gen_random_uuid(), 'M6', 'Operations Planning', 
         'Plan operational workflows, supply chain, and logistics', 
         'paid', 6, 60, true, true, false),
        
        (gen_random_uuid(), 'M7', 'Legal & Compliance', 
         'Address legal structure, intellectual property, and compliance requirements', 
         'paid', 7, 45, true, true, false),
        
        (gen_random_uuid(), 'M8', 'Launch Preparation', 
         'Prepare for launch with final checklists and contingency plans', 
         'paid', 8, 60, true, true, false),
        
        (gen_random_uuid(), 'M9', 'Executive Summary', 
         'Compile a comprehensive executive summary and pitch deck', 
         'free', 9, 30, true, false, false)
    """)
    
    # Set up milestone dependencies (M0 is prerequisite for M1-M8, M1-M8 are prerequisites for M9)
    op.execute("""
        WITH milestone_ids AS (
            SELECT id, code FROM milestones
        )
        INSERT INTO milestone_dependencies (id, milestone_id, dependency_id, is_required)
        SELECT 
            gen_random_uuid(),
            m.id,
            d.id,
            true
        FROM milestone_ids m
        CROSS JOIN milestone_ids d
        WHERE 
            (m.code IN ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8') AND d.code = 'M0')
            OR (m.code = 'M9' AND d.code IN ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'))
    """)


def downgrade():
    """Drop milestone system tables"""
    
    # Drop tables in reverse order of creation
    op.drop_table('milestone_cache')
    op.drop_table('milestone_progress_logs')
    op.drop_table('user_milestone_artifacts')
    op.drop_table('milestone_artifacts')
    op.drop_table('user_milestones')
    op.drop_table('milestone_dependencies')
    op.drop_table('milestones')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS milestone_status")
    op.execute("DROP TYPE IF EXISTS milestone_type")