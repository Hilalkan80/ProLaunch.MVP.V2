-- =====================================================
-- ProLaunch MVP V2 - Seed and Test Data
-- =====================================================
-- Version: 1.0.0
-- Description: Sample data for development and testing
-- WARNING: This script should only be run in development/test environments
-- =====================================================

-- =====================================================
-- SECTION 1: CONFIGURATION
-- =====================================================

-- Set variables for test data generation
DO $$
DECLARE
    v_test_users_count INT := 50;
    v_test_projects_count INT := 20;
    v_test_tasks_per_project INT := 30;
BEGIN
    -- Store in config table for reference
    CREATE TEMP TABLE IF NOT EXISTS test_config (
        key VARCHAR(50),
        value VARCHAR(100)
    );
    
    INSERT INTO test_config VALUES
        ('users_count', v_test_users_count::VARCHAR),
        ('projects_count', v_test_projects_count::VARCHAR),
        ('tasks_per_project', v_test_tasks_per_project::VARCHAR),
        ('seed_date', CURRENT_TIMESTAMP::VARCHAR);
END $$;

-- =====================================================
-- SECTION 2: TEST USERS
-- =====================================================

-- Create admin users
INSERT INTO auth.users (
    email, username, full_name, password_hash,
    role, status, subscription_tier, email_verified
) VALUES
    ('admin@prolaunch.com', 'admin', 'System Administrator', 
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5OrcxhNyI8JDi', -- password: Admin123!
     'super_admin', 'active', 'enterprise', true),
    
    ('john.doe@example.com', 'johndoe', 'John Doe',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5OrcxhNyI8JDi', -- password: Admin123!
     'admin', 'active', 'enterprise', true),
    
    ('jane.smith@example.com', 'janesmith', 'Jane Smith',
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5OrcxhNyI8JDi', -- password: Admin123!
     'moderator', 'active', 'professional', true)
ON CONFLICT (email) DO NOTHING;

-- Generate test users
INSERT INTO auth.users (
    email, username, full_name, password_hash,
    role, status, subscription_tier, email_verified,
    created_at, last_login_at
)
SELECT 
    'user' || i || '@example.com',
    'user' || i,
    'Test User ' || i,
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5OrcxhNyI8JDi', -- password: Admin123!
    CASE 
        WHEN i % 10 = 0 THEN 'premium_user'::auth.user_role
        ELSE 'user'::auth.user_role
    END,
    CASE 
        WHEN i % 20 = 0 THEN 'inactive'::auth.user_status
        ELSE 'active'::auth.user_status
    END,
    CASE 
        WHEN i % 5 = 0 THEN 'professional'::auth.subscription_tier
        WHEN i % 10 = 0 THEN 'business'::auth.subscription_tier
        ELSE 'free'::auth.subscription_tier
    END,
    true,
    CURRENT_TIMESTAMP - INTERVAL '1 day' * (random() * 365)::INT,
    CURRENT_TIMESTAMP - INTERVAL '1 hour' * (random() * 168)::INT
FROM generate_series(1, 50) i
ON CONFLICT (email) DO NOTHING;

