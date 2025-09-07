-- =====================================================
-- ProLaunch MVP V2 - Database Migrations and Procedures
-- =====================================================
-- Version: 1.0.0
-- Description: Migration management, stored procedures,
--              and utility functions for database operations
-- =====================================================

-- =====================================================
-- SECTION 1: MIGRATION MANAGEMENT SYSTEM
-- =====================================================

-- Create migration tracking schema
CREATE SCHEMA IF NOT EXISTS migrations;

-- Migration history table
CREATE TABLE IF NOT EXISTS migrations.history (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    script_hash VARCHAR(64),
    executed_by VARCHAR(100) DEFAULT CURRENT_USER,
    execution_time_ms INT,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    rollback_script TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rolled_back_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT valid_version CHECK (version ~ '^\d+\.\d+\.\d+$')
);

-- Migration locks to prevent concurrent migrations
CREATE TABLE IF NOT EXISTS migrations.locks (
    id SERIAL PRIMARY KEY,
    lock_name VARCHAR(100) UNIQUE NOT NULL,
    locked_by VARCHAR(100) DEFAULT CURRENT_USER,
    locked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP WITH TIME ZONE
);

-- Function to acquire migration lock
CREATE OR REPLACE FUNCTION migrations.acquire_lock(p_lock_name VARCHAR DEFAULT 'migration')
RETURNS BOOLEAN AS $$
DECLARE
    v_locked BOOLEAN;
