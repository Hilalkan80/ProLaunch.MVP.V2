-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS marketplace;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
ALTER DATABASE prolaunch SET search_path TO app, auth, ai, public;

-- Custom types and domains
CREATE TYPE user_role AS ENUM ('admin', 'user', 'manager', 'viewer');
CREATE TYPE subscription_status AS ENUM ('active', 'pending', 'cancelled', 'expired');
CREATE TYPE project_status AS ENUM ('draft', 'active', 'archived', 'completed');
CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'review', 'completed');
CREATE TYPE notification_type AS ENUM ('email', 'push', 'in_app');
CREATE TYPE verification_type AS ENUM ('email', 'phone', 'totp');

CREATE DOMAIN email AS text CHECK (VALUE ~ '^[a-zA-Z0-9.!#$%&''*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$');
CREATE DOMAIN phone AS text CHECK (VALUE ~ '^\+[1-9]\d{1,14}$');
CREATE DOMAIN slug AS text CHECK (VALUE ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$');

-- Create tables with proper relationships

-- Auth Schema
CREATE TABLE auth.users (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    email email UNIQUE NOT NULL,
    password_hash text NOT NULL,
    full_name text NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    is_active boolean NOT NULL DEFAULT true,
    email_verified boolean NOT NULL DEFAULT false,
    phone phone,
    phone_verified boolean NOT NULL DEFAULT false,
    totp_secret text,
    totp_enabled boolean NOT NULL DEFAULT false,
    last_login_at timestamptz,
    failed_login_attempts int NOT NULL DEFAULT 0,
    locked_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE auth.sessions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    refresh_token text NOT NULL,
    user_agent text,
    ip_address inet,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, refresh_token)
);