-- Create user profiles for all users
INSERT INTO app.user_profiles (
    user_id, bio, headline, company_name, company_role,
    industry, years_experience, country, city,
    linkedin_url, skills, languages,
    profile_completion_percentage, onboarding_completed
)
SELECT 
    u.id,
    'Passionate entrepreneur and ' || 
    CASE (random() * 4)::INT 
        WHEN 0 THEN 'software developer'
        WHEN 1 THEN 'product manager'
        WHEN 2 THEN 'designer'
        WHEN 3 THEN 'marketing specialist'
        ELSE 'business strategist'
    END || ' with extensive experience.',
    CASE (random() * 4)::INT 
        WHEN 0 THEN 'Building the future'
        WHEN 1 THEN 'Innovation enthusiast'
        WHEN 2 THEN 'Serial entrepreneur'
        WHEN 3 THEN 'Tech visionary'
        ELSE 'Startup founder'
    END,
    'Company ' || substr(md5(random()::text), 1, 8),
    CASE (random() * 5)::INT 
        WHEN 0 THEN 'CEO'
        WHEN 1 THEN 'CTO'
        WHEN 2 THEN 'Product Manager'
        WHEN 3 THEN 'Developer'
        WHEN 4 THEN 'Designer'
        ELSE 'Founder'
    END,
    CASE (random() * 5)::INT 
        WHEN 0 THEN 'Technology'
        WHEN 1 THEN 'Healthcare'
        WHEN 2 THEN 'Finance'
        WHEN 3 THEN 'E-commerce'
        WHEN 4 THEN 'Education'
        ELSE 'SaaS'
    END,
    (random() * 15 + 1)::INT,
    CASE (random() * 5)::INT 
        WHEN 0 THEN 'US'
        WHEN 1 THEN 'GB'
        WHEN 2 THEN 'CA'
        WHEN 3 THEN 'AU'
        WHEN 4 THEN 'DE'
        ELSE 'FR'
    END,
    CASE (random() * 5)::INT 
        WHEN 0 THEN 'New York'
        WHEN 1 THEN 'London'
        WHEN 2 THEN 'San Francisco'
        WHEN 3 THEN 'Toronto'
        WHEN 4 THEN 'Berlin'
        ELSE 'Paris'
    END,
    'https://linkedin.com/in/user-' || substr(md5(random()::text), 1, 8),
    ARRAY['JavaScript', 'Python', 'SQL', 'React', 'Node.js', 'AWS'],
    ARRAY['English', 'Spanish'],
    (random() * 40 + 60)::INT,
    true
FROM auth.users u
LEFT JOIN app.user_profiles p ON u.id = p.user_id
WHERE p.id IS NULL;

-- =====================================================
-- SECTION 3: TEST PROJECTS
-- =====================================================

-- Create diverse test projects
INSERT INTO app.projects (
    user_id, name, slug, description, short_description,
    industry, business_model, target_market,
    current_milestone, milestone_progress, overall_progress,
    is_active, is_public, team_size, funding_stage,
    created_at, tags
)
SELECT 
    u.id,
    project_names.name,
    LOWER(REPLACE(project_names.name, ' ', '-')) || '-' || substr(md5(random()::text), 1, 6),
    project_names.description,
    substr(project_names.description, 1, 200),
    project_names.industry,
    project_names.business_model,
    'Small to medium businesses in ' || project_names.industry,
    project_names.milestone,
    (random() * 100)::INT,
    (random() * 100)::INT,
    true,
    random() > 0.7,
    (random() * 10 + 1)::INT,
    project_names.funding_stage,
    CURRENT_TIMESTAMP - INTERVAL '1 day' * (random() * 180)::INT,
    project_names.tags
