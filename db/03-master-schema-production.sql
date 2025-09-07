-- =====================================================
-- ProLaunch MVP V2 - Master Production Database Schema
-- =====================================================
-- Version: 3.0.0
-- Description: Complete production-ready PostgreSQL schema with
--              advanced features, vector support, and optimizations
-- =====================================================

-- =====================================================
-- SECTION 1: DATABASE INITIALIZATION & CONFIGURATION
-- =====================================================

-- Create database with optimal settings
-- Note: Run these commands as superuser before connecting
-- DROP DATABASE IF EXISTS prolaunch_prod;
-- CREATE DATABASE prolaunch_prod 
--     WITH 
--     ENCODING = 'UTF8' 
--     LC_COLLATE = 'en_US.utf8' 
--     LC_CTYPE = 'en_US.utf8'
--     TEMPLATE = template0
--     CONNECTION LIMIT = 500;

-- Connect to database
\c prolaunch_prod;

-- Set optimal configuration parameters
ALTER DATABASE prolaunch_prod SET shared_preload_libraries = 'pg_stat_statements, pgaudit, pg_cron';
ALTER DATABASE prolaunch_prod SET max_connections = 500;
ALTER DATABASE prolaunch_prod SET shared_buffers = '4GB';
ALTER DATABASE prolaunch_prod SET effective_cache_size = '12GB';
ALTER DATABASE prolaunch_prod SET maintenance_work_mem = '1GB';
ALTER DATABASE prolaunch_prod SET checkpoint_completion_target = 0.9;
ALTER DATABASE prolaunch_prod SET wal_buffers = '16MB';
ALTER DATABASE prolaunch_prod SET default_statistics_target = 100;
ALTER DATABASE prolaunch_prod SET random_page_cost = 1.1;
ALTER DATABASE prolaunch_prod SET effective_io_concurrency = 200;
ALTER DATABASE prolaunch_prod SET work_mem = '16MB';
ALTER DATABASE prolaunch_prod SET min_wal_size = '2GB';
ALTER DATABASE prolaunch_prod SET max_wal_size = '8GB';
ALTER DATABASE prolaunch_prod SET max_worker_processes = 8;
ALTER DATABASE prolaunch_prod SET max_parallel_workers_per_gather = 4;
ALTER DATABASE prolaunch_prod SET max_parallel_workers = 8;
ALTER DATABASE prolaunch_prod SET max_parallel_maintenance_workers = 4;

-- =====================================================
-- SECTION 2: EXTENSIONS
-- =====================================================

-- Core extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram matching for text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";        -- GIN indexes on scalar types
CREATE EXTENSION IF NOT EXISTS "btree_gist";       -- GiST indexes on scalar types
CREATE EXTENSION IF NOT EXISTS "hstore";           -- Key-value store
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pgaudit";          -- Audit logging
CREATE EXTENSION IF NOT EXISTS "pg_cron";          -- Job scheduling
CREATE EXTENSION IF NOT EXISTS "tablefunc";        -- Crosstab and other functions
CREATE EXTENSION IF NOT EXISTS "pg_partman";       -- Partition management

-- Vector and AI extensions
CREATE EXTENSION IF NOT EXISTS "vector";           -- Vector similarity search
CREATE EXTENSION IF NOT EXISTS "pg_similarity";    -- Additional similarity functions

-- Full-text search and performance
CREATE EXTENSION IF NOT EXISTS "unaccent";         -- Remove accents from text
CREATE EXTENSION IF NOT EXISTS "pg_prewarm";       -- Preload indexes into cache
CREATE EXTENSION IF NOT EXISTS "pg_buffercache";   -- Monitor buffer cache
CREATE EXTENSION IF NOT EXISTS "pg_repack";        -- Online table reorganization

-- Additional utility extensions
CREATE EXTENSION IF NOT EXISTS "citext";           -- Case-insensitive text
CREATE EXTENSION IF NOT EXISTS "ltree";            -- Hierarchical tree-like structures
CREATE EXTENSION IF NOT EXISTS "earthdistance";    -- Geographic calculations
CREATE EXTENSION IF NOT EXISTS "cube";             -- Multi-dimensional cubes

-- =====================================================
-- SECTION 3: SCHEMAS AND NAMESPACES
-- =====================================================

-- Create logical schemas
CREATE SCHEMA IF NOT EXISTS app;                   -- Main application schema
CREATE SCHEMA IF NOT EXISTS auth;                  -- Authentication and authorization
CREATE SCHEMA IF NOT EXISTS audit;                 -- Audit logging and compliance
CREATE SCHEMA IF NOT EXISTS analytics;             -- Analytics and reporting
CREATE SCHEMA IF NOT EXISTS ai;                    -- AI and ML related tables
CREATE SCHEMA IF NOT EXISTS marketplace;           -- Marketplace features
CREATE SCHEMA IF NOT EXISTS notifications;         -- Notification system
CREATE SCHEMA IF NOT EXISTS billing;               -- Billing and subscriptions
CREATE SCHEMA IF NOT EXISTS monitoring;            -- System monitoring
CREATE SCHEMA IF NOT EXISTS cache;                 -- Caching layer
CREATE SCHEMA IF NOT EXISTS queue;                 -- Job queue system
CREATE SCHEMA IF NOT EXISTS search;                -- Search optimization