BEGIN
    -- Try to acquire lock
    INSERT INTO migrations.locks (lock_name, locked_by, locked_at)
    VALUES (p_lock_name, CURRENT_USER, CURRENT_TIMESTAMP)
    ON CONFLICT (lock_name) DO NOTHING
    RETURNING true INTO v_locked;
    
    RETURN COALESCE(v_locked, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Function to release migration lock
CREATE OR REPLACE FUNCTION migrations.release_lock(p_lock_name VARCHAR DEFAULT 'migration')
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE migrations.locks 
    SET released_at = CURRENT_TIMESTAMP
    WHERE lock_name = p_lock_name 
        AND released_at IS NULL
        AND locked_by = CURRENT_USER;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to execute migration
CREATE OR REPLACE FUNCTION migrations.execute_migration(
    p_version VARCHAR,
    p_name VARCHAR,
    p_up_script TEXT,
    p_down_script TEXT DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    execution_time_ms INT
) AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_exec_time_ms INT;
    v_error_message TEXT;
BEGIN
    -- Check if migration already executed
    IF EXISTS (SELECT 1 FROM migrations.history WHERE version = p_version AND success = TRUE) THEN
        RETURN QUERY SELECT FALSE, 'Migration already executed', 0;
        RETURN;
    END IF;
    
    -- Acquire lock
    IF NOT migrations.acquire_lock() THEN
        RETURN QUERY SELECT FALSE, 'Could not acquire migration lock', 0;
        RETURN;
    END IF;
    
    BEGIN
        v_start_time := clock_timestamp();
        
        -- Execute migration script
        EXECUTE p_up_script;
        
        v_end_time := clock_timestamp();
        v_exec_time_ms := EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time))::INT;
        
        -- Record success
        INSERT INTO migrations.history (
            version, name, description, 
            rollback_script, execution_time_ms, success
        ) VALUES (
            p_version, p_name, p_name,
            p_down_script, v_exec_time_ms, TRUE
        );
        
        -- Release lock
        PERFORM migrations.release_lock();
        
        RETURN QUERY SELECT TRUE, 'Migration executed successfully', v_exec_time_ms;
        
    EXCEPTION WHEN OTHERS THEN
        -- Record failure
        GET STACKED DIAGNOSTICS v_error_message = MESSAGE_TEXT;
        
        INSERT INTO migrations.history (
            version, name, description,
            rollback_script, error_message, success
        ) VALUES (
            p_version, p_name, p_name,
            p_down_script, v_error_message, FALSE
        );
        
        -- Release lock
        PERFORM migrations.release_lock();
        
        RETURN QUERY SELECT FALSE, v_error_message, 0;
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to rollback migration
CREATE OR REPLACE FUNCTION migrations.rollback_migration(p_version VARCHAR)
RETURNS TABLE (
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_rollback_script TEXT;
    v_error_message TEXT;
BEGIN
    -- Get rollback script
    SELECT rollback_script INTO v_rollback_script
    FROM migrations.history
    WHERE version = p_version 
        AND success = TRUE 
        AND rolled_back_at IS NULL;
    
    IF v_rollback_script IS NULL THEN
        RETURN QUERY SELECT FALSE, 'No rollback script found or migration not executed';
        RETURN;
    END IF;
    
    BEGIN
        -- Execute rollback
        EXECUTE v_rollback_script;
        
        -- Mark as rolled back
        UPDATE migrations.history 
        SET rolled_back_at = CURRENT_TIMESTAMP
        WHERE version = p_version;
        
        RETURN QUERY SELECT TRUE, 'Migration rolled back successfully';
        
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_error_message = MESSAGE_TEXT;
        RETURN QUERY SELECT FALSE, v_error_message;
    END;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 2: DATA VALIDATION PROCEDURES
-- =====================================================

-- Validate email format
CREATE OR REPLACE FUNCTION validate_email(p_email VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN p_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validate URL format
CREATE OR REPLACE FUNCTION validate_url(p_url TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN p_url ~* '^https?://[^\s/$.?#].[^\s]*$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Validate phone number
CREATE OR REPLACE FUNCTION validate_phone(p_phone VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN p_phone ~* '^\+?[1-9]\d{1,14}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Sanitize HTML content
CREATE OR REPLACE FUNCTION sanitize_html(p_content TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Remove script tags
    p_content := REGEXP_REPLACE(p_content, '<script[^>]*>.*?</script>', '', 'gi');
    -- Remove style tags
    p_content := REGEXP_REPLACE(p_content, '<style[^>]*>.*?</style>', '', 'gi');
    -- Remove on* attributes
    p_content := REGEXP_REPLACE(p_content, '\son\w+\s*=\s*"[^"]*"', '', 'gi');
    -- Remove javascript: protocol
    p_content := REGEXP_REPLACE(p_content, 'javascript:', '', 'gi');
    
    RETURN p_content;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =====================================================
-- SECTION 3: USER MANAGEMENT PROCEDURES
-- =====================================================

-- Create new user with profile
CREATE OR REPLACE FUNCTION auth.create_user_with_profile(
    p_email VARCHAR,
    p_username VARCHAR,
    p_full_name VARCHAR,
    p_password_hash VARCHAR DEFAULT NULL,
    p_role auth.user_role DEFAULT 'user'
)
RETURNS UUID AS $$
DECLARE
    v_user_id UUID;
BEGIN
    -- Validate inputs
    IF NOT validate_email(p_email) THEN
        RAISE EXCEPTION 'Invalid email format';
    END IF;
    
    IF LENGTH(p_username) < 3 THEN
        RAISE EXCEPTION 'Username must be at least 3 characters';
    END IF;
    
    -- Create user
    INSERT INTO auth.users (
        email, username, full_name, password_hash, role
    ) VALUES (
        p_email, p_username, p_full_name, p_password_hash, p_role
    ) RETURNING id INTO v_user_id;
    
    -- Create profile
    INSERT INTO app.user_profiles (user_id) VALUES (v_user_id);
    
    -- Create notification preferences
    INSERT INTO notifications.user_preferences (user_id) VALUES (v_user_id);
    
    -- Log activity
    INSERT INTO audit.activity_logs (
        user_id, action, entity_type, entity_id, metadata
    ) VALUES (
        v_user_id, 'create', 'user', v_user_id, 
        jsonb_build_object('email', p_email, 'username', p_username)
    );
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Soft delete user
CREATE OR REPLACE FUNCTION auth.soft_delete_user(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if user exists
    IF NOT EXISTS (SELECT 1 FROM auth.users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'User not found';
    END IF;
    
    -- Soft delete user
    UPDATE auth.users 
    SET 
        status = 'deleted',
        deleted_at = CURRENT_TIMESTAMP,
        email = email || '_deleted_' || EXTRACT(EPOCH FROM CURRENT_TIMESTAMP),
        username = username || '_deleted_' || EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
    WHERE id = p_user_id;
    
    -- Revoke all sessions
    UPDATE auth.sessions 
    SET revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'User deleted'
    WHERE user_id = p_user_id AND revoked_at IS NULL;
    
    -- Revoke all API keys
    UPDATE auth.api_keys 
    SET revoked_at = CURRENT_TIMESTAMP, revoked_reason = 'User deleted'
    WHERE user_id = p_user_id AND revoked_at IS NULL;
    
    -- Log activity
    INSERT INTO audit.activity_logs (
        user_id, action, entity_type, entity_id
    ) VALUES (
        p_user_id, 'delete', 'user', p_user_id
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Update user subscription
CREATE OR REPLACE FUNCTION auth.update_subscription(
    p_user_id UUID,
    p_tier auth.subscription_tier,
    p_valid_until TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE auth.users 
    SET 
        subscription_tier = p_tier,
        subscription_valid_until = p_valid_until,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;
    
    -- Log activity
    INSERT INTO audit.activity_logs (
        user_id, action, entity_type, entity_id, new_values
    ) VALUES (
        p_user_id, 'update_subscription', 'user', p_user_id,
        jsonb_build_object('tier', p_tier, 'valid_until', p_valid_until)
    );
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SECTION 4: PROJECT MANAGEMENT PROCEDURES
-- =====================================================

-- Create project with initial setup
CREATE OR REPLACE FUNCTION app.create_project(
    p_user_id UUID,
    p_name VARCHAR,
    p_description TEXT DEFAULT NULL,
    p_industry VARCHAR DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_project_id UUID;
    v_milestone_type app.milestone_type;
BEGIN
    -- Create project
    INSERT INTO app.projects (
        user_id, name, description, industry
    ) VALUES (
        p_user_id, p_name, p_description, p_industry
    ) RETURNING id INTO v_project_id;
    
    -- Add creator as owner
    INSERT INTO app.project_members (
        project_id, user_id, role, joined_at
    ) VALUES (
        v_project_id, p_user_id, 'owner', CURRENT_TIMESTAMP
    );
    
    -- Create default milestones
    FOR v_milestone_type IN 
        SELECT unnest(enum_range(NULL::app.milestone_type))
    LOOP
        INSERT INTO app.milestones (
            project_id, milestone_type, name, description
        ) VALUES (
            v_project_id, v_milestone_type, 
            v_milestone_type::TEXT, 
            'Default ' || v_milestone_type::TEXT || ' milestone'
        );
    END LOOP;
    
    -- Log activity
    INSERT INTO audit.activity_logs (
        user_id, action, entity_type, entity_id, new_values
    ) VALUES (
        p_user_id, 'create', 'project', v_project_id,
        jsonb_build_object('name', p_name)
    );
    
    RETURN v_project_id;
END;
$$ LANGUAGE plpgsql;

-- Add member to project
CREATE OR REPLACE FUNCTION app.add_project_member(
    p_project_id UUID,
    p_user_id UUID,
    p_role VARCHAR DEFAULT 'member',
    p_invited_by UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if already member
    IF EXISTS (
        SELECT 1 FROM app.project_members 
        WHERE project_id = p_project_id AND user_id = p_user_id
    ) THEN
        RAISE EXCEPTION 'User is already a project member';
    END IF;
    
    -- Add member
    INSERT INTO app.project_members (
        project_id, user_id, role, invited_by, joined_at
    ) VALUES (
        p_project_id, p_user_id, p_role, p_invited_by, CURRENT_TIMESTAMP
    );
    
    -- Create notification
    INSERT INTO notifications.queue (
        user_id, template_id, channel, variables
    )
    SELECT 
        p_user_id, id, 'in_app',
        jsonb_build_object(
            'project_name', (SELECT name FROM app.projects WHERE id = p_project_id),
            'inviter_name', (SELECT full_name FROM auth.users WHERE id = p_invited_by)
        )
    FROM notifications.templates
    WHERE name = 'project_invitation';
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Archive project
CREATE OR REPLACE FUNCTION app.archive_project(p_project_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE app.projects 
    SET 
        is_active = FALSE,
        archived_at = CURRENT_TIMESTAMP
    WHERE id = p_project_id;
    
    -- Cancel all pending tasks
    UPDATE app.tasks 
    SET status = 'cancelled'
    WHERE project_id = p_project_id 
        AND status NOT IN ('completed', 'cancelled');
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 5: TASK MANAGEMENT PROCEDURES
-- =====================================================

-- Create task with dependencies
CREATE OR REPLACE FUNCTION app.create_task(
    p_project_id UUID,
    p_title VARCHAR,
    p_description TEXT DEFAULT NULL,
    p_assigned_to UUID DEFAULT NULL,
    p_milestone_id UUID DEFAULT NULL,
    p_dependencies UUID[] DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
    v_created_by UUID;
BEGIN
    -- Get current user
    v_created_by := current_setting('app.current_user_id', true)::UUID;
    
    -- Create task
    INSERT INTO app.tasks (
        project_id, title, description, 
        assigned_to, milestone_id, created_by, dependencies
    ) VALUES (
        p_project_id, p_title, p_description,
        p_assigned_to, p_milestone_id, v_created_by, p_dependencies
    ) RETURNING id INTO v_task_id;
    
    -- Update blocked tasks
    IF p_dependencies IS NOT NULL THEN
        UPDATE app.tasks 
        SET blocks = array_append(blocks, v_task_id)
        WHERE id = ANY(p_dependencies);
    END IF;
    
    -- Send notification if assigned
    IF p_assigned_to IS NOT NULL THEN
        INSERT INTO notifications.queue (
            user_id, template_id, channel, variables
        )
        SELECT 
            p_assigned_to, id, 'in_app',
            jsonb_build_object('task_title', p_title)
        FROM notifications.templates
        WHERE name = 'task_assigned';
    END IF;
    
    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql;

-- Update task status with validation
CREATE OR REPLACE FUNCTION app.update_task_status(
    p_task_id UUID,
    p_status app.task_status
)
RETURNS BOOLEAN AS $$
DECLARE
    v_current_status app.task_status;
    v_has_blockers BOOLEAN;
BEGIN
    -- Get current status
    SELECT status INTO v_current_status
    FROM app.tasks WHERE id = p_task_id;
    
    -- Check for blockers if moving to in_progress
    IF p_status = 'in_progress' THEN
        SELECT EXISTS (
            SELECT 1 FROM app.tasks 
            WHERE id = ANY(
                SELECT unnest(dependencies) FROM app.tasks WHERE id = p_task_id
            ) AND status != 'completed'
        ) INTO v_has_blockers;
        
        IF v_has_blockers THEN
            RAISE EXCEPTION 'Cannot start task with incomplete dependencies';
        END IF;
    END IF;
    
    -- Update status
    UPDATE app.tasks 
    SET 
        status = p_status,
        started_at = CASE 
            WHEN p_status = 'in_progress' AND started_at IS NULL 
            THEN CURRENT_TIMESTAMP 
            ELSE started_at 
        END,
        completed_at = CASE 
            WHEN p_status = 'completed' 
            THEN CURRENT_TIMESTAMP 
            ELSE NULL 
        END
    WHERE id = p_task_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 6: AI AND EMBEDDINGS PROCEDURES
-- =====================================================

-- Store embedding for content
CREATE OR REPLACE FUNCTION ai.store_embedding(
    p_content_type VARCHAR,
    p_content_id UUID,
    p_content TEXT,
    p_embedding vector(1536),
    p_chunk_index INT DEFAULT 0
)
RETURNS UUID AS $$
DECLARE
    v_embedding_id UUID;
BEGIN
    -- Store or update embedding
    INSERT INTO ai.embeddings (
        content_type, content_id, content_chunk,
        chunk_index, embedding
    ) VALUES (
        p_content_type, p_content_id, p_content,
        p_chunk_index, p_embedding
    )
    ON CONFLICT (content_type, content_id, chunk_index, content_version)
    DO UPDATE SET 
        content_chunk = EXCLUDED.content_chunk,
        embedding = EXCLUDED.embedding,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id INTO v_embedding_id;
    
    RETURN v_embedding_id;
END;
$$ LANGUAGE plpgsql;

-- Semantic search function
CREATE OR REPLACE FUNCTION ai.semantic_search(
    p_query_embedding vector(1536),
    p_content_type VARCHAR DEFAULT NULL,
    p_limit INT DEFAULT 10,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    content_type VARCHAR,
    content_id UUID,
    content_chunk TEXT,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.content_type,
        e.content_id,
        e.content_chunk,
        1 - (e.embedding <=> p_query_embedding) AS similarity,
        e.metadata
    FROM ai.embeddings e
    WHERE 
        (p_content_type IS NULL OR e.content_type = p_content_type)
        AND (1 - (e.embedding <=> p_query_embedding)) > p_similarity_threshold
    ORDER BY e.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Track AI usage
CREATE OR REPLACE FUNCTION ai.track_usage(
    p_user_id UUID,
    p_project_id UUID,
    p_feature ai.ai_feature,
    p_model ai.ai_model,
    p_tokens INT,
    p_cost NUMERIC DEFAULT 0
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO ai.usage_tracking (
        user_id, project_id, feature, model,
        total_tokens, estimated_cost
    ) VALUES (
        p_user_id, p_project_id, p_feature, p_model,
        p_tokens, p_cost
    );
    
    -- Update conversation totals if chat feature
    IF p_feature = 'chat' AND p_project_id IS NOT NULL THEN
        UPDATE ai.chat_conversations 
        SET 
            total_tokens_used = total_tokens_used + p_tokens,
            total_cost = total_cost + p_cost
        WHERE project_id = p_project_id AND user_id = p_user_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 7: ANALYTICS AND REPORTING PROCEDURES
-- =====================================================

-- Generate user activity report
CREATE OR REPLACE FUNCTION analytics.user_activity_report(
    p_user_id UUID,
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    login_count INT,
    tasks_created INT,
    tasks_completed INT,
    messages_sent INT,
    ai_tokens_used INT
) AS $$
BEGIN
    RETURN QUERY
    WITH date_series AS (
        SELECT generate_series(p_start_date, p_end_date, '1 day'::interval)::DATE AS date
    )
    SELECT 
        ds.date,
        COALESCE(ua.login_count, 0) AS login_count,
        COALESCE(ua.tasks_created, 0) AS tasks_created,
        COALESCE(ua.tasks_completed, 0) AS tasks_completed,
        COALESCE(ua.chat_messages_sent, 0) AS messages_sent,
        COALESCE(ua.ai_tokens_used, 0) AS ai_tokens_used
    FROM date_series ds
    LEFT JOIN analytics.user_analytics ua 
        ON ua.user_id = p_user_id AND ua.date = ds.date
    ORDER BY ds.date;
END;
$$ LANGUAGE plpgsql;

-- Calculate project velocity
CREATE OR REPLACE FUNCTION analytics.calculate_project_velocity(
    p_project_id UUID,
    p_period_days INT DEFAULT 30
)
RETURNS TABLE (
    tasks_completed_per_day NUMERIC,
    avg_task_completion_time_hours NUMERIC,
    team_productivity_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::NUMERIC / p_period_days AS tasks_completed_per_day,
        AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600)::NUMERIC AS avg_task_completion_time_hours,
        (COUNT(*)::NUMERIC / COUNT(DISTINCT assigned_to)) * 10 AS team_productivity_score
    FROM app.tasks
    WHERE project_id = p_project_id
        AND completed_at >= CURRENT_DATE - INTERVAL '1 day' * p_period_days
        AND status = 'completed';
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 8: MAINTENANCE PROCEDURES
-- =====================================================

-- Vacuum and analyze tables
CREATE OR REPLACE PROCEDURE maintenance.vacuum_analyze_all()
LANGUAGE plpgsql AS $$
DECLARE
    v_table RECORD;
BEGIN
    FOR v_table IN 
        SELECT schemaname, tablename 
        FROM pg_tables 
        WHERE schemaname IN ('app', 'auth', 'ai', 'marketplace', 'notifications')
    LOOP
        EXECUTE format('VACUUM ANALYZE %I.%I', v_table.schemaname, v_table.tablename);
        RAISE NOTICE 'Vacuumed and analyzed %.%', v_table.schemaname, v_table.tablename;
    END LOOP;
END;
$$;

-- Reindex all indexes in a schema
CREATE OR REPLACE PROCEDURE maintenance.reindex_schema(p_schema TEXT)
LANGUAGE plpgsql AS $$
DECLARE
    v_index RECORD;
BEGIN
    FOR v_index IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = p_schema
    LOOP
        EXECUTE format('REINDEX INDEX CONCURRENTLY %I.%I', p_schema, v_index.indexname);
        RAISE NOTICE 'Reindexed %I.%I', p_schema, v_index.indexname;
    END LOOP;
END;
$$;

-- Clean up old audit logs
CREATE OR REPLACE FUNCTION maintenance.cleanup_audit_logs(
    p_days_to_keep INT DEFAULT 90
)
RETURNS INT AS $$
DECLARE
    v_deleted_count INT;
BEGIN
    DELETE FROM audit.activity_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days_to_keep;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    DELETE FROM audit.api_logs
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days_to_keep;
    
    GET DIAGNOSTICS v_deleted_count = v_deleted_count + ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Archive old completed tasks
CREATE OR REPLACE FUNCTION maintenance.archive_old_tasks(
    p_days_old INT DEFAULT 180
)
RETURNS INT AS $$
DECLARE
    v_archived_count INT;
BEGIN
    -- Create archive table if not exists
    CREATE TABLE IF NOT EXISTS app.tasks_archive (LIKE app.tasks INCLUDING ALL);
    
    -- Move old completed tasks to archive
    WITH archived AS (
        DELETE FROM app.tasks
        WHERE status = 'completed'
            AND completed_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days_old
        RETURNING *
    )
    INSERT INTO app.tasks_archive SELECT * FROM archived;
    
    GET DIAGNOSTICS v_archived_count = ROW_COUNT;
    
    RETURN v_archived_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 9: MONITORING PROCEDURES
-- =====================================================

-- Get database size information
CREATE OR REPLACE FUNCTION monitoring.database_size_info()
RETURNS TABLE (
    database_name TEXT,
    database_size TEXT,
    schema_name TEXT,
    schema_size TEXT,
    table_count INT
) AS $$
BEGIN
    RETURN QUERY
    WITH schema_sizes AS (
        SELECT 
            nspname AS schema_name,
            COUNT(c.oid) AS table_count,
            SUM(pg_total_relation_size(c.oid)) AS total_size
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            AND c.relkind IN ('r', 'p')
        GROUP BY nspname
    )
    SELECT 
        current_database()::TEXT,
        pg_size_pretty(pg_database_size(current_database()))::TEXT,
        schema_name::TEXT,
        pg_size_pretty(total_size)::TEXT,
        table_count
    FROM schema_sizes
    ORDER BY total_size DESC;
END;
$$ LANGUAGE plpgsql;

-- Get slow queries
CREATE OR REPLACE FUNCTION monitoring.get_slow_queries(
    p_min_duration_ms INT DEFAULT 1000
)
RETURNS TABLE (
    query TEXT,
    calls BIGINT,
    total_time NUMERIC,
    mean_time NUMERIC,
    max_time NUMERIC,
    rows BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        LEFT(query, 100) AS query,
        calls,
        ROUND(total_exec_time::NUMERIC, 2) AS total_time,
        ROUND(mean_exec_time::NUMERIC, 2) AS mean_time,
        ROUND(max_exec_time::NUMERIC, 2) AS max_time,
        rows
    FROM pg_stat_statements
    WHERE mean_exec_time > p_min_duration_ms
    ORDER BY mean_exec_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Get table bloat information
CREATE OR REPLACE FUNCTION monitoring.table_bloat()
RETURNS TABLE (
    schema_name TEXT,
    table_name TEXT,
    table_size TEXT,
    dead_tuples BIGINT,
    bloat_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname::TEXT,
        tablename::TEXT,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))::TEXT,
        n_dead_tup,
        ROUND(
            CASE WHEN n_live_tup > 0 
            THEN (n_dead_tup::NUMERIC / n_live_tup) * 100 
            ELSE 0 END, 2
        ) AS bloat_ratio
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 1000
    ORDER BY n_dead_tup DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 10: SECURITY PROCEDURES
-- =====================================================

-- Audit sensitive operations
CREATE OR REPLACE FUNCTION security.audit_operation(
    p_operation VARCHAR,
    p_table_name VARCHAR,
    p_record_id UUID,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO audit.activity_logs (
        user_id,
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        ip_address,
        metadata
    ) VALUES (
        current_setting('app.current_user_id', true)::UUID,
        p_operation,
        p_table_name,
        p_record_id,
        p_old_values,
        p_new_values,
        inet_client_addr(),
        jsonb_build_object(
            'timestamp', CURRENT_TIMESTAMP,
            'session_user', session_user,
            'current_user', current_user
        )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Revoke expired sessions
CREATE OR REPLACE FUNCTION security.revoke_expired_sessions()
RETURNS INT AS $$
DECLARE
    v_revoked_count INT;
BEGIN
    UPDATE auth.sessions
    SET 
        revoked_at = CURRENT_TIMESTAMP,
        revoked_reason = 'Session expired'
    WHERE expires_at < CURRENT_TIMESTAMP
        AND revoked_at IS NULL;
    
    GET DIAGNOSTICS v_revoked_count = ROW_COUNT;
    
    -- Also clean up refresh tokens
    UPDATE auth.sessions
    SET 
        revoked_at = CURRENT_TIMESTAMP,
        revoked_reason = 'Refresh token expired'
    WHERE refresh_expires_at < CURRENT_TIMESTAMP
        AND revoked_at IS NULL;
    
    RETURN v_revoked_count;
END;
$$ LANGUAGE plpgsql;

-- Lock user account after failed attempts
CREATE OR REPLACE FUNCTION security.handle_failed_login(
    p_email VARCHAR,
    p_max_attempts INT DEFAULT 5,
    p_lockout_duration INTERVAL DEFAULT '30 minutes'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_attempts INT;
BEGIN
    -- Get user and increment failed attempts
    UPDATE auth.users
    SET failed_login_attempts = failed_login_attempts + 1
    WHERE email = p_email
    RETURNING id, failed_login_attempts INTO v_user_id, v_attempts;
    
    -- Lock account if max attempts reached
    IF v_attempts >= p_max_attempts THEN
        UPDATE auth.users
        SET 
            locked_until = CURRENT_TIMESTAMP + p_lockout_duration,
            status = 'suspended'
        WHERE id = v_user_id;
        
        -- Log security event
        INSERT INTO audit.activity_logs (
            user_id, action, entity_type, entity_id, metadata
        ) VALUES (
            v_user_id, 'account_locked', 'user', v_user_id,
            jsonb_build_object('reason', 'Too many failed login attempts', 'attempts', v_attempts)
        );
        
        RETURN FALSE; -- Account locked
    END IF;
    
    RETURN TRUE; -- Account still active
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- SECTION 11: UTILITY PROCEDURES
-- =====================================================

-- Generate API key
CREATE OR REPLACE FUNCTION generate_api_key()
RETURNS VARCHAR AS $$
BEGIN
    RETURN 'pk_' || encode(gen_random_bytes(32), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Generate secure token
CREATE OR REPLACE FUNCTION generate_secure_token(p_length INT DEFAULT 32)
RETURNS VARCHAR AS $$
BEGIN
    RETURN encode(gen_random_bytes(p_length), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Calculate business days between dates
CREATE OR REPLACE FUNCTION calculate_business_days(
    p_start_date DATE,
    p_end_date DATE
)
RETURNS INT AS $$
DECLARE
    v_days INT := 0;
    v_current_date DATE := p_start_date;
BEGIN
    WHILE v_current_date <= p_end_date LOOP
        IF EXTRACT(DOW FROM v_current_date) NOT IN (0, 6) THEN
            v_days := v_days + 1;
        END IF;
        v_current_date := v_current_date + INTERVAL '1 day';
    END LOOP;
    
    RETURN v_days;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Format currency
CREATE OR REPLACE FUNCTION format_currency(
    p_amount NUMERIC,
    p_currency billing.currency DEFAULT 'USD'
)
RETURNS VARCHAR AS $$
BEGIN
    RETURN CASE p_currency
        WHEN 'USD' THEN '$' || TO_CHAR(p_amount, 'FM999,999,999.00')
        WHEN 'EUR' THEN '€' || TO_CHAR(p_amount, 'FM999,999,999.00')
        WHEN 'GBP' THEN '£' || TO_CHAR(p_amount, 'FM999,999,999.00')
        WHEN 'JPY' THEN '¥' || TO_CHAR(p_amount, 'FM999,999,999')
        ELSE p_currency || ' ' || TO_CHAR(p_amount, 'FM999,999,999.00')
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =====================================================
-- SECTION 12: SCHEDULED JOBS
-- =====================================================

-- Daily maintenance job
CREATE OR REPLACE FUNCTION jobs.daily_maintenance()
RETURNS VOID AS $$
BEGIN
    -- Clean up expired sessions
    PERFORM security.revoke_expired_sessions();
    
    -- Process notification queue
    PERFORM process_notification_queue();
    
    -- Update analytics
    INSERT INTO analytics.user_analytics (user_id, date, login_count, active_minutes)
    SELECT 
        user_id,
        CURRENT_DATE,
        COUNT(*),
        SUM(EXTRACT(EPOCH FROM (last_activity_at - created_at)) / 60)::INT
    FROM auth.sessions
    WHERE DATE(created_at) = CURRENT_DATE
    GROUP BY user_id
    ON CONFLICT (user_id, date) DO UPDATE
    SET 
        login_count = EXCLUDED.login_count,
        active_minutes = EXCLUDED.active_minutes;
    
    -- Clean up old notifications
    DELETE FROM notifications.queue
    WHERE status IN ('sent', 'failed')
        AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    
    -- Vacuum analyze high-activity tables
    VACUUM ANALYZE auth.sessions;
    VACUUM ANALYZE app.tasks;
    VACUUM ANALYZE notifications.queue;
END;
$$ LANGUAGE plpgsql;

-- Weekly maintenance job
CREATE OR REPLACE FUNCTION jobs.weekly_maintenance()
RETURNS VOID AS $$
BEGIN
    -- Archive old audit logs
    PERFORM maintenance.cleanup_audit_logs(90);
    
    -- Archive old tasks
    PERFORM maintenance.archive_old_tasks(180);
    
    -- Update table statistics
    ANALYZE;
    
    -- Reindex heavily used tables
    REINDEX TABLE CONCURRENTLY auth.users;
    REINDEX TABLE CONCURRENTLY app.projects;
    REINDEX TABLE CONCURRENTLY app.tasks;
END;
$$ LANGUAGE plpgsql;

-- Schedule jobs with pg_cron
SELECT cron.schedule('daily-maintenance', '0 2 * * *', $$SELECT jobs.daily_maintenance();$$);
SELECT cron.schedule('weekly-maintenance', '0 3 * * 0', $$SELECT jobs.weekly_maintenance();$$);

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Database Migrations and Procedures Created';
    RAISE NOTICE '================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Components created:';
    RAISE NOTICE '- Migration management system';
    RAISE NOTICE '- Data validation functions';
    RAISE NOTICE '- User management procedures';
    RAISE NOTICE '- Project management procedures';
    RAISE NOTICE '- Task management procedures';
    RAISE NOTICE '- AI and embedding procedures';
    RAISE NOTICE '- Analytics procedures';
    RAISE NOTICE '- Maintenance procedures';
    RAISE NOTICE '- Monitoring functions';
    RAISE NOTICE '- Security procedures';
    RAISE NOTICE '- Utility functions';
    RAISE NOTICE '- Scheduled jobs';
    RAISE NOTICE '';
    RAISE NOTICE 'Usage examples:';
    RAISE NOTICE '- SELECT auth.create_user_with_profile(...)';
    RAISE NOTICE '- SELECT app.create_project(...)';
    RAISE NOTICE '- SELECT ai.semantic_search(...)';
    RAISE NOTICE '- CALL maintenance.vacuum_analyze_all()';
    RAISE NOTICE '================================================';
END $$;