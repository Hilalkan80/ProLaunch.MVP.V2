"""Add M0 feasibility system tables

Revision ID: 004
Revises: 003
Create Date: 2025-09-06 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create M0 feasibility system tables."""
    
    # Create m0_feasibility_snapshots table
    op.create_table(
        'm0_feasibility_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Core idea information
        sa.Column('idea_name', sa.String(255), nullable=False),
        sa.Column('idea_summary', sa.Text(), nullable=False),
        
        # User profile snapshot
        sa.Column('user_profile', postgresql.JSONB(), nullable=False),
        
        # Viability scoring
        sa.Column('viability_score', sa.Integer(), nullable=False),
        sa.Column('score_range', sa.String(20), nullable=False),
        sa.Column('score_rationale', sa.Text(), nullable=False),
        
        # Lean plan tiles
        sa.Column('lean_tiles', postgresql.JSONB(), nullable=False),
        
        # Competitive analysis
        sa.Column('competitors', postgresql.JSONB(), nullable=False),
        
        # Price band
        sa.Column('price_band_min', sa.Float(), nullable=True),
        sa.Column('price_band_max', sa.Float(), nullable=True),
        sa.Column('price_band_currency', sa.String(3), nullable=True, server_default='USD'),
        sa.Column('price_band_is_assumption', sa.Boolean(), nullable=True, server_default='false'),
        
        # Next steps and evidence
        sa.Column('next_steps', postgresql.JSONB(), nullable=False),
        sa.Column('evidence_data', postgresql.JSONB(), nullable=False),
        
        # Analysis metadata
        sa.Column('signals', postgresql.JSONB(), nullable=False),
        sa.Column('generation_time_ms', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('max_words', sa.Integer(), nullable=True, server_default='500'),
        
        # Status and caching
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('is_cached', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('cache_key', sa.String(255), nullable=True),
        sa.Column('cached_until', sa.DateTime(), nullable=True),
        
        # Performance metrics
        sa.Column('research_time_ms', sa.Integer(), nullable=True),
        sa.Column('analysis_time_ms', sa.Integer(), nullable=True),
        sa.Column('total_api_calls', sa.Integer(), nullable=True, server_default='0'),
        
        # Version tracking
        sa.Column('prompt_version', sa.String(20), nullable=True, server_default='1.0.0'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('cache_key', name='uq_m0_cache_key'),
        sa.CheckConstraint('viability_score >= 0 AND viability_score <= 100', name='check_viability_score_range')
    )
    
    # Create indexes for m0_feasibility_snapshots
    op.create_index('idx_m0_user_created', 'm0_feasibility_snapshots', ['user_id', 'created_at'])
    op.create_index('idx_m0_viability_score', 'm0_feasibility_snapshots', ['viability_score'])
    op.create_index('idx_m0_status_cached', 'm0_feasibility_snapshots', ['status', 'is_cached'])
    op.create_index('idx_m0_cache_key', 'm0_feasibility_snapshots', ['cache_key'])
    op.create_index('idx_m0_project', 'm0_feasibility_snapshots', ['project_id'])
    
    # Create m0_research_cache table
    op.create_table(
        'm0_research_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Cache key components
        sa.Column('idea_hash', sa.String(64), nullable=False),
        sa.Column('research_query', sa.Text(), nullable=False),
        
        # Cached data
        sa.Column('search_results', postgresql.JSONB(), nullable=False),
        sa.Column('processed_evidence', postgresql.JSONB(), nullable=False),
        sa.Column('competitor_data', postgresql.JSONB(), nullable=False),
        sa.Column('market_signals', postgresql.JSONB(), nullable=False),
        
        # Cache metadata
        sa.Column('fetch_time_ms', sa.Integer(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=True, server_default='0'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['m0_feasibility_snapshots.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('idea_hash', 'research_query', name='uq_m0_research_cache')
    )
    
    # Create indexes for m0_research_cache
    op.create_index('idx_m0_research_hash_expires', 'm0_research_cache', ['idea_hash', 'expires_at'])
    op.create_index('idx_m0_research_snapshot', 'm0_research_cache', ['snapshot_id'])
    
    # Create m0_performance_logs table
    op.create_table(
        'm0_performance_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Timing breakdown
        sa.Column('total_time_ms', sa.Integer(), nullable=False),
        sa.Column('research_time_ms', sa.Integer(), nullable=False),
        sa.Column('analysis_time_ms', sa.Integer(), nullable=False),
        sa.Column('cache_lookup_time_ms', sa.Integer(), nullable=True),
        sa.Column('db_time_ms', sa.Integer(), nullable=True),
        
        # Resource usage
        sa.Column('api_calls', postgresql.JSONB(), nullable=False),
        sa.Column('cache_hits', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('cache_misses', sa.Integer(), nullable=True, server_default='0'),
        
        # Optimization flags
        sa.Column('used_cache', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('parallel_research', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('batch_processing', sa.Boolean(), nullable=True, server_default='true'),
        
        # Error tracking
        sa.Column('had_errors', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['m0_feasibility_snapshots.id'], ondelete='CASCADE')
    )
    
    # Create indexes for m0_performance_logs
    op.create_index('idx_m0_perf_total_time', 'm0_performance_logs', ['total_time_ms'])
    op.create_index('idx_m0_perf_snapshot', 'm0_performance_logs', ['snapshot_id'])
    
    # Add trigger for updated_at columns
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Add triggers to each table
    for table in ['m0_feasibility_snapshots', 'm0_research_cache', 'm0_performance_logs']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop M0 feasibility system tables."""
    
    # Drop triggers
    for table in ['m0_feasibility_snapshots', 'm0_research_cache', 'm0_performance_logs']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")
    
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('m0_performance_logs')
    op.drop_table('m0_research_cache')
    op.drop_table('m0_feasibility_snapshots')