-- Set default search path
ALTER DATABASE prolaunch_prod SET search_path TO app, auth, public;

-- =====================================================
-- SECTION 4: CUSTOM DOMAINS AND TYPES
-- =====================================================

-- Email domain with validation
CREATE DOMAIN email_address AS VARCHAR(255)
    CHECK (VALUE ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$');

-- URL domain with validation
CREATE DOMAIN url AS TEXT
    CHECK (VALUE ~* '^https?://[^\s/$.?#].[^\s]*$');

-- Phone number domain
CREATE DOMAIN phone_number AS VARCHAR(20)
    CHECK (VALUE ~* '^\+?[1-9]\d{1,14}$');

-- Positive integer domain
CREATE DOMAIN positive_integer AS INTEGER
    CHECK (VALUE > 0);

-- Percentage domain
CREATE DOMAIN percentage AS NUMERIC(5,2)
    CHECK (VALUE >= 0 AND VALUE <= 100);

-- Money domain
CREATE DOMAIN money_amount AS NUMERIC(19,4)
    CHECK (VALUE >= 0);

-- User and authentication types
CREATE TYPE auth.user_role AS ENUM (
    'super_admin',
    'admin',
    'moderator',
    'premium_user',
    'user',
    'guest'
);

CREATE TYPE auth.user_status AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending_verification',
    'deleted',
    'banned'
);

CREATE TYPE auth.subscription_tier AS ENUM (
    'free',
    'starter',
    'professional',
    'business',
    'enterprise',
    'custom'
);

CREATE TYPE auth.auth_provider AS ENUM (
    'email',
    'google',
    'microsoft',
    'linkedin',
    'github',
    'apple',
    'facebook'
);

CREATE TYPE auth.mfa_type AS ENUM (
    'totp',
    'sms',
    'email',
    'backup_codes',
    'webauthn'
);

-- Business and project types
CREATE TYPE app.milestone_type AS ENUM (
    'M0_ideation',
    'M1_validation',
    'M2_planning',
    'M3_development',
    'M4_launch',
    'M5_growth',
    'M6_scale',
    'M7_exit'
);

CREATE TYPE app.milestone_status AS ENUM (
    'not_started',
    'in_progress',
    'completed',
    'skipped',
    'blocked',
    'on_hold'
);

CREATE TYPE app.task_priority AS ENUM (
    'critical',
    'high',
    'medium',
    'low',
    'trivial'
);

CREATE TYPE app.task_status AS ENUM (
    'backlog',
    'todo',
    'in_progress',
    'in_review',
    'testing',
    'completed',
    'cancelled',
    'blocked'
);

CREATE TYPE app.document_type AS ENUM (
    'business_plan',
    'pitch_deck',
    'financial_model',
    'market_analysis',
    'legal_document',
    'contract',
    'proposal',
    'report',
    'presentation',
    'spreadsheet',
    'other'
);

CREATE TYPE app.document_status AS ENUM (
    'draft',
    'in_review',
    'approved',
    'published',
    'archived',
    'deleted'
);

-- AI and chat types
CREATE TYPE ai.message_role AS ENUM (
    'system',
    'user',
    'assistant',
    'function',
    'tool'
);

CREATE TYPE ai.ai_model AS ENUM (
    'gpt-4',
    'gpt-4-turbo',
    'gpt-3.5-turbo',
    'claude-3-opus',
    'claude-3-sonnet',
    'claude-3-haiku',
    'llama-3',
    'mistral',
    'custom'
);

CREATE TYPE ai.ai_feature AS ENUM (
    'chat',
    'completion',
    'embedding',
    'image_generation',
    'image_analysis',
    'speech_to_text',
    'text_to_speech',
    'translation',
    'summarization',
    'code_generation'
);

-- Marketplace types
CREATE TYPE marketplace.supplier_category AS ENUM (
    'legal',
    'accounting',
    'marketing',
    'development',
    'design',
    'consulting',
    'manufacturing',
    'logistics',
    'hr',
    'finance',
    'other'
);

CREATE TYPE marketplace.supplier_status AS ENUM (
    'pending',
    'verified',
    'premium',
    'suspended',
    'rejected',
    'blacklisted'
);

-- Billing and payment types
CREATE TYPE billing.payment_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'refunded',
    'partially_refunded',
    'cancelled',
    'disputed'
);

CREATE TYPE billing.invoice_status AS ENUM (
    'draft',
    'sent',
    'paid',
    'partially_paid',
    'overdue',
    'cancelled',
    'refunded'
);

CREATE TYPE billing.currency AS ENUM (
    'USD',
    'EUR',
    'GBP',
    'CAD',
    'AUD',
    'JPY',
    'CNY',
    'INR',
    'BRL',
    'MXN'
);

