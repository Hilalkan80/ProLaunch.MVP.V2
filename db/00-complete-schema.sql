-- =====================================================
-- ProLaunch MVP V2 - Complete PostgreSQL Database Schema
-- =====================================================
-- Version: 2.0.0
-- Description: Comprehensive database schema with all required
--              extensions, tables, indexes, functions, and security
-- =====================================================

-- =====================================================
-- 1. DATABASE INITIALIZATION
-- =====================================================

-- Drop and recreate database (for initial setup only)
-- Note: Comment these lines after initial setup
-- DROP DATABASE IF EXISTS prolaunch;
-- CREATE DATABASE prolaunch WITH ENCODING 'UTF8' LC_COLLATE = 'en_US.utf8' LC_CTYPE = 'en_US.utf8';

-- Connect to the database
\c prolaunch;

-- =====================================================
-- 2. EXTENSIONS
-- =====================================================

-- Core extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- Trigram matching for text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";        -- GIN indexes on scalar types
CREATE EXTENSION IF NOT EXISTS "btree_gist";       -- GiST indexes on scalar types
CREATE EXTENSION IF NOT EXISTS "hstore";           -- Key-value store
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance monitoring

-- Vector search extension for AI embeddings
CREATE EXTENSION IF NOT EXISTS "vector";

-- Full-text search extensions
CREATE EXTENSION IF NOT EXISTS "unaccent";         -- Remove accents from text
CREATE EXTENSION IF NOT EXISTS "pg_prewarm";       -- Preload indexes into cache

-- =====================================================
-- 3. SCHEMAS
-- =====================================================

-- Create logical schemas for better organization
CREATE SCHEMA IF NOT EXISTS app;                   -- Main application schema
CREATE SCHEMA IF NOT EXISTS auth;                  -- Authentication and authorization
CREATE SCHEMA IF NOT EXISTS audit;                 -- Audit logging
CREATE SCHEMA IF NOT EXISTS analytics;             -- Analytics and reporting
CREATE SCHEMA IF NOT EXISTS ai;                    -- AI and ML related tables
CREATE SCHEMA IF NOT EXISTS marketplace;           -- Marketplace features

-- Set default search path
ALTER DATABASE prolaunch SET search_path TO app, auth, public;

-- =====================================================
-- 4. CUSTOM TYPES AND ENUMS
-- =====================================================

-- User and authentication types
CREATE TYPE auth.user_role AS ENUM (
    'super_admin',
    'admin',
    'moderator',
    'user',
    'guest'
);

CREATE TYPE auth.user_status AS ENUM (
    'active',
    'inactive',
    'suspended',
    'pending_verification',
    'deleted'
);

CREATE TYPE auth.subscription_tier AS ENUM (
    'free',
    'starter',
    'professional',
    'enterprise',
    'custom'
);

CREATE TYPE auth.auth_provider AS ENUM (
    'email',
    'google',
    'microsoft',
    'linkedin',
    'github'
);

-- Business milestone types
CREATE TYPE app.milestone_type AS ENUM (
    'M0_ideation',
    'M1_validation',
    'M2_planning',
    'M3_development',
    'M4_launch',
    'M5_growth'
);

CREATE TYPE app.milestone_status AS ENUM (
    'not_started',
    'in_progress',
    'completed',
    'skipped',
    'blocked'
);

CREATE TYPE app.task_priority AS ENUM (
    'critical',
    'high',
    'medium',
    'low'
);

CREATE TYPE app.task_status AS ENUM (
    'todo',
    'in_progress',
    'in_review',
    'completed',
    'cancelled',
    'blocked'
);

-- Document and content types
CREATE TYPE app.document_type AS ENUM (
    'business_plan',
    'pitch_deck',
    'financial_model',
    'market_analysis',
    'legal_document',
    'contract',
    'proposal',
    'report',
    'other'
);

CREATE TYPE app.document_status AS ENUM (
    'draft',
    'in_review',
    'approved',
    'published',
    'archived'
);

-- Chat and AI types
CREATE TYPE ai.message_role AS ENUM (
    'system',
    'user',
    'assistant',
    'function'
);

