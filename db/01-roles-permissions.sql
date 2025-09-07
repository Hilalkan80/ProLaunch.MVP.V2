-- =====================================================
-- ProLaunch MVP V2 - Database Roles and Permissions
-- =====================================================
-- Description: Comprehensive role-based access control setup
--              with granular permissions for different user types
-- =====================================================

-- =====================================================
-- 1. DROP EXISTING ROLES (IF ANY)
-- =====================================================

-- Drop existing roles if they exist (for clean setup)
DROP ROLE IF EXISTS prolaunch_super_admin;
DROP ROLE IF EXISTS prolaunch_admin;
DROP ROLE IF EXISTS prolaunch_app;
DROP ROLE IF EXISTS prolaunch_api;
DROP ROLE IF EXISTS prolaunch_readonly;
DROP ROLE IF EXISTS prolaunch_analytics;
DROP ROLE IF EXISTS prolaunch_backup;
DROP ROLE IF EXISTS prolaunch_migration;

-- =====================================================
-- 2. CREATE APPLICATION ROLES
-- =====================================================

-- Super Admin Role (Full database access)
CREATE ROLE prolaunch_super_admin WITH 
    LOGIN 
    SUPERUSER 
    CREATEDB 
    CREATEROLE 
    REPLICATION 
    BYPASSRLS
    PASSWORD 'ChangeMeSuperAdmin123!';

-- Database Admin Role (Schema and object management)
CREATE ROLE prolaunch_admin WITH 
    LOGIN 
    NOSUPERUSER 
    CREATEDB 
    CREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    PASSWORD 'ChangeMeAdmin123!';

-- Application Service Role (Main API access)
CREATE ROLE prolaunch_app WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 100
    PASSWORD 'ChangeMeApp123!';

-- API Service Role (Limited API access for external services)
CREATE ROLE prolaunch_api WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 50
    PASSWORD 'ChangeMeAPI123!';

-- Read-Only Role (For reporting and analytics)
CREATE ROLE prolaunch_readonly WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 20
    PASSWORD 'ChangeMeReadOnly123!';

-- Analytics Role (For BI tools and data analysis)
CREATE ROLE prolaunch_analytics WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 10
    PASSWORD 'ChangeMeAnalytics123!';

-- Backup Role (For automated backup processes)
CREATE ROLE prolaunch_backup WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    REPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 2
    PASSWORD 'ChangeMeBackup123!';

-- Migration Role (For database migrations)
CREATE ROLE prolaunch_migration WITH 
    LOGIN 
    NOSUPERUSER 
    NOCREATEDB 
    NOCREATEROLE 
    NOREPLICATION 
    NOBYPASSRLS
    CONNECTION LIMIT 5
    PASSWORD 'ChangeMeMigration123!';

-- =====================================================
-- 3. DATABASE-LEVEL PERMISSIONS
-- =====================================================

-- Grant database connection permissions
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_app;
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_api;
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_readonly;
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_analytics;
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_backup;
GRANT CONNECT ON DATABASE prolaunch TO prolaunch_migration;

-- Grant temporary table creation for app and migration roles
GRANT TEMPORARY ON DATABASE prolaunch TO prolaunch_app;
GRANT TEMPORARY ON DATABASE prolaunch TO prolaunch_migration;

-- =====================================================
-- 4. SCHEMA-LEVEL PERMISSIONS
-- =====================================================

-- Admin role: Full access to all schemas
GRANT ALL ON SCHEMA public, app, auth, ai, marketplace, audit, analytics TO prolaunch_admin;

-- App role: Full CRUD on application schemas
GRANT USAGE ON SCHEMA app, auth, ai, marketplace TO prolaunch_app;
GRANT CREATE ON SCHEMA app TO prolaunch_app;
GRANT USAGE ON SCHEMA audit, analytics TO prolaunch_app;

-- API role: Limited access to specific schemas
GRANT USAGE ON SCHEMA app, marketplace TO prolaunch_api;