FROM (
    SELECT id, row_number() OVER (ORDER BY random()) as rn 
    FROM auth.users 
    WHERE role NOT IN ('super_admin', 'admin')
) u
JOIN (
    SELECT 
        row_number() OVER () as rn,
        name, description, industry, business_model, milestone, funding_stage, tags
    FROM (VALUES
        ('TechStart AI', 'AI-powered platform for automating business processes using machine learning', 
         'Technology', 'SaaS', 'M3_development'::app.milestone_type, 'seed', 
         ARRAY['ai', 'automation', 'saas']),
        
        ('HealthTrack Pro', 'Comprehensive health monitoring and analytics platform for fitness enthusiasts', 
         'Healthcare', 'B2C Subscription', 'M2_planning'::app.milestone_type, 'pre-seed',
         ARRAY['health', 'fitness', 'mobile']),
        
        ('EduLearn Platform', 'Interactive online learning platform with personalized curricula', 
         'Education', 'Marketplace', 'M4_launch'::app.milestone_type, 'series-a',
         ARRAY['education', 'edtech', 'online-learning']),
        
        ('GreenEnergy Solutions', 'Renewable energy management system for residential and commercial use', 
         'Energy', 'B2B', 'M1_validation'::app.milestone_type, 'seed',
         ARRAY['cleantech', 'energy', 'sustainability']),
        
        ('FinanceFlow', 'Personal finance management with AI-driven insights and recommendations', 
         'Finance', 'Freemium', 'M5_growth'::app.milestone_type, 'series-b',
         ARRAY['fintech', 'ai', 'personal-finance']),
        
        ('MarketPlace Connect', 'B2B marketplace connecting suppliers with retailers globally', 
         'E-commerce', 'Transaction Fee', 'M3_development'::app.milestone_type, 'seed',
         ARRAY['marketplace', 'b2b', 'ecommerce']),
        
        ('FoodDelivery Express', 'Ultra-fast food delivery service with drone technology', 
         'Food & Beverage', 'Commission', 'M2_planning'::app.milestone_type, 'series-a',
         ARRAY['food-delivery', 'logistics', 'drones']),
        
        ('CyberShield Security', 'Enterprise cybersecurity platform with threat detection', 
         'Security', 'Enterprise License', 'M4_launch'::app.milestone_type, 'series-b',
         ARRAY['cybersecurity', 'enterprise', 'ai']),
        
        ('TravelBuddy App', 'Social travel planning and booking platform', 
         'Travel', 'Commission + Premium', 'M1_validation'::app.milestone_type, 'pre-seed',
         ARRAY['travel', 'social', 'mobile']),
        
        ('SmartHome Hub', 'IoT platform for home automation and energy management', 
         'IoT', 'Hardware + Subscription', 'M3_development'::app.milestone_type, 'seed',
         ARRAY['iot', 'smart-home', 'hardware']),
        
        ('CloudSync Pro', 'Advanced cloud storage with AI-powered organization', 
         'Cloud Services', 'Subscription', 'M5_growth'::app.milestone_type, 'series-a',
         ARRAY['cloud', 'storage', 'ai']),
        
        ('GameStudio Platform', 'Indie game development and publishing platform', 
         'Gaming', 'Revenue Share', 'M2_planning'::app.milestone_type, 'seed',
         ARRAY['gaming', 'platform', 'indie']),
        
        ('LegalTech Assistant', 'AI-powered legal document automation and review', 
         'Legal', 'SaaS', 'M4_launch'::app.milestone_type, 'series-a',
         ARRAY['legaltech', 'ai', 'automation']),
        
        ('AgriTech Solutions', 'Precision agriculture platform with IoT sensors', 
         'Agriculture', 'Hardware + SaaS', 'M1_validation'::app.milestone_type, 'pre-seed',
         ARRAY['agritech', 'iot', 'sustainability']),
        
        ('MediaStream Live', 'Live streaming platform for content creators', 
         'Media', 'Subscription + Ads', 'M3_development'::app.milestone_type, 'seed',
         ARRAY['streaming', 'media', 'content']),
        
        ('RealEstate Pro', 'Property management and investment analytics platform', 
         'Real Estate', 'Commission', 'M2_planning'::app.milestone_type, 'series-a',
         ARRAY['proptech', 'real-estate', 'analytics']),
        
        ('LogisticsChain', 'Blockchain-based supply chain management system', 
         'Logistics', 'Enterprise', 'M4_launch'::app.milestone_type, 'series-b',
         ARRAY['blockchain', 'logistics', 'enterprise']),
        
        ('WellnessCoach AI', 'Personalized wellness and mental health platform', 
         'Wellness', 'Subscription', 'M1_validation'::app.milestone_type, 'pre-seed',
         ARRAY['wellness', 'mental-health', 'ai']),
        
        ('RetailAnalytics', 'Retail analytics and customer behavior prediction', 
         'Retail', 'SaaS', 'M5_growth'::app.milestone_type, 'series-a',
         ARRAY['retail', 'analytics', 'ai']),
        
        ('CryptoWallet Plus', 'Secure multi-chain cryptocurrency wallet with DeFi integration', 
         'Cryptocurrency', 'Transaction Fee', 'M3_development'::app.milestone_type, 'seed',
         ARRAY['crypto', 'defi', 'blockchain'])
    ) AS project_list(name, description, industry, business_model, milestone, funding_stage, tags)
) project_names ON u.rn = project_names.rn
WHERE project_names.rn <= 20
ON CONFLICT (slug) DO NOTHING;

-- Add team members to projects
INSERT INTO app.project_members (
    project_id, user_id, role, joined_at
)
SELECT DISTINCT
    p.id,
    u.id,
    CASE 
        WHEN random() < 0.2 THEN 'admin'
        WHEN random() < 0.4 THEN 'editor'
        ELSE 'member'
    END,
    p.created_at + INTERVAL '1 day' * (random() * 30)::INT