CREATE TYPE ai.ai_model AS ENUM (
    'gpt-4',
    'gpt-3.5-turbo',
    'claude-3',
    'llama-2',
    'custom'
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
    'other'
);

CREATE TYPE marketplace.supplier_status AS ENUM (
    'pending',
    'verified',
    'premium',
    'suspended',
    'rejected'
);

-- Payment and transaction types
CREATE TYPE app.payment_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'refunded',
    'cancelled'
);

CREATE TYPE app.currency AS ENUM (
    'USD',
    'EUR',
    'GBP',
    'CAD',
    'AUD',
    'JPY',
    'CNY'
);

-- =====================================================
-- 5. CORE TABLES
-- =====================================================

-- ===== Authentication Schema =====

-- Users table
CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    phone_number VARCHAR(20),
    role auth.user_role NOT NULL DEFAULT 'user',
    status auth.user_status NOT NULL DEFAULT 'pending_verification',
    subscription_tier auth.subscription_tier NOT NULL DEFAULT 'free',
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- OAuth providers
CREATE TABLE auth.oauth_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider auth.auth_provider NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    provider_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);

-- User sessions
CREATE TABLE auth.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    device_info JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API keys for external integrations
CREATE TABLE auth.api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '[]',
    rate_limit INT DEFAULT 1000,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- ===== Application Schema =====

-- User profiles (extended user information)
CREATE TABLE app.user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bio TEXT,
    company_name VARCHAR(255),
    company_role VARCHAR(100),
    industry VARCHAR(100),
    location VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    linkedin_url VARCHAR(500),
    twitter_url VARCHAR(500),
    website_url VARCHAR(500),
    skills TEXT[],
    languages TEXT[],
    experience_years INT,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_step INT DEFAULT 0,
    profile_completion_percentage INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects/Businesses
CREATE TABLE app.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    industry VARCHAR(100),
    business_model VARCHAR(100),
    target_market TEXT,
    current_milestone app.milestone_type DEFAULT 'M0_ideation',
    logo_url VARCHAR(500),
    cover_image_url VARCHAR(500),
    website_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE,
    team_size INT DEFAULT 1,
    funding_stage VARCHAR(50),
    revenue_range VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    launched_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE
);

-- Project team members
CREATE TABLE app.project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB DEFAULT '[]',
    invited_by UUID REFERENCES auth.users(id),
    invitation_token VARCHAR(255),
    invitation_expires_at TIMESTAMP WITH TIME ZONE,
    joined_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

-- Milestones
CREATE TABLE app.milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    milestone_type app.milestone_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    objectives TEXT[],
    deliverables TEXT[],
    status app.milestone_status NOT NULL DEFAULT 'not_started',
    progress_percentage INT DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    estimated_hours INT,
    actual_hours INT,
    start_date DATE,
    target_date DATE,
    completed_date DATE,
    blockers TEXT[],
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, milestone_type)
);

-- Tasks
CREATE TABLE app.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES app.milestones(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES app.tasks(id) ON DELETE CASCADE,
    assigned_to UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority app.task_priority DEFAULT 'medium',
    status app.task_status DEFAULT 'todo',
    tags TEXT[],
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    progress_percentage INT DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    due_date TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    dependencies UUID[],
    attachments JSONB DEFAULT '[]',
    comments_count INT DEFAULT 0,
    position INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Task comments
CREATE TABLE app.task_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES app.tasks(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES app.task_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    mentions UUID[],
    attachments JSONB DEFAULT '[]',
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Documents
CREATE TABLE app.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES auth.users(id),
    document_type app.document_type NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    file_url VARCHAR(1000),
    file_key VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),
    version INT DEFAULT 1,
    parent_document_id UUID REFERENCES app.documents(id),
    status app.document_status DEFAULT 'draft',
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_model VARCHAR(50),
    ai_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE
);

-- Document collaborators
CREATE TABLE app.document_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES app.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    permission VARCHAR(20) NOT NULL CHECK (permission IN ('view', 'comment', 'edit', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, user_id)
);