-- Read-only role: Read access to all schemas except audit
GRANT USAGE ON SCHEMA public, app, auth, ai, marketplace, analytics TO prolaunch_readonly;

-- Analytics role: Read access to analytics and app schemas
GRANT USAGE ON SCHEMA app, analytics, marketplace TO prolaunch_analytics;

-- Migration role: Full access to all schemas for migrations
GRANT ALL ON SCHEMA public, app, auth, ai, marketplace, audit, analytics TO prolaunch_migration;

-- =====================================================
-- 5. TABLE-LEVEL PERMISSIONS
-- =====================================================

-- App Role Permissions
-- Full CRUD on main application tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA marketplace TO prolaunch_app;

-- Write-only for audit tables (no read for security)
GRANT INSERT ON ALL TABLES IN SCHEMA audit TO prolaunch_app;

-- Write and read for analytics
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA analytics TO prolaunch_app;

-- API Role Permissions
-- Limited to specific operations
GRANT SELECT ON app.projects, app.milestones, app.tasks TO prolaunch_api;
GRANT SELECT ON marketplace.suppliers, marketplace.supplier_reviews TO prolaunch_api;
GRANT SELECT, INSERT ON ai.chat_conversations, ai.chat_messages TO prolaunch_api;

-- Read-Only Role Permissions
GRANT SELECT ON ALL TABLES IN SCHEMA app TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA ai TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA marketplace TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO prolaunch_readonly;

-- Analytics Role Permissions
GRANT SELECT ON ALL TABLES IN SCHEMA app TO prolaunch_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA marketplace TO prolaunch_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO prolaunch_analytics;
GRANT SELECT, INSERT, UPDATE ON analytics.user_analytics TO prolaunch_analytics;
GRANT SELECT, INSERT, UPDATE ON analytics.project_analytics TO prolaunch_analytics;

-- Migration Role Permissions
GRANT ALL ON ALL TABLES IN SCHEMA app TO prolaunch_migration;
GRANT ALL ON ALL TABLES IN SCHEMA auth TO prolaunch_migration;
GRANT ALL ON ALL TABLES IN SCHEMA ai TO prolaunch_migration;
GRANT ALL ON ALL TABLES IN SCHEMA marketplace TO prolaunch_migration;
GRANT ALL ON ALL TABLES IN SCHEMA audit TO prolaunch_migration;
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO prolaunch_migration;

-- =====================================================
-- 6. SEQUENCE PERMISSIONS
-- =====================================================

-- Grant sequence permissions to roles that need to insert data
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA marketplace TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO prolaunch_app;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_api;

GRANT ALL ON ALL SEQUENCES IN SCHEMA app TO prolaunch_migration;
GRANT ALL ON ALL SEQUENCES IN SCHEMA auth TO prolaunch_migration;
GRANT ALL ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_migration;
GRANT ALL ON ALL SEQUENCES IN SCHEMA marketplace TO prolaunch_migration;
GRANT ALL ON ALL SEQUENCES IN SCHEMA audit TO prolaunch_migration;
GRANT ALL ON ALL SEQUENCES IN SCHEMA analytics TO prolaunch_migration;

-- =====================================================
-- 7. FUNCTION PERMISSIONS
-- =====================================================

-- Grant execute permissions on functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO prolaunch_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO prolaunch_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ai TO prolaunch_app;

-- Grant specific function permissions to API role
GRANT EXECUTE ON FUNCTION search_similar_content(vector, text, integer, float) TO prolaunch_api;
GRANT EXECUTE ON FUNCTION calculate_project_completion(uuid) TO prolaunch_api;

-- Grant function permissions to analytics role
GRANT EXECUTE ON FUNCTION calculate_project_completion(uuid) TO prolaunch_analytics;

-- =====================================================
-- 8. VIEW PERMISSIONS
-- =====================================================