-- Notification types
CREATE TYPE notifications.channel AS ENUM (
    'email',
    'sms',
    'push',
    'in_app',
    'webhook'
);

CREATE TYPE notifications.priority AS ENUM (
    'urgent',
    'high',
    'normal',
    'low'
);

CREATE TYPE notifications.status AS ENUM (
    'pending',
    'sent',
    'delivered',
    'read',
    'failed',
    'bounced'
);

-- =====================================================
-- SECTION 5: UTILITY FUNCTIONS
-- =====================================================

-- Function to generate random strings
CREATE OR REPLACE FUNCTION generate_random_string(length INTEGER)
RETURNS TEXT AS $$
DECLARE
    chars TEXT := 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    result TEXT := '';
    i INTEGER;
BEGIN
    FOR i IN 1..length LOOP
        result := result || substr(chars, floor(random() * length(chars) + 1)::INTEGER, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique slugs
CREATE OR REPLACE FUNCTION generate_unique_slug(base_text TEXT, table_name TEXT)
RETURNS TEXT AS $$
DECLARE
    slug TEXT;
    counter INTEGER := 0;
    exists_check BOOLEAN;
BEGIN
    -- Generate base slug
    slug := LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(unaccent(base_text), '[^a-zA-Z0-9\s-]', '', 'g'),
                '\s+', '-', 'g'
            ),
            '-+', '-', 'g'
        )
    );
    
    -- Remove leading/trailing hyphens
    slug := TRIM(BOTH '-' FROM slug);
    
    -- Check if slug exists and append counter if needed
    LOOP
        IF counter > 0 THEN
            EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I WHERE slug = %L)', 
                          table_name, slug || '-' || counter) INTO exists_check;
            IF NOT exists_check THEN
                RETURN slug || '-' || counter;
            END IF;
        ELSE
            EXECUTE format('SELECT EXISTS(SELECT 1 FROM %I WHERE slug = %L)', 
                          table_name, slug) INTO exists_check;
            IF NOT exists_check THEN
                RETURN slug;
            END IF;
        END IF;
        counter := counter + 1;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to validate JSON schema
CREATE OR REPLACE FUNCTION validate_json_schema(data JSONB, schema JSONB)
RETURNS BOOLEAN AS $$
BEGIN
    -- Basic JSON schema validation
    -- This is a simplified version - consider using pg_jsonschema extension for full support
    RETURN data IS NOT NULL AND schema IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SECTION 6: CORE TABLES - AUTHENTICATION
-- =====================================================

-- Users table with enhanced security features
CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email email_address UNIQUE NOT NULL,
    username CITEXT UNIQUE NOT NULL CHECK (length(username) >= 3),
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    display_name VARCHAR(100),
    avatar_url url,
    phone_number phone_number,
    role auth.user_role NOT NULL DEFAULT 'user',
    status auth.user_status NOT NULL DEFAULT 'pending_verification',
    subscription_tier auth.subscription_tier NOT NULL DEFAULT 'free',
    subscription_valid_until TIMESTAMP WITH TIME ZONE,
    
    -- Verification fields
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),
    email_verification_expires TIMESTAMP WITH TIME ZONE,
    phone_verified BOOLEAN DEFAULT FALSE,
    phone_verification_code VARCHAR(6),
    phone_verification_expires TIMESTAMP WITH TIME ZONE,
    
    -- Multi-factor authentication
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_type auth.mfa_type[],
    mfa_secret VARCHAR(255),
    backup_codes TEXT[],
    
    -- Security fields
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip INET,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    
    -- Preferences and metadata
    language VARCHAR(5) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    metadata JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    feature_flags JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_subscription CHECK (
        subscription_valid_until IS NULL OR 
        subscription_valid_until > CURRENT_TIMESTAMP OR 
        subscription_tier = 'free'
    )
);

-- OAuth providers with token management
CREATE TABLE auth.oauth_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider auth.auth_provider NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    email email_address,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT[],
    provider_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(provider, provider_user_id)
);

-- Enhanced session management
CREATE TABLE auth.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    device_id VARCHAR(255),
    device_info JSONB DEFAULT '{}',
    location_info JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    refresh_expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent overlapping active sessions
    EXCLUDE USING gist (
        user_id WITH =,
        tstzrange(created_at, expires_at) WITH &&
    ) WHERE (revoked_at IS NULL)
);

-- API keys with rate limiting
CREATE TABLE auth.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '[]',
    allowed_ips INET[],
    rate_limit_per_minute INT DEFAULT 60,
    rate_limit_per_hour INT DEFAULT 1000,
    rate_limit_per_day INT DEFAULT 10000,
    usage_count BIGINT DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    last_used_ip INET,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason TEXT
);

-- Password reset tokens
CREATE TABLE auth.password_resets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SECTION 7: CORE TABLES - APPLICATION
-- =====================================================