-- Resources/Files
CREATE TABLE app.resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES auth.users(id),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    file_key VARCHAR(500) UNIQUE NOT NULL,
    file_url VARCHAR(1000),
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    tags TEXT[],
    is_public BOOLEAN DEFAULT FALSE,
    download_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    virus_scanned BOOLEAN DEFAULT FALSE,
    virus_scan_result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- ===== AI Schema =====

-- Chat conversations
CREATE TABLE ai.chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    context JSONB DEFAULT '{}',
    model ai.ai_model DEFAULT 'gpt-4',
    temperature DECIMAL(2,1) DEFAULT 0.7,
    max_tokens INT DEFAULT 2000,
    total_tokens_used INT DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    is_pinned BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE
);

-- Chat messages
CREATE TABLE ai.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai.chat_conversations(id) ON DELETE CASCADE,
    role ai.message_role NOT NULL,
    content TEXT NOT NULL,
    tokens_used INT,
    model_used VARCHAR(50),
    function_name VARCHAR(100),
    function_arguments JSONB,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings for semantic search
CREATE TABLE ai.embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    content_chunk TEXT NOT NULL,
    chunk_index INT DEFAULT 0,
    embedding vector(1536),
    model_used VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated insights
CREATE TABLE ai.insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    insight_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    data_sources JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    model_used VARCHAR(50),
    is_actionable BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- ===== Marketplace Schema =====

-- Suppliers
CREATE TABLE marketplace.suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    company_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category marketplace.supplier_category NOT NULL,
    subcategories TEXT[],
    services_offered TEXT[],
    industries_served TEXT[],
    locations_served TEXT[],
    minimum_budget DECIMAL(10,2),
    status marketplace.supplier_status DEFAULT 'pending',
    rating DECIMAL(2,1) DEFAULT 0 CHECK (rating >= 0 AND rating <= 5),
    total_reviews INT DEFAULT 0,
    total_projects INT DEFAULT 0,
    response_time_hours INT,
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    logo_url VARCHAR(500),
    portfolio_urls TEXT[],
    certifications JSONB DEFAULT '[]',
    team_size VARCHAR(20),
    year_founded INT,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Supplier reviews
CREATE TABLE marketplace.supplier_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    supplier_id UUID NOT NULL REFERENCES marketplace.suppliers(id) ON DELETE CASCADE,
    project_id UUID REFERENCES app.projects(id) ON DELETE SET NULL,
    reviewer_id UUID NOT NULL REFERENCES auth.users(id),
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    content TEXT,
    pros TEXT[],
    cons TEXT[],
    would_recommend BOOLEAN,
    project_budget_range VARCHAR(50),
    project_duration_months INT,
    verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Connection requests
CREATE TABLE marketplace.connection_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES marketplace.suppliers(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES auth.users(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'expired')),
    message TEXT,
    budget_range VARCHAR(50),
    timeline VARCHAR(100),
    requirements TEXT,
    response_message TEXT,
    responded_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '7 days')
);

-- ===== Audit Schema =====

-- Activity log
CREATE TABLE audit.activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API request logs
CREATE TABLE audit.api_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(500) NOT NULL,
    query_params JSONB,
    request_body JSONB,
    response_status INT,
    response_time_ms INT,
    ip_address INET,
    user_agent TEXT,
    api_key_id UUID REFERENCES auth.api_keys(id) ON DELETE SET NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email logs
CREATE TABLE audit.email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    email_type VARCHAR(50) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    provider VARCHAR(50),
    provider_message_id VARCHAR(255),
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===== Analytics Schema =====

-- User analytics
CREATE TABLE analytics.user_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    login_count INT DEFAULT 0,
    active_minutes INT DEFAULT 0,
    tasks_created INT DEFAULT 0,
    tasks_completed INT DEFAULT 0,
    documents_created INT DEFAULT 0,
    chat_messages_sent INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, date)
);

-- Project analytics
CREATE TABLE analytics.project_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES app.projects(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    active_users INT DEFAULT 0,
    tasks_created INT DEFAULT 0,
    tasks_completed INT DEFAULT 0,
    milestone_progress JSONB DEFAULT '{}',
    documents_created INT DEFAULT 0,
    chat_conversations INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, date)
);