-- Grant view permissions
GRANT SELECT ON ALL TABLES IN SCHEMA app TO prolaunch_app;
GRANT SELECT ON app.v_active_users TO prolaunch_app, prolaunch_api, prolaunch_readonly;
GRANT SELECT ON app.v_project_overview TO prolaunch_app, prolaunch_api, prolaunch_readonly;
GRANT SELECT ON app.v_milestone_progress TO prolaunch_app, prolaunch_api, prolaunch_readonly;
GRANT SELECT ON analytics.v_user_activity_summary TO prolaunch_analytics, prolaunch_readonly;
GRANT SELECT ON marketplace.v_supplier_rankings TO prolaunch_app, prolaunch_api, prolaunch_readonly;
GRANT SELECT ON ai.v_recent_conversations TO prolaunch_app, prolaunch_readonly;

-- =====================================================
-- 9. DEFAULT PRIVILEGES
-- =====================================================

-- Set default privileges for future objects created by admin
ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA app 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prolaunch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA auth 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prolaunch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA ai 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prolaunch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA marketplace 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO prolaunch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA audit 
    GRANT INSERT ON TABLES TO prolaunch_app;

ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin IN SCHEMA analytics 
    GRANT SELECT, INSERT, UPDATE ON TABLES TO prolaunch_app;

-- Set default privileges for sequences
ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin 
    GRANT USAGE, SELECT ON SEQUENCES TO prolaunch_app;

-- Set default privileges for functions
ALTER DEFAULT PRIVILEGES FOR ROLE prolaunch_admin 
    GRANT EXECUTE ON FUNCTIONS TO prolaunch_app;

-- =====================================================
-- 10. ROW-LEVEL SECURITY POLICIES
-- =====================================================

-- Create RLS policies for app role
-- These policies ensure users can only access their own data