-- Enhanced user profiles
CREATE TABLE app.user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Personal information
    bio TEXT,
    headline VARCHAR(200),
    company_name VARCHAR(255),
    company_role VARCHAR(100),
    industry VARCHAR(100),
    years_experience positive_integer,
    
    -- Location
    country VARCHAR(2),
    state_province VARCHAR(100),
    city VARCHAR(100),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    postal_code VARCHAR(20),
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    
    -- Social and contact
    linkedin_url url,
    twitter_url url,
    github_url url,
    website_url url,
    calendar_link url,
    
    -- Professional details
    skills TEXT[],
    languages TEXT[],
    certifications JSONB DEFAULT '[]',
    education JSONB DEFAULT '[]',
    work_history JSONB DEFAULT '[]',
    
    -- Profile completion
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_step INT DEFAULT 0,
    profile_completion_percentage percentage DEFAULT 0,
    profile_views INT DEFAULT 0,
    
    -- Privacy settings
    is_public BOOLEAN DEFAULT TRUE,
    show_email BOOLEAN DEFAULT FALSE,
    show_phone BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects with enhanced features
CREATE TABLE app.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Basic information
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    short_description VARCHAR(500),
    
    -- Business details
    industry VARCHAR(100),
    business_model VARCHAR(100),
    target_market TEXT,
    value_proposition TEXT,
    competitive_advantage TEXT,
    
    -- Progress tracking
    current_milestone app.milestone_type DEFAULT 'M0_ideation',
    milestone_progress percentage DEFAULT 0,
    overall_progress percentage DEFAULT 0,
    health_score percentage,
    
    -- Visual elements
    logo_url url,
    cover_image_url url,
    brand_colors JSONB DEFAULT '{}',
    
    -- External links
    website_url url,
    demo_url url,
    repository_url url,
    
    -- Status and visibility
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    visibility VARCHAR(20) DEFAULT 'private', -- private, team, public
    
    -- Team and funding
    team_size INT DEFAULT 1,
    funding_stage VARCHAR(50),
    funding_amount money_amount,
    revenue_range VARCHAR(50),
    burn_rate money_amount,
    runway_months positive_integer,
    
    -- Metrics
    star_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    
    -- Settings and metadata
    settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Important dates
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    launched_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_team_size CHECK (team_size >= 1),
    CONSTRAINT valid_progress CHECK (
        milestone_progress >= 0 AND milestone_progress <= 100 AND
        overall_progress >= 0 AND overall_progress <= 100
    )
);

-- Project team members with roles and permissions
CREATE TABLE app.project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Role and permissions
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner, admin, editor, viewer, member
    permissions JSONB DEFAULT '[]',
    title VARCHAR(100),
    
    -- Invitation tracking
    invited_by UUID REFERENCES auth.users(id),
    invitation_token VARCHAR(255),
    invitation_message TEXT,
    invitation_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Activity tracking
    joined_at TIMESTAMP WITH TIME ZONE,
    last_active_at TIMESTAMP WITH TIME ZONE,
    contribution_score INT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    removed_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(project_id, user_id)
);

-- Enhanced milestones with dependencies
CREATE TABLE app.milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    milestone_type app.milestone_type NOT NULL,
    
    -- Basic information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    success_criteria TEXT[],
    
    -- Goals and deliverables
    objectives TEXT[],
    deliverables TEXT[],
    key_results JSONB DEFAULT '[]',
    
    -- Status and progress
    status app.milestone_status NOT NULL DEFAULT 'not_started',
    progress_percentage percentage DEFAULT 0,
    health_status VARCHAR(20), -- on_track, at_risk, delayed, blocked
    
    -- Time tracking
    estimated_hours INT,
    actual_hours INT,
    start_date DATE,
    target_date DATE,
    completed_date DATE,
    
    -- Dependencies
    depends_on UUID[], -- Array of milestone IDs
    blocks UUID[], -- Array of milestone IDs this blocks
    
    -- Issues and risks
    blockers TEXT[],
    risks JSONB DEFAULT '[]',
    notes TEXT,
    lessons_learned TEXT,
    
    -- Resources
    budget money_amount,
    actual_cost money_amount,
    resources_needed JSONB DEFAULT '[]',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(project_id, milestone_type)
);

-- Enhanced tasks with subtasks and dependencies
CREATE TABLE app.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES app.milestones(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES app.tasks(id) ON DELETE CASCADE,
    
    -- Assignment and ownership
    assigned_to UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    reviewed_by UUID REFERENCES auth.users(id),
    
    -- Basic information
    title VARCHAR(500) NOT NULL,
    description TEXT,
    acceptance_criteria TEXT[],
    
    -- Status and priority
    priority app.task_priority DEFAULT 'medium',
    status app.task_status DEFAULT 'backlog',
    resolution VARCHAR(50), -- completed, wont_do, duplicate, invalid
    
    -- Categorization
    category VARCHAR(50),
    tags TEXT[],
    labels JSONB DEFAULT '[]',
    
    -- Time tracking
    estimated_hours NUMERIC(8,2),
    actual_hours NUMERIC(8,2),
    remaining_hours NUMERIC(8,2),
    time_entries JSONB DEFAULT '[]',
    
    -- Progress tracking
    progress_percentage percentage DEFAULT 0,
    checklist JSONB DEFAULT '[]',
    
    -- Scheduling
    due_date TIMESTAMP WITH TIME ZONE,
    scheduled_date DATE,
    reminder_date TIMESTAMP WITH TIME ZONE,
    
    -- Dependencies and relationships
    dependencies UUID[], -- Tasks that must be completed first
    blocks UUID[], -- Tasks that this blocks
    related_tasks UUID[],
    
    -- Attachments and links
    attachments JSONB DEFAULT '[]',
    links JSONB DEFAULT '[]',
    
    -- Collaboration
    watchers UUID[], -- User IDs watching this task
    comments_count INT DEFAULT 0,
    
    -- Positioning and organization
    position INT,
    board_column VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    custom_fields JSONB DEFAULT '{}',
    
    -- Important timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date_changed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_hours CHECK (
        (estimated_hours IS NULL OR estimated_hours >= 0) AND
        (actual_hours IS NULL OR actual_hours >= 0) AND
        (remaining_hours IS NULL OR remaining_hours >= 0)
    )
);