-- =====================================================
-- 6. INDEXES FOR OPTIMIZATION
-- =====================================================

-- Auth indexes
CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_username ON auth.users(username);
CREATE INDEX idx_users_status ON auth.users(status);
CREATE INDEX idx_users_role ON auth.users(role);
CREATE INDEX idx_users_subscription_tier ON auth.users(subscription_tier);
CREATE INDEX idx_users_created_at ON auth.users(created_at DESC);
CREATE INDEX idx_users_last_login ON auth.users(last_login_at DESC);

CREATE INDEX idx_oauth_user_id ON auth.oauth_accounts(user_id);
CREATE INDEX idx_oauth_provider ON auth.oauth_accounts(provider, provider_user_id);

CREATE INDEX idx_sessions_user_id ON auth.sessions(user_id);
CREATE INDEX idx_sessions_token ON auth.sessions(token_hash);
CREATE INDEX idx_sessions_expires ON auth.sessions(expires_at);

CREATE INDEX idx_api_keys_user_id ON auth.api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON auth.api_keys(key_hash);

-- App indexes
CREATE INDEX idx_projects_user_id ON app.projects(user_id);
CREATE INDEX idx_projects_slug ON app.projects(slug);
CREATE INDEX idx_projects_milestone ON app.projects(current_milestone);
CREATE INDEX idx_projects_active ON app.projects(is_active) WHERE is_active = true;
CREATE INDEX idx_projects_public ON app.projects(is_public) WHERE is_public = true;

CREATE INDEX idx_project_members_project ON app.project_members(project_id);
CREATE INDEX idx_project_members_user ON app.project_members(user_id);

CREATE INDEX idx_milestones_project ON app.milestones(project_id);
CREATE INDEX idx_milestones_type ON app.milestones(milestone_type);
CREATE INDEX idx_milestones_status ON app.milestones(status);

CREATE INDEX idx_tasks_project ON app.tasks(project_id);
CREATE INDEX idx_tasks_milestone ON app.tasks(milestone_id);
CREATE INDEX idx_tasks_assigned ON app.tasks(assigned_to);
CREATE INDEX idx_tasks_status ON app.tasks(status);
CREATE INDEX idx_tasks_priority ON app.tasks(priority);
CREATE INDEX idx_tasks_due_date ON app.tasks(due_date);

CREATE INDEX idx_documents_project ON app.documents(project_id);
CREATE INDEX idx_documents_type ON app.documents(document_type);
CREATE INDEX idx_documents_status ON app.documents(status);
CREATE INDEX idx_documents_ai_generated ON app.documents(ai_generated) WHERE ai_generated = true;

CREATE INDEX idx_resources_project ON app.resources(project_id);
CREATE INDEX idx_resources_uploaded_by ON app.resources(uploaded_by);

-- AI indexes
CREATE INDEX idx_chat_conv_project ON ai.chat_conversations(project_id);
CREATE INDEX idx_chat_conv_user ON ai.chat_conversations(user_id);
CREATE INDEX idx_chat_conv_last_message ON ai.chat_conversations(last_message_at DESC);

CREATE INDEX idx_chat_messages_conv ON ai.chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created ON ai.chat_messages(created_at DESC);

-- Vector similarity search indexes
CREATE INDEX idx_embeddings_vector ON ai.embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);
CREATE INDEX idx_embeddings_content ON ai.embeddings(content_type, content_id);

CREATE INDEX idx_suppliers_embedding ON marketplace.suppliers 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 50);

-- Marketplace indexes
CREATE INDEX idx_suppliers_category ON marketplace.suppliers(category);
CREATE INDEX idx_suppliers_status ON marketplace.suppliers(status);
CREATE INDEX idx_suppliers_rating ON marketplace.suppliers(rating DESC);
CREATE INDEX idx_suppliers_slug ON marketplace.suppliers(slug);