-- Policy for users table
CREATE POLICY app_users_select ON auth.users
    FOR SELECT
    TO prolaunch_app
    USING (
        id = current_setting('app.current_user_id', true)::UUID
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

CREATE POLICY app_users_update ON auth.users
    FOR UPDATE
    TO prolaunch_app
    USING (id = current_setting('app.current_user_id', true)::UUID)
    WITH CHECK (id = current_setting('app.current_user_id', true)::UUID);

-- Policy for projects
CREATE POLICY app_projects_all ON app.projects
    FOR ALL
    TO prolaunch_app
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR is_public = true
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- Policy for tasks
CREATE POLICY app_tasks_all ON app.tasks
    FOR ALL
    TO prolaunch_app
    USING (
        project_id IN (
            SELECT id FROM app.projects 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
            UNION
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- Policy for documents
CREATE POLICY app_documents_all ON app.documents
    FOR ALL
    TO prolaunch_app
    USING (
        project_id IN (
            SELECT id FROM app.projects 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
            UNION
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR id IN (
            SELECT document_id FROM app.document_collaborators 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- Policy for chat conversations
CREATE POLICY app_chat_conversations_all ON ai.chat_conversations
    FOR ALL
    TO prolaunch_app
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR project_id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- =====================================================
-- 11. SECURITY DEFINER FUNCTIONS
-- =====================================================

-- Function to safely check user permissions
CREATE OR REPLACE FUNCTION auth.check_user_permission(
    p_user_id UUID,
    p_resource_type TEXT,
    p_resource_id UUID,
    p_permission TEXT
) RETURNS BOOLEAN
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    has_permission BOOLEAN := FALSE;
BEGIN
    -- Check based on resource type
    CASE p_resource_type
        WHEN 'project' THEN
            SELECT EXISTS (
                SELECT 1 FROM app.projects 
                WHERE id = p_resource_id 
                AND (user_id = p_user_id OR id IN (
                    SELECT project_id FROM app.project_members 
                    WHERE user_id = p_user_id
                ))
            ) INTO has_permission;
            
        WHEN 'document' THEN
            SELECT EXISTS (
                SELECT 1 FROM app.documents d
                WHERE d.id = p_resource_id 
                AND (
                    d.created_by = p_user_id 
                    OR EXISTS (
                        SELECT 1 FROM app.document_collaborators 
                        WHERE document_id = p_resource_id 
                        AND user_id = p_user_id
                    )
                )
            ) INTO has_permission;
            
        WHEN 'task' THEN
            SELECT EXISTS (
                SELECT 1 FROM app.tasks t
                WHERE t.id = p_resource_id 
                AND (
                    t.assigned_to = p_user_id 
                    OR t.created_by = p_user_id
                    OR EXISTS (
                        SELECT 1 FROM app.projects p
                        WHERE p.id = t.project_id 
                        AND (p.user_id = p_user_id OR p.id IN (
                            SELECT project_id FROM app.project_members 
                            WHERE user_id = p_user_id
                        ))
                    )
                )
            ) INTO has_permission;
            
        ELSE
            has_permission := FALSE;
    END CASE;
    
    RETURN has_permission;
END;
$$;

-- Grant execute on security functions
GRANT EXECUTE ON FUNCTION auth.check_user_permission(UUID, TEXT, UUID, TEXT) TO prolaunch_app, prolaunch_api;

-- =====================================================
-- 12. AUDIT ROLE PERMISSIONS
-- =====================================================

-- Create audit function that only specific roles can execute
CREATE OR REPLACE FUNCTION audit.log_activity_secure(
    p_user_id UUID,
    p_action TEXT,
    p_entity_type TEXT,
    p_entity_id UUID,
    p_metadata JSONB
) RETURNS UUID
SECURITY DEFINER
LANGUAGE plpgsql
AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO audit.activity_logs (
        user_id,
        action,
        entity_type,
        entity_id,
        metadata,
        ip_address,
        created_at
    ) VALUES (
        p_user_id,
        p_action,
        p_entity_type,
        p_entity_id,
        p_metadata,
        inet_client_addr(),
        CURRENT_TIMESTAMP
    ) RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$;

-- Grant execute only to app role
GRANT EXECUTE ON FUNCTION audit.log_activity_secure(UUID, TEXT, TEXT, UUID, JSONB) TO prolaunch_app;

-- =====================================================
-- 13. CONNECTION POOLING SETTINGS
-- =====================================================

-- Set connection pooling parameters for each role
ALTER ROLE prolaunch_app SET statement_timeout = '30s';
ALTER ROLE prolaunch_app SET idle_in_transaction_session_timeout = '5min';

ALTER ROLE prolaunch_api SET statement_timeout = '10s';
ALTER ROLE prolaunch_api SET idle_in_transaction_session_timeout = '1min';

ALTER ROLE prolaunch_readonly SET statement_timeout = '1min';
ALTER ROLE prolaunch_analytics SET statement_timeout = '5min';

-- =====================================================
-- 14. ROLE MEMBERSHIP
-- =====================================================

-- Create role hierarchies
GRANT prolaunch_readonly TO prolaunch_analytics;
GRANT prolaunch_readonly TO prolaunch_app;
GRANT prolaunch_app TO prolaunch_admin;

-- =====================================================
-- 15. SECURITY NOTES
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'SECURITY CONFIGURATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'IMPORTANT: Change all default passwords immediately!';
    RAISE NOTICE '';
    RAISE NOTICE 'Roles created:';
    RAISE NOTICE '1. prolaunch_super_admin - Full database access';
    RAISE NOTICE '2. prolaunch_admin - Schema and object management';
    RAISE NOTICE '3. prolaunch_app - Main application access';
    RAISE NOTICE '4. prolaunch_api - Limited API access';
    RAISE NOTICE '5. prolaunch_readonly - Read-only access';
    RAISE NOTICE '6. prolaunch_analytics - Analytics and reporting';
    RAISE NOTICE '7. prolaunch_backup - Backup operations';
    RAISE NOTICE '8. prolaunch_migration - Migration operations';
    RAISE NOTICE '';
    RAISE NOTICE 'Security features enabled:';
    RAISE NOTICE '- Row-level security policies';
    RAISE NOTICE '- Connection limits per role';
    RAISE NOTICE '- Statement timeouts';
    RAISE NOTICE '- Granular table permissions';
    RAISE NOTICE '- Security definer functions';
    RAISE NOTICE '========================================';
END $$;