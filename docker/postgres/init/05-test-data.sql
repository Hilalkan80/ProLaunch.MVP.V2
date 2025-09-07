-- Insert test users
INSERT INTO auth.users (email, password_hash, full_name, role, email_verified)
VALUES
    ('admin@prolaunch.local', crypt('admin123', gen_salt('bf')), 'Admin User', 'admin', true),
    ('manager@prolaunch.local', crypt('manager123', gen_salt('bf')), 'Manager User', 'manager', true),
    ('user@prolaunch.local', crypt('user123', gen_salt('bf')), 'Regular User', 'user', true);

-- Insert test organization
INSERT INTO app.organizations (name, slug, description, created_by)
SELECT 
    'ProLaunch Test Org',
    'prolaunch-test',
    'Test organization for development',
    id
FROM auth.users
WHERE email = 'admin@prolaunch.local';

-- Add organization members
INSERT INTO app.organization_members (organization_id, user_id, role)
SELECT 
    o.id,
    u.id,
    u.role
FROM app.organizations o
CROSS JOIN auth.users u;

-- Insert test projects
INSERT INTO app.projects (organization_id, name, slug, description, status, created_by)
SELECT
    o.id,
    name,
    slug,
    description,
    status,
    u.id
FROM app.organizations o
CROSS JOIN (
    VALUES
        ('Website Redesign', 'website-redesign', 'Complete website overhaul', 'active'::project_status),
        ('Mobile App Development', 'mobile-app', 'New mobile application', 'in_progress'::project_status),
        ('Marketing Campaign', 'marketing-campaign', 'Q4 marketing initiative', 'draft'::project_status)
) AS p(name, slug, description, status)
CROSS JOIN (
    SELECT id FROM auth.users WHERE email = 'admin@prolaunch.local'
) AS u;

-- Insert test tasks
INSERT INTO app.tasks (project_id, title, description, status, priority, assigned_to, due_date, created_by)
SELECT
    p.id,
    title,
    description,
    status,
    priority,
    u.id,
    due_date,
    u.id
FROM app.projects p
CROSS JOIN (
    VALUES
        ('Design mockups', 'Create initial design mockups', 'todo'::task_status, 1, now() + interval '7 days'),
        ('Frontend implementation', 'Implement approved designs', 'in_progress'::task_status, 2, now() + interval '14 days'),
        ('Backend API', 'Create REST API endpoints', 'review'::task_status, 2, now() + interval '10 days'),
        ('Testing', 'Comprehensive testing', 'todo'::task_status, 3, now() + interval '21 days')
) AS t(title, description, status, priority, due_date)
CROSS JOIN (
    SELECT id FROM auth.users WHERE email = 'user@prolaunch.local'
) AS u
WHERE p.name = 'Website Redesign';

-- Insert test chat conversations
INSERT INTO ai.chat_conversations (user_id, title, context)
SELECT
    u.id,
    'Project Planning Discussion',
    '{"project": "Website Redesign", "topic": "Initial Planning"}'::jsonb
FROM auth.users u
WHERE email = 'manager@prolaunch.local';

-- Insert test chat messages
INSERT INTO ai.chat_messages (conversation_id, role, content, tokens_used)
SELECT
    cc.id,
    role,
    content,
    tokens_used
FROM ai.chat_conversations cc
CROSS JOIN (
    VALUES
        ('user', 'How should we structure the website redesign project?', 15),
        ('assistant', 'I recommend breaking it down into the following phases: 1. Research & Planning, 2. Design, 3. Development, 4. Testing, 5. Deployment', 35),
        ('user', 'That sounds good. How long should each phase take?', 12),
        ('assistant', 'Based on typical project timelines: Research & Planning: 2 weeks, Design: 3 weeks, Development: 6 weeks, Testing: 2 weeks, Deployment: 1 week', 40)
) AS m(role, content, tokens_used);

-- Insert test notifications
INSERT INTO notifications.notifications (user_id, type, title, content)
SELECT
    u.id,
    'in_app',
    'Welcome to ProLaunch',
    'Welcome to the ProLaunch platform! Get started by exploring your dashboard.'
FROM auth.users u;

-- Insert test subscription
INSERT INTO billing.subscriptions (organization_id, plan_id, status, current_period_start, current_period_end)
SELECT
    o.id,
    'pro_monthly',
    'active',
    now(),
    now() + interval '1 month'
FROM app.organizations o;

-- Insert test usage records
INSERT INTO billing.usage_records (organization_id, feature, quantity)
SELECT
    o.id,
    feature,
    quantity
FROM app.organizations o
CROSS JOIN (
    VALUES
        ('api_calls', 1000),
        ('storage_gb', 5),
        ('ai_tokens', 50000)
) AS u(feature, quantity);