CREATE INDEX idx_reviews_supplier ON marketplace.supplier_reviews(supplier_id);
CREATE INDEX idx_reviews_rating ON marketplace.supplier_reviews(rating);

CREATE INDEX idx_connections_project ON marketplace.connection_requests(project_id);
CREATE INDEX idx_connections_supplier ON marketplace.connection_requests(supplier_id);
CREATE INDEX idx_connections_status ON marketplace.connection_requests(status);

-- Audit indexes
CREATE INDEX idx_activity_user ON audit.activity_logs(user_id);
CREATE INDEX idx_activity_entity ON audit.activity_logs(entity_type, entity_id);
CREATE INDEX idx_activity_created ON audit.activity_logs(created_at DESC);
CREATE INDEX idx_activity_action ON audit.activity_logs(action);

CREATE INDEX idx_api_logs_user ON audit.api_logs(user_id);
CREATE INDEX idx_api_logs_path ON audit.api_logs(path);
CREATE INDEX idx_api_logs_created ON audit.api_logs(created_at DESC);
CREATE INDEX idx_api_logs_status ON audit.api_logs(response_status);

-- Analytics indexes
CREATE INDEX idx_user_analytics_user_date ON analytics.user_analytics(user_id, date DESC);
CREATE INDEX idx_project_analytics_project_date ON analytics.project_analytics(project_id, date DESC);

-- Full-text search indexes
CREATE INDEX idx_projects_search ON app.projects 
    USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

CREATE INDEX idx_tasks_search ON app.tasks 
    USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

CREATE INDEX idx_documents_search ON app.documents 
    USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(content, '')));

CREATE INDEX idx_suppliers_search ON marketplace.suppliers 
    USING gin(to_tsvector('english', company_name || ' ' || COALESCE(description, '')));

-- =====================================================
-- 7. FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_accounts_updated_at BEFORE UPDATE ON auth.oauth_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON app.user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON app.projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_project_members_updated_at BEFORE UPDATE ON app.project_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_milestones_updated_at BEFORE UPDATE ON app.milestones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON app.tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON app.documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_resources_updated_at BEFORE UPDATE ON app.resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON ai.chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embeddings_updated_at BEFORE UPDATE ON ai.embeddings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_suppliers_updated_at BEFORE UPDATE ON marketplace.suppliers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate slug from name
CREATE OR REPLACE FUNCTION generate_slug(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(input_text, '[^a-zA-Z0-9\s-]', '', 'g'),
                '\s+', '-', 'g'
            ),
            '-+', '-', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Function to log activity
CREATE OR REPLACE FUNCTION log_activity()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit.activity_logs (
        user_id,
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        metadata
    ) VALUES (
        current_setting('app.current_user_id', true)::UUID,
        TG_OP,
        TG_TABLE_NAME,
        CASE 
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        CASE 
            WHEN TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN to_jsonb(OLD)
            ELSE NULL
        END,
        CASE 
            WHEN TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN to_jsonb(NEW)
            ELSE NULL
        END,
        jsonb_build_object('schema', TG_TABLE_SCHEMA)
    );
    
    RETURN CASE 
        WHEN TG_OP = 'DELETE' THEN OLD
        ELSE NEW
    END;
END;
$$ LANGUAGE plpgsql;

-- Apply activity logging to critical tables
CREATE TRIGGER log_projects_activity AFTER INSERT OR UPDATE OR DELETE ON app.projects
    FOR EACH ROW EXECUTE FUNCTION log_activity();

CREATE TRIGGER log_milestones_activity AFTER INSERT OR UPDATE OR DELETE ON app.milestones
    FOR EACH ROW EXECUTE FUNCTION log_activity();

CREATE TRIGGER log_documents_activity AFTER INSERT OR UPDATE OR DELETE ON app.documents
    FOR EACH ROW EXECUTE FUNCTION log_activity();