FROM app.projects p
CROSS JOIN auth.users u
WHERE u.id != p.user_id
    AND random() < 0.3  -- 30% chance of being a member
    AND NOT EXISTS (
        SELECT 1 FROM app.project_members pm 
        WHERE pm.project_id = p.id AND pm.user_id = u.id
    )
LIMIT 100;

-- =====================================================
-- SECTION 4: MILESTONES AND TASKS
-- =====================================================

-- Create milestones for each project
INSERT INTO app.milestones (
    project_id, milestone_type, name, description,
    status, progress_percentage, start_date, target_date,
    objectives, deliverables
)
SELECT 
    p.id,
    mt.milestone_type,
    CASE mt.milestone_type
        WHEN 'M0_ideation' THEN 'Ideation & Concept Development'
        WHEN 'M1_validation' THEN 'Market Validation'
        WHEN 'M2_planning' THEN 'Business Planning'
        WHEN 'M3_development' THEN 'Product Development'
        WHEN 'M4_launch' THEN 'Market Launch'
        WHEN 'M5_growth' THEN 'Growth & Scaling'
        WHEN 'M6_scale' THEN 'Scale Operations'
        WHEN 'M7_exit' THEN 'Exit Strategy'
    END,
    'Strategic milestone for ' || p.name,
    CASE 
        WHEN mt.milestone_type < p.current_milestone THEN 'completed'::app.milestone_status
        WHEN mt.milestone_type = p.current_milestone THEN 'in_progress'::app.milestone_status
        ELSE 'not_started'::app.milestone_status
    END,
    CASE 
        WHEN mt.milestone_type < p.current_milestone THEN 100
        WHEN mt.milestone_type = p.current_milestone THEN (random() * 80 + 20)::INT
        ELSE 0
    END,
    p.created_at + INTERVAL '30 days' * (mt.milestone_order - 1),
    p.created_at + INTERVAL '30 days' * mt.milestone_order,
    ARRAY['Objective 1', 'Objective 2', 'Objective 3'],
    ARRAY['Deliverable 1', 'Deliverable 2', 'Deliverable 3']
FROM app.projects p
CROSS JOIN (
    SELECT milestone_type, 
           row_number() OVER (ORDER BY milestone_type) as milestone_order
    FROM unnest(enum_range(NULL::app.milestone_type)) milestone_type
) mt
ON CONFLICT (project_id, milestone_type) DO NOTHING;

-- Generate tasks for projects
INSERT INTO app.tasks (
    project_id, milestone_id, created_by, assigned_to,
    title, description, priority, status,
    estimated_hours, due_date, tags, created_at
)
SELECT 
    p.id,
    m.id,
    p.user_id,
    CASE WHEN random() < 0.7 THEN 
        (SELECT user_id FROM app.project_members 
         WHERE project_id = p.id 
         ORDER BY random() LIMIT 1)
    ELSE p.user_id END,
    task_titles.title,
    'Detailed description for: ' || task_titles.title || '. This task is part of the ' || m.name || ' milestone.',
    task_titles.priority,
    task_titles.status,
    (random() * 40 + 1)::INT,
    CURRENT_DATE + INTERVAL '1 day' * (random() * 60)::INT,
    task_titles.tags,
    p.created_at + INTERVAL '1 day' * (random() * 30)::INT