CREATE TABLE auth.api_keys (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    key_hash text NOT NULL,
    name text NOT NULL,
    expires_at timestamptz,
    last_used_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

-- App Schema
CREATE TABLE app.organizations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name text NOT NULL,
    slug slug UNIQUE NOT NULL,
    description text,
    logo_url text,
    website_url text,
    created_by uuid NOT NULL REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.organization_members (
    organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role user_role NOT NULL DEFAULT 'user',
    joined_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE app.projects (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    name text NOT NULL,
    slug slug NOT NULL,
    description text,
    status project_status NOT NULL DEFAULT 'draft',
    start_date date,
    end_date date,
    created_by uuid NOT NULL REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, slug)
);

CREATE TABLE app.tasks (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id uuid NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    title text NOT NULL,
    description text,
    status task_status NOT NULL DEFAULT 'todo',
    priority int NOT NULL DEFAULT 0,
    assigned_to uuid REFERENCES auth.users(id),
    due_date timestamptz,
    parent_task_id uuid REFERENCES app.tasks(id),
    completion_percentage int NOT NULL DEFAULT 0 CHECK (completion_percentage BETWEEN 0 AND 100),
    created_by uuid NOT NULL REFERENCES auth.users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app.task_dependencies (
    task_id uuid NOT NULL REFERENCES app.tasks(id) ON DELETE CASCADE,
    depends_on_id uuid NOT NULL REFERENCES app.tasks(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (task_id, depends_on_id),
    CHECK (task_id != depends_on_id)
);

-- AI Schema
CREATE TABLE ai.embeddings (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type text NOT NULL,
    content_id uuid NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_type, content_id)
);

CREATE TABLE ai.chat_conversations (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title text NOT NULL,
    context jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ai.chat_messages (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id uuid NOT NULL REFERENCES ai.chat_conversations(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content text NOT NULL,
    tokens_used int,
    embedding vector(1536),
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Notifications Schema
CREATE TABLE notifications.notifications (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    title text NOT NULL,
    content text NOT NULL,
    metadata jsonb,
    read_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Billing Schema
CREATE TABLE billing.subscriptions (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    plan_id text NOT NULL,
    status subscription_status NOT NULL DEFAULT 'pending',
    current_period_start timestamptz NOT NULL,
    current_period_end timestamptz NOT NULL,
    cancel_at_period_end boolean NOT NULL DEFAULT false,
    payment_method_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE billing.usage_records (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id uuid NOT NULL REFERENCES app.organizations(id) ON DELETE CASCADE,
    feature text NOT NULL,
    quantity int NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX users_email_idx ON auth.users (email);
CREATE INDEX users_role_idx ON auth.users (role);
CREATE INDEX sessions_user_id_idx ON auth.sessions (user_id);
CREATE INDEX sessions_expires_at_idx ON auth.sessions (expires_at);
CREATE INDEX api_keys_user_id_idx ON auth.api_keys (user_id);
CREATE INDEX api_keys_expires_at_idx ON auth.api_keys (expires_at);

CREATE INDEX organizations_created_by_idx ON app.organizations (created_by);
CREATE INDEX organization_members_user_id_idx ON app.organization_members (user_id);
CREATE INDEX projects_organization_id_idx ON app.projects (organization_id);
CREATE INDEX projects_status_idx ON app.projects (status);
CREATE INDEX projects_created_by_idx ON app.projects (created_by);

CREATE INDEX tasks_project_id_idx ON app.tasks (project_id);
CREATE INDEX tasks_assigned_to_idx ON app.tasks (assigned_to);
CREATE INDEX tasks_status_idx ON app.tasks (status);
CREATE INDEX tasks_due_date_idx ON app.tasks (due_date);
CREATE INDEX tasks_parent_task_id_idx ON app.tasks (parent_task_id);

CREATE INDEX chat_conversations_user_id_idx ON ai.chat_conversations (user_id);
CREATE INDEX chat_messages_conversation_id_idx ON ai.chat_messages (conversation_id);

CREATE INDEX embeddings_content_type_id_idx ON ai.embeddings (content_type, content_id);
CREATE INDEX embeddings_vector_idx ON ai.embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX notifications_user_id_idx ON notifications.notifications (user_id);
CREATE INDEX notifications_created_at_idx ON notifications.notifications (created_at);
CREATE INDEX notifications_read_at_idx ON notifications.notifications (read_at);

CREATE INDEX subscriptions_organization_id_idx ON billing.subscriptions (organization_id);
CREATE INDEX subscriptions_status_idx ON billing.subscriptions (status);
CREATE INDEX usage_records_organization_id_idx ON billing.usage_records (organization_id);
CREATE INDEX usage_records_feature_idx ON billing.usage_records (feature);

-- Create functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON app.organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON app.projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON app.tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_chat_conversations_updated_at
    BEFORE UPDATE ON ai.chat_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Create roles and permissions
DO $$ BEGIN
    -- Application roles
    CREATE ROLE prolaunch_admin;
    CREATE ROLE prolaunch_app;
    CREATE ROLE prolaunch_readonly;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Grant permissions
GRANT USAGE ON SCHEMA app, auth, ai, notifications, billing TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA notifications TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA billing TO prolaunch_app;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO prolaunch_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA auth TO prolaunch_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA notifications TO prolaunch_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA billing TO prolaunch_app;

-- Read-only permissions
GRANT USAGE ON SCHEMA app, auth, ai, notifications, billing TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA ai TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA notifications TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA billing TO prolaunch_readonly;

-- Create common views
CREATE OR REPLACE VIEW app.user_projects AS
SELECT 
    p.*,
    o.name AS organization_name,
    u.email AS created_by_email,
    u.full_name AS created_by_name,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks
FROM app.projects p
JOIN app.organizations o ON p.organization_id = o.id
JOIN auth.users u ON p.created_by = u.id
LEFT JOIN app.tasks t ON t.project_id = p.id
GROUP BY p.id, o.name, u.email, u.full_name;

CREATE OR REPLACE VIEW app.project_progress AS
SELECT 
    p.id AS project_id,
    p.name AS project_name,
    p.status,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks,
    ROUND(AVG(t.completion_percentage)::numeric, 2) AS avg_completion_percentage,
    MIN(t.due_date) AS next_due_date,
    MAX(t.updated_at) AS last_activity
FROM app.projects p
LEFT JOIN app.tasks t ON t.project_id = p.id
GROUP BY p.id, p.name, p.status;

CREATE OR REPLACE VIEW app.user_task_summary AS
SELECT 
    t.assigned_to,
    u.full_name AS assignee_name,
    COUNT(*) AS total_tasks,
    COUNT(CASE WHEN t.status = 'todo' THEN 1 END) AS todo_tasks,
    COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) AS in_progress_tasks,
    COUNT(CASE WHEN t.status = 'review' THEN 1 END) AS review_tasks,
    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) AS completed_tasks,
    COUNT(CASE WHEN t.due_date < now() AND t.status != 'completed' THEN 1 END) AS overdue_tasks
FROM app.tasks t
JOIN auth.users u ON t.assigned_to = u.id
GROUP BY t.assigned_to, u.full_name;

-- Initialize cron jobs
SELECT cron.schedule(
    'cleanup-expired-sessions',
    '0 0 * * *',  -- Run daily at midnight
    $$DELETE FROM auth.sessions WHERE expires_at < now()$$
);

SELECT cron.schedule(
    'cleanup-expired-notifications',
    '0 0 * * *',  -- Run daily at midnight
    $$DELETE FROM notifications.notifications WHERE created_at < now() - interval '90 days'$$
);

-- Set table storage parameters for frequently updated tables
ALTER TABLE app.tasks SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

ALTER TABLE notifications.notifications SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

ALTER TABLE ai.chat_messages SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);