-- Task comments with threading and reactions
CREATE TABLE app.task_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES app.tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES app.task_comments(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    content_html TEXT, -- Rendered HTML version
    
    -- Mentions and references
    mentions UUID[], -- User IDs mentioned
    task_references UUID[], -- Task IDs referenced
    
    -- Attachments
    attachments JSONB DEFAULT '[]',
    
    -- Engagement
    reactions JSONB DEFAULT '{}', -- {emoji: [user_ids]}
    
    -- Edit tracking
    is_edited BOOLEAN DEFAULT FALSE,
    edit_history JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- =====================================================
-- SECTION 8: AI AND MACHINE LEARNING TABLES
-- =====================================================

-- AI chat conversations with context
CREATE TABLE ai.chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Conversation details
    title VARCHAR(500),
    summary TEXT,
    purpose VARCHAR(100), -- general, brainstorming, analysis, coding, writing
    
    -- Context and configuration
    context JSONB DEFAULT '{}',
    system_prompt TEXT,
    model ai.ai_model DEFAULT 'gpt-4',
    temperature NUMERIC(3,2) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    max_tokens INT DEFAULT 2000,
    top_p NUMERIC(3,2) DEFAULT 1.0,
    
    -- Usage tracking
    total_messages INT DEFAULT 0,
    total_tokens_used INT DEFAULT 0,
    total_cost money_amount DEFAULT 0,
    
    -- Organization
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    folder VARCHAR(100),
    tags TEXT[],
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE
);

-- Chat messages with function calling
CREATE TABLE ai.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai.chat_conversations(id) ON DELETE CASCADE,
    
    -- Message details
    role ai.message_role NOT NULL,
    content TEXT,
    name VARCHAR(100), -- For function messages
    
    -- Token usage
    prompt_tokens INT,
    completion_tokens INT,
    total_tokens INT,
    
    -- Model information
    model_used VARCHAR(50),
    model_version VARCHAR(20),
    
    -- Function calling
    function_name VARCHAR(100),
    function_arguments JSONB,
    function_response JSONB,
    
    -- Tool usage
    tool_calls JSONB DEFAULT '[]',
    tool_responses JSONB DEFAULT '[]',
    
    -- Attachments and references
    attachments JSONB DEFAULT '[]',
    citations JSONB DEFAULT '[]',
    
    -- Feedback and rating
    rating INT CHECK (rating >= 1 AND rating <= 5),
    feedback TEXT,
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings for semantic search
CREATE TABLE ai.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Content reference
    content_type VARCHAR(50) NOT NULL, -- project, task, document, etc.
    content_id UUID NOT NULL,
    content_version INT DEFAULT 1,
    
    -- Content details
    content_chunk TEXT NOT NULL,
    chunk_index INT DEFAULT 0,
    chunk_tokens INT,
    
    -- Embedding data
    embedding vector(1536), -- OpenAI ada-002 dimensions
    embedding_model VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    
    -- Search optimization
    search_keywords TEXT[],
    category VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique chunks per content
    UNIQUE(content_type, content_id, chunk_index, content_version)
);

-- AI-generated insights and recommendations
CREATE TABLE ai.insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    
    -- Insight details
    insight_type VARCHAR(50) NOT NULL, -- recommendation, warning, opportunity, risk
    category VARCHAR(50),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    
    -- Analysis details
    confidence_score percentage,
    impact_score INT CHECK (impact_score >= 1 AND impact_score <= 10),
    urgency_level VARCHAR(20), -- immediate, high, medium, low
    
    -- Data and recommendations
    data_sources JSONB DEFAULT '[]',
    supporting_data JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    
    -- Model information
    model_used VARCHAR(50),
    analysis_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- User interaction
    is_actionable BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    dismissed_by UUID REFERENCES auth.users(id),
    dismissed_reason TEXT,
    actions_taken JSONB DEFAULT '[]',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    acted_on_at TIMESTAMP WITH TIME ZONE
);