FROM app.projects p
JOIN app.milestones m ON m.project_id = p.id
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('Research market competitors', ARRAY['research', 'analysis'], 'high'::app.task_priority, 
         CASE WHEN random() < 0.3 THEN 'completed'::app.task_status 
              WHEN random() < 0.5 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Define product requirements', ARRAY['planning', 'product'], 'critical'::app.task_priority,
         CASE WHEN random() < 0.4 THEN 'completed'::app.task_status 
              WHEN random() < 0.6 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Create wireframes and mockups', ARRAY['design', 'ui'], 'high'::app.task_priority,
         CASE WHEN random() < 0.2 THEN 'completed'::app.task_status 
              WHEN random() < 0.4 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Develop MVP features', ARRAY['development', 'mvp'], 'critical'::app.task_priority,
         CASE WHEN random() < 0.25 THEN 'completed'::app.task_status 
              WHEN random() < 0.5 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Setup CI/CD pipeline', ARRAY['devops', 'infrastructure'], 'medium'::app.task_priority,
         CASE WHEN random() < 0.3 THEN 'completed'::app.task_status 
              WHEN random() < 0.4 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Write unit tests', ARRAY['testing', 'quality'], 'high'::app.task_priority,
         CASE WHEN random() < 0.2 THEN 'completed'::app.task_status 
              WHEN random() < 0.3 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Prepare marketing materials', ARRAY['marketing', 'content'], 'medium'::app.task_priority,
         CASE WHEN random() < 0.35 THEN 'completed'::app.task_status 
              WHEN random() < 0.5 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Conduct user interviews', ARRAY['research', 'user-feedback'], 'high'::app.task_priority,
         CASE WHEN random() < 0.4 THEN 'completed'::app.task_status 
              WHEN random() < 0.6 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Implement authentication', ARRAY['development', 'security'], 'critical'::app.task_priority,
         CASE WHEN random() < 0.5 THEN 'completed'::app.task_status 
              WHEN random() < 0.7 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END),
        
        ('Setup monitoring and analytics', ARRAY['devops', 'monitoring'], 'medium'::app.task_priority,
         CASE WHEN random() < 0.3 THEN 'completed'::app.task_status 
              WHEN random() < 0.45 THEN 'in_progress'::app.task_status 
              ELSE 'todo'::app.task_status END)
    ) AS task_list(title, tags, priority, status)
    ORDER BY random()
    LIMIT 5
) task_titles;

-- Add task comments
INSERT INTO app.task_comments (
    task_id, user_id, content, created_at
)
SELECT 
    t.id,
    COALESCE(t.assigned_to, t.created_by),
    comments.content,
    t.created_at + INTERVAL '1 hour' * (random() * 48)::INT
FROM app.tasks t
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('Great progress on this task!'),
        ('I need more information about the requirements.'),
        ('This is blocked by the API development.'),
        ('Completed the initial implementation, ready for review.'),
        ('Found an issue, will need to revisit this.')
    ) AS c(content)
    ORDER BY random()
    LIMIT CASE WHEN random() < 0.3 THEN 2 ELSE 1 END
) comments
WHERE random() < 0.4;  -- 40% of tasks have comments

-- =====================================================
-- SECTION 5: AI CHAT DATA
-- =====================================================

-- Create chat conversations
INSERT INTO ai.chat_conversations (
    project_id, user_id, title, model, created_at, last_message_at
)
SELECT 
    p.id,
    p.user_id,
    conversation_titles.title,
    CASE WHEN random() < 0.7 THEN 'gpt-4'::ai.ai_model ELSE 'gpt-3.5-turbo'::ai.ai_model END,
    p.created_at + INTERVAL '1 day' * (random() * 30)::INT,
    p.created_at + INTERVAL '1 day' * (random() * 30 + 1)::INT
FROM app.projects p
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('Business strategy discussion'),
        ('Technical architecture planning'),
        ('Marketing campaign ideas'),
        ('Product feature brainstorming'),
        ('Competitive analysis')
    ) AS titles(title)
    ORDER BY random()
    LIMIT 2
) conversation_titles
WHERE random() < 0.6;  -- 60% of projects have conversations

-- Add chat messages
INSERT INTO ai.chat_messages (
    conversation_id, role, content, created_at
)
SELECT 
    c.id,
    message_data.role,
    message_data.content,
    c.created_at + INTERVAL '1 minute' * row_number() OVER (PARTITION BY c.id ORDER BY message_data.seq)
FROM ai.chat_conversations c
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        (1, 'user'::ai.message_role, 'What are the key considerations for launching a SaaS product?'),
        (2, 'assistant'::ai.message_role, 'Here are the key considerations for launching a SaaS product:

1. **Product-Market Fit**: Ensure your product solves a real problem
2. **Pricing Strategy**: Choose between freemium, tiered, or usage-based pricing
3. **Technical Infrastructure**: Scalable architecture, security, and reliability
4. **Customer Onboarding**: Smooth onboarding experience and documentation
5. **Support System**: Customer support channels and response times'),
        (3, 'user'::ai.message_role, 'How should I approach pricing for my product?'),
        (4, 'assistant'::ai.message_role, 'For SaaS pricing strategy, consider:

1. **Value-Based Pricing**: Price based on the value you provide
2. **Competitor Analysis**: Research what similar products charge
3. **Tiered Plans**: Offer multiple tiers (Basic, Pro, Enterprise)
4. **Free Trial**: 14-30 day trials to demonstrate value
5. **Annual Discounts**: Offer 15-20% discount for annual payments')
    ) AS messages(seq, role, content)
) message_data;