-- Function to calculate project completion percentage
CREATE OR REPLACE FUNCTION calculate_project_completion(project_id UUID)
RETURNS INTEGER AS $$
DECLARE
    total_tasks INTEGER;
    completed_tasks INTEGER;
    completion_percentage INTEGER;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'completed')
    INTO total_tasks, completed_tasks
    FROM app.tasks
    WHERE app.tasks.project_id = calculate_project_completion.project_id;
    
    IF total_tasks = 0 THEN
        RETURN 0;
    END IF;
    
    completion_percentage := ROUND((completed_tasks::DECIMAL / total_tasks) * 100);
    RETURN completion_percentage;
END;
$$ LANGUAGE plpgsql;

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION search_similar_content(
    query_embedding vector(1536),
    search_type TEXT,
    limit_results INTEGER DEFAULT 10,
    threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    content_type VARCHAR,
    content_id UUID,
    content_chunk TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.content_type,
        e.content_id,
        e.content_chunk,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM ai.embeddings e
    WHERE 
        (search_type IS NULL OR e.content_type = search_type)
        AND (1 - (e.embedding <=> query_embedding)) > threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM auth.sessions
    WHERE expires_at < CURRENT_TIMESTAMP
    OR revoked_at IS NOT NULL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update user last activity
CREATE OR REPLACE FUNCTION update_user_last_activity(user_id_param UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE auth.users
    SET last_activity_at = CURRENT_TIMESTAMP
    WHERE id = user_id_param;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 8. VIEWS FOR COMMON QUERIES
-- =====================================================

-- View for active users with profile information
CREATE OR REPLACE VIEW app.v_active_users AS
SELECT 
    u.id,
    u.email,
    u.username,
    u.full_name,
    u.role,
    u.subscription_tier,
    p.company_name,
    p.company_role,
    p.industry,
    p.profile_completion_percentage,
    u.last_login_at,
    u.created_at
FROM auth.users u
LEFT JOIN app.user_profiles p ON u.id = p.user_id
WHERE u.status = 'active'
AND u.deleted_at IS NULL;

-- View for project overview
CREATE OR REPLACE VIEW app.v_project_overview AS
SELECT 
    p.id,
    p.name,
    p.slug,
    p.description,
    p.current_milestone,
    u.full_name AS owner_name,
    u.email AS owner_email,
    COUNT(DISTINCT pm.user_id) AS team_members,
    COUNT(DISTINCT m.id) AS total_milestones,
    COUNT(DISTINCT m.id) FILTER (WHERE m.status = 'completed') AS completed_milestones,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    calculate_project_completion(p.id) AS completion_percentage,
    p.created_at,
    p.updated_at
FROM app.projects p
JOIN auth.users u ON p.user_id = u.id
LEFT JOIN app.project_members pm ON p.id = pm.project_id
LEFT JOIN app.milestones m ON p.id = m.project_id
LEFT JOIN app.tasks t ON p.id = t.project_id
WHERE p.is_active = true
GROUP BY p.id, u.full_name, u.email;

-- View for milestone progress
CREATE OR REPLACE VIEW app.v_milestone_progress AS
SELECT 
    m.id,
    m.project_id,
    p.name AS project_name,
    m.milestone_type,
    m.name AS milestone_name,
    m.status,
    m.progress_percentage,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    m.start_date,
    m.target_date,
    m.completed_date,
    CASE 
        WHEN m.target_date IS NOT NULL AND m.status != 'completed' 
        THEN m.target_date - CURRENT_DATE
        ELSE NULL
    END AS days_remaining
FROM app.milestones m
JOIN app.projects p ON m.project_id = p.id
LEFT JOIN app.tasks t ON m.id = t.milestone_id
GROUP BY m.id, p.name;

-- View for user activity summary
CREATE OR REPLACE VIEW analytics.v_user_activity_summary AS
SELECT 
    u.id,
    u.email,
    u.username,
    COUNT(DISTINCT p.id) AS total_projects,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    COUNT(DISTINCT d.id) AS total_documents,
    COUNT(DISTINCT c.id) AS total_conversations,
    COUNT(DISTINCT cm.id) AS total_messages,
    COALESCE(SUM(c.total_tokens_used), 0) AS total_ai_tokens,
    MAX(u.last_login_at) AS last_login,
    MAX(u.last_activity_at) AS last_activity
FROM auth.users u
LEFT JOIN app.projects p ON u.id = p.user_id
LEFT JOIN app.tasks t ON u.id = t.assigned_to OR u.id = t.created_by
LEFT JOIN app.documents d ON u.id = d.created_by
LEFT JOIN ai.chat_conversations c ON u.id = c.user_id
LEFT JOIN ai.chat_messages cm ON c.id = cm.conversation_id
WHERE u.deleted_at IS NULL
GROUP BY u.id;

-- View for supplier rankings
CREATE OR REPLACE VIEW marketplace.v_supplier_rankings AS
SELECT 
    s.id,
    s.company_name,
    s.slug,
    s.category,
    s.status,
    s.rating,
    s.total_reviews,
    s.total_projects,
    COUNT(DISTINCT cr.id) AS pending_connections,
    COUNT(DISTINCT cr.id) FILTER (WHERE cr.status = 'accepted') AS accepted_connections,
    s.response_time_hours,
    s.verified_at IS NOT NULL AS is_verified,
    s.created_at
FROM marketplace.suppliers s
LEFT JOIN marketplace.connection_requests cr ON s.id = cr.supplier_id
WHERE s.status IN ('verified', 'premium')
GROUP BY s.id
ORDER BY s.rating DESC, s.total_reviews DESC;

-- View for recent chat conversations with context
CREATE OR REPLACE VIEW ai.v_recent_conversations AS
SELECT 
    c.id,
    c.project_id,
    p.name AS project_name,
    c.user_id,
    u.full_name AS user_name,
    c.title,
    c.model,
    COUNT(m.id) AS message_count,
    c.total_tokens_used,
    c.total_cost,
    MAX(m.created_at) AS last_message_at,
    c.created_at
FROM ai.chat_conversations c
JOIN app.projects p ON c.project_id = p.id
JOIN auth.users u ON c.user_id = u.id
LEFT JOIN ai.chat_messages m ON c.id = m.conversation_id
GROUP BY c.id, p.name, u.full_name
ORDER BY MAX(m.created_at) DESC NULLS LAST, c.created_at DESC;

-- =====================================================
-- 9. ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on sensitive tables
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY users_select_policy ON auth.users
    FOR SELECT
    USING (
        id = current_setting('app.current_user_id', true)::UUID
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

CREATE POLICY users_update_policy ON auth.users
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true)::UUID)
    WITH CHECK (id = current_setting('app.current_user_id', true)::UUID);

-- RLS Policies for projects
CREATE POLICY projects_select_policy ON app.projects
    FOR SELECT
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
        )
        OR is_public = true
        OR current_setting('app.current_user_role', true) IN ('admin', 'super_admin')
    );