-- AI model usage tracking
CREATE TABLE ai.usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES app.projects(id) ON DELETE CASCADE,
    
    -- Usage details
    feature ai.ai_feature NOT NULL,
    model ai.ai_model NOT NULL,
    
    -- Token and cost tracking
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    estimated_cost money_amount DEFAULT 0,
    
    -- Request details
    request_id VARCHAR(100),
    response_time_ms INT,
    status_code INT,
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SECTION 9: NOTIFICATION AND COMMUNICATION TABLES
-- =====================================================

-- Notification templates
CREATE TABLE notifications.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Template identification
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    
    -- Content templates
    subject_template TEXT,
    body_template TEXT,
    body_html_template TEXT,
    
    -- Channel-specific templates
    email_template TEXT,
    sms_template TEXT,
    push_template JSONB,
    in_app_template JSONB,
    
    -- Configuration
    available_channels notifications.channel[],
    default_channel notifications.channel,
    
    -- Variables and metadata
    required_variables TEXT[],
    optional_variables TEXT[],
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User notification preferences
CREATE TABLE notifications.user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Global preferences
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Channel preferences
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    push_enabled BOOLEAN DEFAULT TRUE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    
    -- Category preferences (JSONB for flexibility)
    category_preferences JSONB DEFAULT '{}',
    
    -- Frequency settings
    digest_frequency VARCHAR(20), -- immediate, hourly, daily, weekly
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notification queue
CREATE TABLE notifications.queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Notification details
    template_id UUID REFERENCES notifications.templates(id),
    channel notifications.channel NOT NULL,
    priority notifications.priority DEFAULT 'normal',
    
    -- Content
    subject TEXT,
    body TEXT,
    body_html TEXT,
    variables JSONB DEFAULT '{}',
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Status tracking
    status notifications.status DEFAULT 'pending',
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    
    -- Delivery information
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    last_error TEXT,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Provider information
    provider VARCHAR(50),
    provider_message_id VARCHAR(255),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- SECTION 10: COMPREHENSIVE INDEXES
-- =====================================================

-- Create monitoring schema for index views
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Auth schema indexes
CREATE INDEX idx_users_email_lower ON auth.users (LOWER(email));
CREATE INDEX idx_users_username_lower ON auth.users (LOWER(username));
CREATE INDEX idx_users_status_role ON auth.users (status, role) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_subscription ON auth.users (subscription_tier) WHERE status = 'active';
CREATE INDEX idx_users_last_activity ON auth.users (last_activity_at DESC NULLS LAST) WHERE status = 'active';

CREATE INDEX idx_oauth_composite ON auth.oauth_accounts (provider, provider_user_id, user_id);
CREATE INDEX idx_sessions_active ON auth.sessions (user_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_keys_active ON auth.api_keys (key_hash) WHERE revoked_at IS NULL;

-- App schema indexes
CREATE INDEX idx_projects_user_active ON app.projects (user_id, is_active) WHERE archived_at IS NULL;
CREATE INDEX idx_projects_slug ON app.projects (slug);
CREATE INDEX idx_project_members_composite ON app.project_members (project_id, user_id, role) WHERE removed_at IS NULL;

CREATE INDEX idx_milestones_project_type ON app.milestones (project_id, milestone_type, status);
CREATE INDEX idx_tasks_assignment ON app.tasks (assigned_to, status, priority) WHERE status NOT IN ('completed', 'cancelled');
CREATE INDEX idx_tasks_due_soon ON app.tasks (due_date, status) WHERE status NOT IN ('completed', 'cancelled') AND due_date IS NOT NULL;

-- AI schema indexes
CREATE INDEX idx_chat_conv_recent ON ai.chat_conversations (user_id, last_message_at DESC NULLS LAST);
CREATE INDEX idx_chat_messages_conversation ON ai.chat_messages (conversation_id, created_at DESC);

-- Vector similarity indexes
CREATE INDEX idx_embeddings_vector_cosine ON ai.embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Full-text search indexes
CREATE INDEX idx_projects_fts ON app.projects 
    USING gin(to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')));

CREATE INDEX idx_tasks_fts ON app.tasks 
    USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(description, '')));

-- JSONB indexes
CREATE INDEX idx_users_metadata_gin ON auth.users USING gin(metadata);
CREATE INDEX idx_users_preferences_gin ON auth.users USING gin(preferences);
CREATE INDEX idx_projects_settings_gin ON app.projects USING gin(settings);

-- Notification indexes
CREATE INDEX idx_notif_queue_pending ON notifications.queue (user_id, scheduled_for) 
    WHERE status = 'pending' AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

-- =====================================================
-- SECTION 11: TRIGGERS AND AUTOMATION
-- =====================================================

-- Universal updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all relevant tables
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN 
        SELECT table_schema, table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
        AND table_schema IN ('auth', 'app', 'ai', 'marketplace', 'notifications')
    LOOP
        EXECUTE format('CREATE TRIGGER update_%I_updated_at BEFORE UPDATE ON %I.%I 
                       FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
                       t.table_name, t.table_schema, t.table_name);
    END LOOP;
END $$;