-- =====================================================
-- SECTION 6: NOTIFICATIONS
-- =====================================================

-- Generate sample notifications
INSERT INTO notifications.queue (
    user_id, channel, subject, body, status, created_at
)
SELECT 
    u.id,
    'in_app'::notifications.channel,
    notification_data.subject,
    notification_data.body,
    CASE 
        WHEN random() < 0.7 THEN 'sent'::notifications.status
        WHEN random() < 0.9 THEN 'delivered'::notifications.status
        ELSE 'pending'::notifications.status
    END,
    CURRENT_TIMESTAMP - INTERVAL '1 hour' * (random() * 168)::INT
FROM auth.users u
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('New task assigned', 'You have been assigned a new task: Research market competitors'),
        ('Project invitation', 'You have been invited to join TechStart AI project'),
        ('Milestone completed', 'Congratulations! The Planning milestone has been completed'),
        ('Comment mention', 'You were mentioned in a comment on task: Define product requirements'),
        ('Weekly digest', 'Your weekly project summary is ready')
    ) AS notif(subject, body)
    ORDER BY random()
    LIMIT 3
) notification_data
WHERE u.role = 'user'
    AND random() < 0.3;  -- 30% of users have notifications

-- =====================================================
-- SECTION 7: ANALYTICS DATA
-- =====================================================

-- Generate user analytics
INSERT INTO analytics.user_analytics (
    user_id, date, login_count, active_minutes,
    tasks_created, tasks_completed, documents_created,
    chat_messages_sent, ai_tokens_used
)
SELECT 
    u.id,
    dates.date,
    (random() * 5)::INT,
    (random() * 480)::INT,
    (random() * 10)::INT,
    (random() * 8)::INT,
    (random() * 5)::INT,
    (random() * 20)::INT,
    (random() * 5000)::INT
FROM auth.users u
CROSS JOIN (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        '1 day'::interval
    )::DATE AS date
) dates
WHERE u.role = 'user'
    AND random() < 0.5  -- 50% chance of activity per day
ON CONFLICT (user_id, date) DO NOTHING;

-- Generate project analytics
INSERT INTO analytics.project_analytics (
    project_id, date, active_users,
    tasks_created, tasks_completed,
    documents_created, chat_conversations,
    ai_tokens_used
)
SELECT 
    p.id,
    dates.date,
    (random() * member_count + 1)::INT,
    (random() * 15)::INT,
    (random() * 10)::INT,
    (random() * 5)::INT,
    (random() * 8)::INT,
    (random() * 10000)::INT
FROM (
    SELECT p.id, COUNT(pm.id) + 1 as member_count
    FROM app.projects p
    LEFT JOIN app.project_members pm ON p.id = pm.project_id
    GROUP BY p.id
) p
CROSS JOIN (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '30 days',
        CURRENT_DATE,
        '1 day'::interval
    )::DATE AS date
) dates
WHERE random() < 0.7  -- 70% chance of activity per day
ON CONFLICT (project_id, date) DO NOTHING;

-- =====================================================
-- SECTION 8: SAMPLE EMBEDDINGS
-- =====================================================

-- Generate sample embeddings for semantic search
-- Note: These are random vectors for testing. In production, use actual embedding API
INSERT INTO ai.embeddings (
    content_type, content_id, content_chunk, embedding
)
SELECT 
    'project',
    p.id,
    p.name || ' ' || COALESCE(p.description, ''),
    -- Generate random 1536-dimensional vector (OpenAI ada-002 dimensions)
    ARRAY(SELECT random()::REAL FROM generate_series(1, 1536))::vector(1536)
FROM app.projects p
WHERE random() < 0.5;  -- 50% of projects have embeddings

-- =====================================================
-- SECTION 9: VERIFICATION QUERIES
-- =====================================================

