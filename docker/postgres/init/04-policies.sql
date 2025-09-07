-- Enable Row Level Security
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE app.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing.usage_records ENABLE ROW LEVEL SECURITY;

-- User Policies
CREATE POLICY user_self_access ON auth.users
    FOR ALL
    USING (id = current_user_id());

CREATE POLICY user_org_member_read ON auth.users
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.user_id = auth.users.id
        AND om.organization_id IN (
            SELECT organization_id FROM app.organization_members
            WHERE user_id = current_user_id()
        )
    ));

-- Organization Policies
CREATE POLICY org_member_access ON app.organizations
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = app.organizations.id
        AND om.user_id = current_user_id()
    ));

CREATE POLICY org_admin_all ON app.organizations
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = app.organizations.id
        AND om.user_id = current_user_id()
        AND om.role = 'admin'
    ));

-- Project Policies
CREATE POLICY project_org_member_read ON app.projects
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = app.projects.organization_id
        AND om.user_id = current_user_id()
    ));

CREATE POLICY project_org_manager_write ON app.projects
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = app.projects.organization_id
        AND om.user_id = current_user_id()
        AND om.role IN ('admin', 'manager')
    ));

-- Task Policies
CREATE POLICY task_project_member_read ON app.tasks
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM app.projects p
        JOIN app.organization_members om ON om.organization_id = p.organization_id
        WHERE p.id = app.tasks.project_id
        AND om.user_id = current_user_id()
    ));

CREATE POLICY task_assigned_to_write ON app.tasks
    FOR UPDATE
    USING (assigned_to = current_user_id())
    WITH CHECK (assigned_to = current_user_id());

CREATE POLICY task_project_manager_write ON app.tasks
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM app.projects p
        JOIN app.organization_members om ON om.organization_id = p.organization_id
        WHERE p.id = app.tasks.project_id
        AND om.user_id = current_user_id()
        AND om.role IN ('admin', 'manager')
    ));

-- AI Policies
CREATE POLICY chat_owner_access ON ai.chat_conversations
    FOR ALL
    USING (user_id = current_user_id());

CREATE POLICY chat_message_conversation_access ON ai.chat_messages
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM ai.chat_conversations cc
        WHERE cc.id = ai.chat_messages.conversation_id
        AND cc.user_id = current_user_id()
    ));

-- Notification Policies
CREATE POLICY notification_owner_access ON notifications.notifications
    FOR ALL
    USING (user_id = current_user_id());

-- Billing Policies
CREATE POLICY subscription_org_admin_access ON billing.subscriptions
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = billing.subscriptions.organization_id
        AND om.user_id = current_user_id()
        AND om.role = 'admin'
    ));

CREATE POLICY usage_org_member_read ON billing.usage_records
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = billing.usage_records.organization_id
        AND om.user_id = current_user_id()
    ));

CREATE POLICY usage_org_admin_write ON billing.usage_records
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM app.organization_members om
        WHERE om.organization_id = billing.usage_records.organization_id
        AND om.user_id = current_user_id()
        AND om.role = 'admin'
    ));