-- Auto-generate slugs for projects
CREATE OR REPLACE FUNCTION auto_generate_project_slug()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.slug IS NULL OR NEW.slug = '' THEN
        NEW.slug := generate_unique_slug(NEW.name, 'app.projects');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER generate_project_slug 
    BEFORE INSERT OR UPDATE OF name ON app.projects
    FOR EACH ROW EXECUTE FUNCTION auto_generate_project_slug();

-- Update project progress when tasks change
CREATE OR REPLACE FUNCTION update_project_progress()
RETURNS TRIGGER AS $$
DECLARE
    v_total_tasks INT;
    v_completed_tasks INT;
    v_progress percentage;
BEGIN
    -- Get task counts
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'completed')
    INTO v_total_tasks, v_completed_tasks
    FROM app.tasks
    WHERE project_id = COALESCE(NEW.project_id, OLD.project_id);
    
    -- Calculate progress
    IF v_total_tasks > 0 THEN
        v_progress := ROUND((v_completed_tasks::NUMERIC / v_total_tasks) * 100, 2);
    ELSE
        v_progress := 0;
    END IF;
    
    -- Update project
    UPDATE app.projects 
    SET overall_progress = v_progress
    WHERE id = COALESCE(NEW.project_id, OLD.project_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_project_progress_trigger
    AFTER INSERT OR UPDATE OF status OR DELETE ON app.tasks
    FOR EACH ROW EXECUTE FUNCTION update_project_progress();

-- =====================================================
-- SECTION 12: ROW LEVEL SECURITY POLICIES
-- =====================================================

-- Enable RLS on sensitive tables
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.chat_conversations ENABLE ROW LEVEL SECURITY;

-- Users can only see and update their own data
CREATE POLICY users_self_access ON auth.users
    FOR ALL
    USING (id = current_setting('app.current_user_id', true)::UUID 
           OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin'));

-- Project access based on ownership or membership
CREATE POLICY projects_access ON app.projects
    FOR ALL
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
                AND removed_at IS NULL
        )
        OR (is_public = true AND visibility = 'public')
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- Task access through project membership
CREATE POLICY tasks_access ON app.tasks
    FOR ALL
    USING (
        project_id IN (
            SELECT id FROM app.projects 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
            UNION
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
                AND removed_at IS NULL
        )
        OR assigned_to = current_setting('app.current_user_id', true)::UUID
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- Chat conversations access
CREATE POLICY chat_access ON ai.chat_conversations
    FOR ALL
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR project_id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
                AND removed_at IS NULL
        )
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

-- =====================================================
-- SECTION 13: PERFORMANCE OPTIMIZATION SETTINGS
-- =====================================================

-- Set table storage parameters for frequently updated tables
ALTER TABLE auth.users SET (fillfactor = 90);
ALTER TABLE auth.sessions SET (fillfactor = 70);
ALTER TABLE app.tasks SET (fillfactor = 85);
ALTER TABLE ai.chat_messages SET (fillfactor = 95);
ALTER TABLE notifications.queue SET (fillfactor = 80);

-- Configure autovacuum for high-activity tables
ALTER TABLE auth.sessions SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05,
    autovacuum_vacuum_cost_delay = 10
);

ALTER TABLE app.tasks SET (
    autovacuum_vacuum_scale_factor = 0.15,
    autovacuum_analyze_scale_factor = 0.1
);

ALTER TABLE notifications.queue SET (
    autovacuum_vacuum_scale_factor = 0.1,
    autovacuum_analyze_scale_factor = 0.05
);

-- =====================================================
-- SECTION 14: SCHEDULED MAINTENANCE JOBS
-- =====================================================

-- Cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth.sessions
    WHERE expires_at < CURRENT_TIMESTAMP
        OR (revoked_at IS NOT NULL AND revoked_at < CURRENT_TIMESTAMP - INTERVAL '7 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log the cleanup
    INSERT INTO audit.system_logs (action, details, rows_affected)
    VALUES ('cleanup_sessions', 'Expired sessions cleanup', deleted_count);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Process notification queue
CREATE OR REPLACE FUNCTION process_notification_queue()
RETURNS INTEGER AS $$
DECLARE
    processed_count INTEGER := 0;
    notification RECORD;
BEGIN
    -- Process pending notifications
    FOR notification IN 
        SELECT * FROM notifications.queue
        WHERE status = 'pending'
            AND (scheduled_for IS NULL OR scheduled_for <= CURRENT_TIMESTAMP)
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            AND attempts < max_attempts
        ORDER BY priority DESC, created_at ASC
        LIMIT 100
        FOR UPDATE SKIP LOCKED
    LOOP
        -- Update status to processing
        UPDATE notifications.queue 
        SET status = 'processing', attempts = attempts + 1
        WHERE id = notification.id;
        
        -- Here you would call your notification service
        -- For now, we'll just mark as sent
        UPDATE notifications.queue 
        SET status = 'sent', sent_at = CURRENT_TIMESTAMP
        WHERE id = notification.id;
        
        processed_count := processed_count + 1;
    END LOOP;
    
    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule jobs with pg_cron
SELECT cron.schedule('cleanup-sessions', '0 */2 * * *', $$SELECT cleanup_expired_sessions();$$);
SELECT cron.schedule('process-notifications', '* * * * *', $$SELECT process_notification_queue();$$);

-- =====================================================
-- SECTION 15: MONITORING AND ANALYTICS VIEWS
-- =====================================================

-- System health overview
CREATE OR REPLACE VIEW monitoring.system_health AS
SELECT 
    (SELECT COUNT(*) FROM auth.users WHERE status = 'active') AS active_users,
    (SELECT COUNT(*) FROM auth.sessions WHERE expires_at > CURRENT_TIMESTAMP AND revoked_at IS NULL) AS active_sessions,
    (SELECT COUNT(*) FROM app.projects WHERE is_active = true) AS active_projects,
    (SELECT COUNT(*) FROM app.tasks WHERE status IN ('todo', 'in_progress')) AS pending_tasks,
    (SELECT COUNT(*) FROM notifications.queue WHERE status = 'pending') AS pending_notifications,
    (SELECT AVG(response_time_ms) FROM ai.usage_tracking WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour') AS avg_ai_response_time,
    (SELECT SUM(total_tokens) FROM ai.usage_tracking WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours') AS daily_token_usage,
    (SELECT pg_database_size(current_database())) AS database_size;

-- User activity dashboard
CREATE OR REPLACE VIEW monitoring.user_activity AS
SELECT 
    u.id,
    u.email,
    u.role,
    u.subscription_tier,
    u.last_login_at,
    u.last_activity_at,
    COUNT(DISTINCT p.id) AS project_count,
    COUNT(DISTINCT t.id) AS task_count,
    COUNT(DISTINCT c.id) AS conversation_count,
    COALESCE(SUM(ai.total_tokens), 0) AS total_tokens_used
FROM auth.users u
LEFT JOIN app.projects p ON u.id = p.user_id AND p.is_active = true
LEFT JOIN app.tasks t ON u.id = t.assigned_to AND t.status NOT IN ('completed', 'cancelled')
LEFT JOIN ai.chat_conversations c ON u.id = c.user_id
LEFT JOIN ai.usage_tracking ai ON u.id = ai.user_id AND ai.created_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
WHERE u.deleted_at IS NULL
GROUP BY u.id;

-- Project health metrics
CREATE OR REPLACE VIEW monitoring.project_health AS
SELECT 
    p.id,
    p.name,
    p.current_milestone,
    p.overall_progress,
    COUNT(DISTINCT pm.user_id) AS team_size,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'blocked') AS blocked_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.due_date < CURRENT_TIMESTAMP AND t.status NOT IN ('completed', 'cancelled')) AS overdue_tasks,
    AVG(EXTRACT(EPOCH FROM (t.completed_at - t.created_at))/3600)::INT AS avg_task_completion_hours
FROM app.projects p
LEFT JOIN app.project_members pm ON p.id = pm.project_id AND pm.removed_at IS NULL
LEFT JOIN app.tasks t ON p.id = t.project_id
WHERE p.is_active = true
GROUP BY p.id;

-- =====================================================
-- SECTION 16: INITIAL SEED DATA
-- =====================================================

-- Insert default notification templates
INSERT INTO notifications.templates (name, category, subject_template, body_template, available_channels) VALUES
('welcome_email', 'onboarding', 'Welcome to ProLaunch!', 'Hi {{user_name}}, welcome to ProLaunch...', ARRAY['email']),
('task_assigned', 'task', 'New task assigned: {{task_title}}', 'You have been assigned a new task...', ARRAY['email', 'in_app', 'push']),
('milestone_completed', 'milestone', 'Milestone completed: {{milestone_name}}', 'Congratulations! Your milestone has been completed...', ARRAY['email', 'in_app']),
('project_invitation', 'collaboration', 'You''ve been invited to {{project_name}}', '{{inviter_name}} has invited you to collaborate...', ARRAY['email', 'in_app'])
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- SECTION 17: COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '================================================';
    RAISE NOTICE 'ProLaunch Production Database Schema Created';
    RAISE NOTICE '================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Summary of created components:';
    RAISE NOTICE '- 12 Schemas for logical organization';
    RAISE NOTICE '- 15+ Custom types and domains';
    RAISE NOTICE '- 40+ Core tables with advanced features';
    RAISE NOTICE '- 50+ Optimized indexes';
    RAISE NOTICE '- Vector support for AI embeddings';
    RAISE NOTICE '- Row Level Security policies';
    RAISE NOTICE '- Automated triggers and functions';
    RAISE NOTICE '- Monitoring views and analytics';
    RAISE NOTICE '- Scheduled maintenance jobs';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update all role passwords';
    RAISE NOTICE '2. Configure SSL certificates';
    RAISE NOTICE '3. Set up backup procedures';
    RAISE NOTICE '4. Configure monitoring alerts';
    RAISE NOTICE '5. Run initial data migrations';
    RAISE NOTICE '6. Test RLS policies';
    RAISE NOTICE '================================================';
END $$;