-- Verify data creation
DO $$
DECLARE
    v_users_count INT;
    v_projects_count INT;
    v_tasks_count INT;
    v_conversations_count INT;
BEGIN
    SELECT COUNT(*) INTO v_users_count FROM auth.users;
    SELECT COUNT(*) INTO v_projects_count FROM app.projects;
    SELECT COUNT(*) INTO v_tasks_count FROM app.tasks;
    SELECT COUNT(*) INTO v_conversations_count FROM ai.chat_conversations;
    
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Test Data Creation Summary';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Users created: %', v_users_count;
    RAISE NOTICE 'Projects created: %', v_projects_count;
    RAISE NOTICE 'Tasks created: %', v_tasks_count;
    RAISE NOTICE 'Chat conversations created: %', v_conversations_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Sample users:';
    RAISE NOTICE '- Admin: admin@prolaunch.com / Admin123!';
    RAISE NOTICE '- User: john.doe@example.com / Admin123!';
    RAISE NOTICE '- Test: user1@example.com / Admin123!';
    RAISE NOTICE '================================================';
END $$;

-- =====================================================
-- SECTION 10: USEFUL DEVELOPMENT QUERIES
-- =====================================================

-- View project overview
CREATE OR REPLACE VIEW dev.project_summary AS
SELECT 
    p.name AS project_name,
    u.email AS owner_email,
    p.current_milestone,
    p.overall_progress || '%' AS progress,
    COUNT(DISTINCT pm.user_id) + 1 AS team_size,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    COUNT(DISTINCT c.id) AS chat_conversations
FROM app.projects p
JOIN auth.users u ON p.user_id = u.id
LEFT JOIN app.project_members pm ON p.id = pm.project_id
LEFT JOIN app.tasks t ON p.id = t.project_id
LEFT JOIN ai.chat_conversations c ON p.id = c.project_id
GROUP BY p.id, p.name, u.email, p.current_milestone, p.overall_progress
ORDER BY p.created_at DESC;

-- View user activity
CREATE OR REPLACE VIEW dev.user_activity AS
SELECT 
    u.email,
    u.role,
    u.subscription_tier,
    COUNT(DISTINCT p.id) AS projects,
    COUNT(DISTINCT t.id) AS tasks_assigned,
    u.last_login_at,
    CASE 
        WHEN u.last_activity_at > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 'Online'
        WHEN u.last_activity_at > CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 'Recently active'
        ELSE 'Inactive'
    END AS activity_status
FROM auth.users u
LEFT JOIN app.projects p ON u.id = p.user_id
LEFT JOIN app.tasks t ON u.id = t.assigned_to
GROUP BY u.id, u.email, u.role, u.subscription_tier, u.last_login_at, u.last_activity_at
ORDER BY u.last_activity_at DESC NULLS LAST;

-- Quick stats function
CREATE OR REPLACE FUNCTION dev.quick_stats()
RETURNS TABLE (
    metric VARCHAR,
    value BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'Total Users'::VARCHAR, COUNT(*)::BIGINT FROM auth.users
    UNION ALL
    SELECT 'Active Projects'::VARCHAR, COUNT(*)::BIGINT FROM app.projects WHERE is_active = true
    UNION ALL
    SELECT 'Pending Tasks'::VARCHAR, COUNT(*)::BIGINT FROM app.tasks WHERE status IN ('todo', 'in_progress')
    UNION ALL
    SELECT 'Chat Messages'::VARCHAR, COUNT(*)::BIGINT FROM ai.chat_messages
    UNION ALL
    SELECT 'Active Sessions'::VARCHAR, COUNT(*)::BIGINT FROM auth.sessions WHERE expires_at > CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Usage: SELECT * FROM dev.quick_stats();

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '================================================';
    RAISE NOTICE 'Development/Test Data Seeding Complete!';
    RAISE NOTICE '================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'To view quick statistics:';
    RAISE NOTICE '  SELECT * FROM dev.quick_stats();';
    RAISE NOTICE '';
    RAISE NOTICE 'To view project summary:';
    RAISE NOTICE '  SELECT * FROM dev.project_summary;';
    RAISE NOTICE '';
    RAISE NOTICE 'To view user activity:';
    RAISE NOTICE '  SELECT * FROM dev.user_activity;';
    RAISE NOTICE '================================================';
END $$;