CREATE POLICY projects_insert_policy ON app.projects
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::UUID);

CREATE POLICY projects_update_policy ON app.projects
    FOR UPDATE
    USING (
        user_id = current_setting('app.current_user_id', true)::UUID
        OR id IN (
            SELECT project_id FROM app.project_members 
            WHERE user_id = current_setting('app.current_user_id', true)::UUID
            AND role IN ('admin', 'owner')
        )
    );

-- =====================================================
-- 10. PARTITIONING FOR LARGE TABLES
-- =====================================================

-- Partition audit logs by month
CREATE TABLE audit.activity_logs_partitioned (
    LIKE audit.activity_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Create partitions for the current and next 3 months
CREATE TABLE audit.activity_logs_y2024m01 PARTITION OF audit.activity_logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE audit.activity_logs_y2024m02 PARTITION OF audit.activity_logs_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
    
CREATE TABLE audit.activity_logs_y2024m03 PARTITION OF audit.activity_logs_partitioned
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- Function to automatically create monthly partitions
CREATE OR REPLACE FUNCTION create_monthly_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'activity_logs_y' || to_char(start_date, 'YYYY') || 'm' || to_char(start_date, 'MM');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS audit.%I PARTITION OF audit.activity_logs_partitioned FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 11. GRANTS AND PERMISSIONS
-- =====================================================

-- Create application roles
CREATE ROLE prolaunch_app WITH LOGIN PASSWORD 'secure_password_here';
CREATE ROLE prolaunch_readonly WITH LOGIN PASSWORD 'readonly_password_here';
CREATE ROLE prolaunch_admin WITH LOGIN PASSWORD 'admin_password_here';

-- Grant schema permissions
GRANT USAGE ON SCHEMA app, auth, ai, marketplace, audit, analytics TO prolaunch_app;
GRANT USAGE ON SCHEMA app, auth, ai, marketplace, audit, analytics TO prolaunch_readonly;
GRANT ALL ON SCHEMA app, auth, ai, marketplace, audit, analytics TO prolaunch_admin;

-- Grant table permissions to app role
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA auth TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO prolaunch_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA marketplace TO prolaunch_app;
GRANT INSERT ON ALL TABLES IN SCHEMA audit TO prolaunch_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA analytics TO prolaunch_app;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auth TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA marketplace TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO prolaunch_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO prolaunch_app;

-- Grant readonly permissions
GRANT SELECT ON ALL TABLES IN SCHEMA app TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA ai TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA marketplace TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO prolaunch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO prolaunch_readonly;

-- Grant admin full permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ai TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marketplace TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO prolaunch_admin;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ai TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA marketplace TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO prolaunch_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO prolaunch_admin;

-- =====================================================
-- 12. INITIAL SEED DATA
-- =====================================================

-- Insert default admin user (password should be changed immediately)
INSERT INTO auth.users (
    email,
    username,
    password_hash,
    full_name,
    role,
    status,
    subscription_tier,
    email_verified
) VALUES (
    'admin@prolaunch.com',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5OrcxhNyI8JDi', -- Change this!
    'System Administrator',
    'super_admin',
    'active',
    'enterprise',
    true
) ON CONFLICT (email) DO NOTHING;

-- Insert milestone templates
INSERT INTO app.milestones (project_id, milestone_type, name, description, objectives) 
SELECT 
    '00000000-0000-0000-0000-000000000000'::UUID,
    milestone_type,
    name,
    description,
    objectives
FROM (VALUES 
    ('M0_ideation', 'Ideation & Concept', 'Transform your idea into a viable business concept', 
     ARRAY['Define problem statement', 'Identify target audience', 'Research competition', 'Validate initial concept']),
    ('M1_validation', 'Market Validation', 'Validate your business idea with real market feedback',
     ARRAY['Conduct customer interviews', 'Create MVP', 'Test product-market fit', 'Gather feedback']),
    ('M2_planning', 'Business Planning', 'Create comprehensive business plan and strategy',
     ARRAY['Develop business model', 'Create financial projections', 'Define go-to-market strategy', 'Build team structure']),
    ('M3_development', 'Product Development', 'Build and refine your product or service',
     ARRAY['Develop full product', 'Implement feedback', 'Quality assurance', 'Prepare for launch']),
    ('M4_launch', 'Market Launch', 'Launch your business to the market',
     ARRAY['Execute launch plan', 'Marketing campaign', 'First customers', 'Monitor metrics']),
    ('M5_growth', 'Growth & Scale', 'Scale your business operations',
     ARRAY['Optimize operations', 'Expand market reach', 'Build partnerships', 'Secure funding'])
) AS t(milestone_type, name, description, objectives)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 13. MAINTENANCE PROCEDURES
-- =====================================================

-- Create a scheduled job to cleanup expired sessions (requires pg_cron extension)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-sessions', '0 2 * * *', $$SELECT cleanup_expired_sessions();$$);

-- Create a scheduled job to create new partitions
-- SELECT cron.schedule('create-partitions', '0 0 1 * *', $$SELECT create_monthly_partition();$$);

-- =====================================================
-- 14. COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE 'ProLaunch database schema created successfully!';
    RAISE NOTICE 'Remember to:';
    RAISE NOTICE '1. Change default passwords for all roles';
    RAISE NOTICE '2. Update admin user password';
    RAISE NOTICE '3. Configure SSL for production';
    RAISE NOTICE '4. Set up regular backups';
    RAISE NOTICE '5. Monitor query performance';
    RAISE NOTICE '6. Review and adjust RLS policies';
END $$;