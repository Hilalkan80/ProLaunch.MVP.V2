-- =====================================================
-- ProLaunch MVP V2 - Advanced Indexes and Optimization
-- =====================================================
-- Description: Comprehensive indexing strategy for optimal
--              query performance and database optimization
-- =====================================================

-- =====================================================
-- 1. BTREE INDEXES (Standard lookups)
-- =====================================================

-- Auth schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower 
    ON auth.users (LOWER(email));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_username_lower 
    ON auth.users (LOWER(username));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_status_role 
    ON auth.users (status, role) 
    WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_subscription 
    ON auth.users (subscription_tier) 
    WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_activity 
    ON auth.users (last_activity_at DESC NULLS LAST) 
    WHERE status = 'active';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_oauth_accounts_composite 
    ON auth.oauth_accounts (provider, provider_user_id, user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active 
    ON auth.sessions (user_id, expires_at) 
    WHERE revoked_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_active 
    ON auth.api_keys (key_hash) 
    WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

-- App schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_user_active 
    ON app.projects (user_id, is_active) 
    WHERE archived_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_milestone_status 
    ON app.projects (current_milestone, is_active) 
    WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_members_composite 
    ON app.project_members (project_id, user_id, role) 
    WHERE joined_at IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_milestones_project_type 
    ON app.milestones (project_id, milestone_type, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_milestones_incomplete 
    ON app.milestones (project_id, target_date) 
    WHERE status NOT IN ('completed', 'skipped');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_assignment 
    ON app.tasks (assigned_to, status, priority) 
    WHERE status NOT IN ('completed', 'cancelled');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_due_soon 
    ON app.tasks (due_date, status) 
    WHERE status NOT IN ('completed', 'cancelled') AND due_date IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_project_status 
    ON app.tasks (project_id, status, priority);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_task_comments_task 
    ON app.task_comments (task_id, created_at DESC) 
    WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_project_type 
    ON app.documents (project_id, document_type, status) 
    WHERE archived_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_ai_generated 
    ON app.documents (ai_generated, ai_model) 
    WHERE ai_generated = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resources_project_category 
    ON app.resources (project_id, category) 
    WHERE deleted_at IS NULL;

-- AI schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conv_recent 
    ON ai.chat_conversations (user_id, last_message_at DESC NULLS LAST);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conv_project_user 
    ON ai.chat_conversations (project_id, user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_conversation 
    ON ai.chat_messages (conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_role 
    ON ai.chat_messages (conversation_id, role) 
    WHERE role IN ('user', 'assistant');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_insights_actionable 
    ON ai.insights (project_id, is_actionable, created_at DESC) 
    WHERE is_dismissed = false AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

-- Marketplace schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_verified 
    ON marketplace.suppliers (category, rating DESC, total_reviews DESC) 
    WHERE status IN ('verified', 'premium');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_location 
    ON marketplace.suppliers USING gin(locations_served) 
    WHERE status IN ('verified', 'premium');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_supplier_rating 
    ON marketplace.supplier_reviews (supplier_id, rating, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_connections_pending 
    ON marketplace.connection_requests (supplier_id, status, created_at DESC) 
    WHERE status = 'pending' AND expires_at > CURRENT_TIMESTAMP;

-- Audit schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_composite 
    ON audit.activity_logs (entity_type, entity_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activity_user_recent 
    ON audit.activity_logs (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_logs_errors 
    ON audit.api_logs (response_status, created_at DESC) 
    WHERE response_status >= 400;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_logs_status 
    ON audit.email_logs (status, created_at DESC) 
    WHERE status IN ('failed', 'bounced');

-- Analytics schema indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_analytics_date_range 
    ON analytics.user_analytics (user_id, date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_analytics_date_range 
    ON analytics.project_analytics (project_id, date DESC);

-- =====================================================
-- 2. GIN INDEXES (Full-text search and arrays)
-- =====================================================

-- Full-text search indexes with custom configurations
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS prolaunch_search (COPY = english);

-- Projects full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_fts 
    ON app.projects USING gin(
        to_tsvector('prolaunch_search', 
            COALESCE(name, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            COALESCE(industry, '') || ' ' || 
            COALESCE(target_market, '')
        )
    );

-- Tasks full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_fts 
    ON app.tasks USING gin(
        to_tsvector('prolaunch_search', 
            COALESCE(title, '') || ' ' || 
            COALESCE(description, '')
        )
    );

-- Documents full-text search (limited to first 1000 chars for performance)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_fts 
    ON app.documents USING gin(
        to_tsvector('prolaunch_search', 
            COALESCE(title, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            LEFT(COALESCE(content, ''), 1000)
        )
    );

-- Suppliers full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_fts 
    ON marketplace.suppliers USING gin(
        to_tsvector('prolaunch_search', 
            COALESCE(company_name, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            array_to_string(services_offered, ' ')
        )
    );

-- Array column indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_tags 
    ON app.tasks USING gin(tags) 
    WHERE tags IS NOT NULL AND array_length(tags, 1) > 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_tags 
    ON app.documents USING gin(tags) 
    WHERE tags IS NOT NULL AND array_length(tags, 1) > 0;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_services 
    ON marketplace.suppliers USING gin(services_offered);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_industries 
    ON marketplace.suppliers USING gin(industries_served);

-- JSONB indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_metadata 
    ON auth.users USING gin(metadata);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_preferences 
    ON auth.users USING gin(preferences);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_settings 
    ON app.projects USING gin(settings);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conv_context 
    ON ai.chat_conversations USING gin(context);

-- =====================================================
-- 3. GIST INDEXES (Geometric and exclusion constraints)
-- =====================================================

-- Exclusion constraint for preventing overlapping sessions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_no_overlap 
    ON auth.sessions USING gist (
        user_id WITH =,
        tstzrange(created_at, expires_at) WITH &&
    ) WHERE revoked_at IS NULL;

-- =====================================================
-- 4. VECTOR INDEXES (For similarity search)
-- =====================================================

-- IVFFlat indexes for vector similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_vector_l2 
    ON ai.embeddings USING ivfflat (embedding vector_l2_ops) 
    WITH (lists = 100);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_vector_ip 
    ON ai.embeddings USING ivfflat (embedding vector_ip_ops) 
    WITH (lists = 100);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_embeddings_vector_cosine 
    ON ai.embeddings USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Supplier embeddings vector index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_vector_cosine 
    ON marketplace.suppliers USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 50)
    WHERE embedding IS NOT NULL;

-- =====================================================
-- 5. PARTIAL INDEXES (For specific query patterns)
-- =====================================================

-- Active users partial index
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_verified 
    ON auth.users (email, username) 
    WHERE status = 'active' AND email_verified = true;

-- Pending tasks by priority
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_priority_pending 
    ON app.tasks (priority, due_date) 
    WHERE status IN ('todo', 'in_progress') AND priority IN ('critical', 'high');

-- Recent documents
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_recent 
    ON app.documents (created_at DESC) 
    WHERE created_at > CURRENT_DATE - INTERVAL '30 days';

-- High-value suppliers
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_suppliers_premium 
    ON marketplace.suppliers (rating DESC, total_reviews DESC) 
    WHERE status = 'premium' AND rating >= 4.0;

-- =====================================================
-- 6. COVERING INDEXES (Include non-key columns)
-- =====================================================

-- User lookup with common fields
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_lookup 
    ON auth.users (id) 
    INCLUDE (email, username, full_name, role, status, subscription_tier);

-- Project lookup with metadata
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_lookup 
    ON app.projects (id) 
    INCLUDE (name, user_id, current_milestone, is_active);

-- Task assignment lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_assignment_lookup 
    ON app.tasks (assigned_to, status) 
    INCLUDE (title, priority, due_date, project_id);

-- =====================================================
-- 7. COMPOSITE INDEXES FOR COMPLEX QUERIES
-- =====================================================

-- Dashboard query optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dashboard_projects 
    ON app.projects (user_id, is_active, created_at DESC) 
    INCLUDE (name, current_milestone)
    WHERE is_active = true AND archived_at IS NULL;

-- Analytics aggregation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_aggregation 
    ON analytics.project_analytics (project_id, date DESC) 
    INCLUDE (active_users, tasks_completed, ai_tokens_used);

-- Audit trail lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_trail 
    ON audit.activity_logs (entity_type, entity_id, created_at DESC) 
    INCLUDE (user_id, action)
    WHERE created_at > CURRENT_DATE - INTERVAL '90 days';

-- =====================================================
-- 8. STATISTICS AND OPTIMIZATION CONFIGURATION
-- =====================================================

-- Increase statistics target for frequently joined columns
ALTER TABLE auth.users ALTER COLUMN id SET STATISTICS 1000;
ALTER TABLE app.projects ALTER COLUMN id SET STATISTICS 1000;
ALTER TABLE app.projects ALTER COLUMN user_id SET STATISTICS 1000;
ALTER TABLE app.tasks ALTER COLUMN project_id SET STATISTICS 1000;
ALTER TABLE ai.chat_conversations ALTER COLUMN project_id SET STATISTICS 1000;

-- Set fillfactor for frequently updated tables
ALTER TABLE auth.users SET (fillfactor = 90);
ALTER TABLE auth.sessions SET (fillfactor = 70);
ALTER TABLE app.tasks SET (fillfactor = 85);
ALTER TABLE ai.chat_messages SET (fillfactor = 95);
ALTER TABLE audit.activity_logs SET (fillfactor = 100);

-- Enable auto-vacuum for high-activity tables
ALTER TABLE auth.sessions SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

ALTER TABLE app.tasks SET (
    autovacuum_vacuum_scale_factor = 0.15,
    autovacuum_analyze_scale_factor = 0.1
);

ALTER TABLE ai.chat_messages SET (
    autovacuum_vacuum_scale_factor = 0.2,
    autovacuum_analyze_scale_factor = 0.1
);

-- =====================================================
-- 9. QUERY OPTIMIZATION FUNCTIONS
-- =====================================================

-- Function to analyze index usage
CREATE OR REPLACE FUNCTION analyze_index_usage()
RETURNS TABLE (
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    index_size TEXT,
    idx_scan BIGINT,
    idx_tup_read BIGINT,
    idx_tup_fetch BIGINT,
    usage_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.schemaname::TEXT,
        s.tablename::TEXT,
        s.indexrelname::TEXT AS indexname,
        pg_size_pretty(pg_relation_size(s.indexrelid))::TEXT AS index_size,
        s.idx_scan,
        s.idx_tup_read,
        s.idx_tup_fetch,
        CASE 
            WHEN s.idx_scan = 0 THEN 0
            ELSE ROUND(100.0 * s.idx_tup_fetch / NULLIF(s.idx_scan, 0), 2)
        END AS usage_ratio
    FROM pg_stat_user_indexes s
    JOIN pg_index i ON s.indexrelid = i.indexrelid
    WHERE s.schemaname NOT IN ('pg_catalog', 'pg_toast')
    ORDER BY s.idx_scan DESC, pg_relation_size(s.indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to find missing indexes
CREATE OR REPLACE FUNCTION find_missing_indexes()
RETURNS TABLE (
    schemaname TEXT,
    tablename TEXT,
    attname TEXT,
    seq_scan BIGINT,
    seq_tup_read BIGINT,
    idx_scan BIGINT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH table_stats AS (
        SELECT 
            schemaname,
            tablename,
            seq_scan,
            seq_tup_read,
            idx_scan,
            CASE 
                WHEN seq_scan > 0 THEN 
                    ROUND(100.0 * seq_scan / (seq_scan + idx_scan), 2)
                ELSE 0
            END AS seq_scan_ratio
        FROM pg_stat_user_tables
        WHERE schemaname NOT IN ('pg_catalog', 'pg_toast')
            AND seq_scan > 100
            AND pg_relation_size(schemaname||'.'||tablename) > 1048576 -- > 1MB
    )
    SELECT 
        ts.schemaname::TEXT,
        ts.tablename::TEXT,
        a.attname::TEXT,
        ts.seq_scan,
        ts.seq_tup_read,
        ts.idx_scan,
        CASE 
            WHEN ts.seq_scan_ratio > 50 THEN 
                'Consider adding index on frequently queried columns'
            ELSE 
                'Table has good index coverage'
        END AS recommendation
    FROM table_stats ts
    JOIN pg_attribute a ON a.attrelid = (ts.schemaname||'.'||ts.tablename)::regclass
    WHERE a.attnum > 0 
        AND NOT a.attisdropped
        AND ts.seq_scan_ratio > 25
    ORDER BY ts.seq_scan DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Function to get index bloat
CREATE OR REPLACE FUNCTION check_index_bloat()
RETURNS TABLE (
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    real_size TEXT,
    extra_size TEXT,
    bloat_ratio NUMERIC,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH btree_index_atts AS (
        SELECT 
            nspname,
            indexclass.relname AS index_name,
            indexclass.reltuples,
            indexclass.relpages,
            tableclass.relname AS tablename,
            (
                SELECT COUNT(*)
                FROM pg_index
                WHERE pg_index.indexrelid = indexclass.oid
            ) AS number_of_columns,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_index
        JOIN pg_class AS indexclass ON pg_index.indexrelid = indexclass.oid
        JOIN pg_class AS tableclass ON pg_index.indrelid = tableclass.oid
        JOIN pg_namespace ON pg_namespace.oid = indexclass.relnamespace
        JOIN pg_stat_user_indexes ON pg_stat_user_indexes.indexrelid = indexclass.oid
        WHERE pg_index.indisvalid
            AND indexclass.relpages > 0
    )
    SELECT 
        nspname::TEXT AS schemaname,
        tablename::TEXT,
        index_name::TEXT AS indexname,
        pg_size_pretty(relpages::BIGINT * 8192)::TEXT AS real_size,
        pg_size_pretty(
            CASE 
                WHEN relpages > reltuples * 0.1 THEN 
                    (relpages - (reltuples * 0.1))::BIGINT * 8192
                ELSE 0
            END
        )::TEXT AS extra_size,
        CASE 
            WHEN reltuples > 0 THEN 
                ROUND((relpages / (reltuples * 0.1))::NUMERIC, 2)
            ELSE 0
        END AS bloat_ratio,
        CASE 
            WHEN relpages > reltuples * 0.2 THEN 'REINDEX recommended'
            WHEN relpages > reltuples * 0.15 THEN 'Monitor for bloat'
            ELSE 'Acceptable'
        END AS recommendation
    FROM btree_index_atts
    WHERE relpages > 10
    ORDER BY relpages DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 10. MAINTENANCE PROCEDURES
-- =====================================================

-- Procedure to rebuild all indexes in a schema
CREATE OR REPLACE PROCEDURE rebuild_schema_indexes(p_schema TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_index RECORD;
BEGIN
    FOR v_index IN 
        SELECT schemaname, indexname 
        FROM pg_indexes 
        WHERE schemaname = p_schema
    LOOP
        EXECUTE format('REINDEX INDEX CONCURRENTLY %I.%I', 
                      v_index.schemaname, v_index.indexname);
        RAISE NOTICE 'Reindexed: %.%', v_index.schemaname, v_index.indexname;
    END LOOP;
END;
$$;

-- Procedure to update table statistics
CREATE OR REPLACE PROCEDURE update_statistics(p_schema TEXT DEFAULT NULL)
LANGUAGE plpgsql
AS $$
DECLARE
    v_table RECORD;
BEGIN
    FOR v_table IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE schemaname = COALESCE(p_schema, schemaname)
            AND schemaname NOT IN ('pg_catalog', 'information_schema')
    LOOP
        EXECUTE format('ANALYZE %I.%I', v_table.schemaname, v_table.tablename);
        RAISE NOTICE 'Analyzed: %.%', v_table.schemaname, v_table.tablename;
    END LOOP;
END;
$$;

-- =====================================================
-- 11. MONITORING VIEWS
-- =====================================================

-- View for monitoring index performance
CREATE OR REPLACE VIEW monitoring.v_index_performance AS
SELECT 
    schemaname,
    tablename,
    indexrelname AS indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'RARELY USED'
        WHEN idx_scan < 1000 THEN 'OCCASIONALLY USED'
        ELSE 'FREQUENTLY USED'
    END AS usage_category
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- View for monitoring table performance
CREATE OR REPLACE VIEW monitoring.v_table_performance AS
SELECT 
    schemaname,
    tablename,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    CASE 
        WHEN n_live_tup > 0 THEN 
            ROUND(100.0 * n_dead_tup / n_live_tup, 2)
        ELSE 0
    END AS dead_tuple_ratio,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- =====================================================
-- 12. OPTIMIZATION NOTES
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'INDEX OPTIMIZATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Indexes created:';
    RAISE NOTICE '- BTree indexes for standard lookups';
    RAISE NOTICE '- GIN indexes for full-text search';
    RAISE NOTICE '- GIN indexes for array/JSONB columns';
    RAISE NOTICE '- IVFFlat indexes for vector similarity';
    RAISE NOTICE '- Partial indexes for specific queries';
    RAISE NOTICE '- Covering indexes for common lookups';
    RAISE NOTICE '';
    RAISE NOTICE 'Optimization features:';
    RAISE NOTICE '- Custom fillfactor settings';
    RAISE NOTICE '- Auto-vacuum tuning';
    RAISE NOTICE '- Statistics targets increased';
    RAISE NOTICE '- Monitoring functions created';
    RAISE NOTICE '';
    RAISE NOTICE 'Maintenance procedures:';
    RAISE NOTICE '- analyze_index_usage()';
    RAISE NOTICE '- find_missing_indexes()';
    RAISE NOTICE '- check_index_bloat()';
    RAISE NOTICE '- rebuild_schema_indexes(schema)';
    RAISE NOTICE '- update_statistics(schema)';
    RAISE NOTICE '========================================';
END $$;