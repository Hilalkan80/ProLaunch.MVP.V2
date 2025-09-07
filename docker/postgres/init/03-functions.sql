-- User Management Functions
CREATE OR REPLACE FUNCTION auth.create_user(
    p_email text,
    p_password text,
    p_full_name text,
    p_role user_role DEFAULT 'user'
) RETURNS auth.users AS $$
DECLARE
    v_user auth.users;
BEGIN
    INSERT INTO auth.users (email, password_hash, full_name, role)
    VALUES (
        p_email,
        crypt(p_password, gen_salt('bf')),
        p_full_name,
        p_role
    )
    RETURNING * INTO v_user;
    
    RETURN v_user;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION auth.authenticate(
    p_email text,
    p_password text
) RETURNS auth.users AS $$
DECLARE
    v_user auth.users;
BEGIN
    SELECT * INTO v_user
    FROM auth.users
    WHERE email = p_email
        AND is_active = true
        AND (locked_until IS NULL OR locked_until < now());

    IF v_user.id IS NULL THEN
        RETURN NULL;
    END IF;

    IF v_user.password_hash = crypt(p_password, v_user.password_hash) THEN
        -- Reset failed attempts on successful login
        UPDATE auth.users
        SET failed_login_attempts = 0,
            last_login_at = now()
        WHERE id = v_user.id;
        
        RETURN v_user;
    ELSE
        -- Increment failed attempts
        UPDATE auth.users
        SET failed_login_attempts = failed_login_attempts + 1,
            locked_until = CASE
                WHEN failed_login_attempts >= 5 THEN now() + interval '15 minutes'
                ELSE locked_until
            END
        WHERE id = v_user.id;
        
        RETURN NULL;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Project Management Functions
CREATE OR REPLACE FUNCTION app.create_project(
    p_organization_id uuid,
    p_name text,
    p_description text,
    p_created_by uuid
) RETURNS app.projects AS $$
DECLARE
    v_project app.projects;
    v_slug slug;
BEGIN
    -- Generate slug from name
    v_slug := lower(regexp_replace(p_name, '[^a-zA-Z0-9]+', '-', 'g'));
    
    -- Ensure unique slug
    WHILE EXISTS (
        SELECT 1 FROM app.projects 
        WHERE organization_id = p_organization_id AND slug = v_slug
    ) LOOP
        v_slug := v_slug || '-' || floor(random() * 1000)::text;
    END LOOP;

    INSERT INTO app.projects (
        organization_id,
        name,
        slug,
        description,
        created_by
    )
    VALUES (
        p_organization_id,
        p_name,
        v_slug,
        p_description,
        p_created_by
    )
    RETURNING * INTO v_project;
    
    RETURN v_project;
END;
$$ LANGUAGE plpgsql;

-- Task Management Functions
CREATE OR REPLACE FUNCTION app.assign_task(
    p_task_id uuid,
    p_assigned_to uuid,
    p_updated_by uuid
) RETURNS app.tasks AS $$
DECLARE
    v_task app.tasks;
    v_project_id uuid;
    v_organization_id uuid;
    v_user_is_member boolean;
BEGIN
    -- Get task and project info
    SELECT t.*, p.organization_id INTO v_task, v_organization_id
    FROM app.tasks t
    JOIN app.projects p ON t.project_id = p.id
    WHERE t.id = p_task_id;
    
    -- Check if user is member of the organization
    SELECT EXISTS (
        SELECT 1 FROM app.organization_members
        WHERE organization_id = v_organization_id
        AND user_id = p_assigned_to
    ) INTO v_user_is_member;
    
    IF NOT v_user_is_member THEN
        RAISE EXCEPTION 'User is not a member of the organization';
    END IF;
    
    -- Update task assignment
    UPDATE app.tasks
    SET assigned_to = p_assigned_to,
        updated_at = now()
    WHERE id = p_task_id
    RETURNING * INTO v_task;
    
    -- Create notification
    INSERT INTO notifications.notifications (
        user_id,
        type,
        title,
        content
    )
    VALUES (
        p_assigned_to,
        'in_app',
        'Task Assigned',
        format('You have been assigned task: %s', v_task.title)
    );
    
    RETURN v_task;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.update_task_status(
    p_task_id uuid,
    p_status task_status,
    p_completion_percentage int,
    p_updated_by uuid
) RETURNS app.tasks AS $$
DECLARE
    v_task app.tasks;
    v_old_status task_status;
    v_project app.projects;
BEGIN
    -- Get current task status
    SELECT * INTO v_task
    FROM app.tasks
    WHERE id = p_task_id;
    
    v_old_status := v_task.status;
    
    -- Update task
    UPDATE app.tasks
    SET status = p_status,
        completion_percentage = p_completion_percentage,
        updated_at = now()
    WHERE id = p_task_id
    RETURNING * INTO v_task;
    
    -- Update project status if all tasks are completed
    IF p_status = 'completed' THEN
        SELECT p.* INTO v_project
        FROM app.projects p
        WHERE p.id = v_task.project_id;
        
        IF NOT EXISTS (
            SELECT 1 FROM app.tasks
            WHERE project_id = v_project.id
            AND status != 'completed'
        ) THEN
            UPDATE app.projects
            SET status = 'completed',
                updated_at = now()
            WHERE id = v_project.id;
        END IF;
    END IF;
    
    -- Notify assignee if status changed
    IF v_old_status != p_status AND v_task.assigned_to IS NOT NULL THEN
        INSERT INTO notifications.notifications (
            user_id,
            type,
            title,
            content
        )
        VALUES (
            v_task.assigned_to,
            'in_app',
            'Task Status Updated',
            format('Task "%s" status changed to %s', v_task.title, p_status)
        );
    END IF;
    
    RETURN v_task;
END;
$$ LANGUAGE plpgsql;

-- AI Functions
CREATE OR REPLACE FUNCTION ai.search_similar_content(
    p_embedding vector(1536),
    p_content_type text,
    p_limit int DEFAULT 5,
    p_threshold float DEFAULT 0.8
) RETURNS TABLE (
    id uuid,
    content_type text,
    content_id uuid,
    similarity float,
    metadata jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content_type,
        e.content_id,
        1 - (e.embedding <=> p_embedding) as similarity,
        e.metadata
    FROM ai.embeddings e
    WHERE e.content_type = p_content_type
        AND 1 - (e.embedding <=> p_embedding) >= p_threshold
    ORDER BY e.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION ai.upsert_embedding(
    p_content_type text,
    p_content_id uuid,
    p_embedding vector(1536),
    p_metadata jsonb DEFAULT NULL
) RETURNS ai.embeddings AS $$
DECLARE
    v_embedding ai.embeddings;
BEGIN
    INSERT INTO ai.embeddings (
        content_type,
        content_id,
        embedding,
        metadata
    )
    VALUES (
        p_content_type,
        p_content_id,
        p_embedding,
        p_metadata
    )
    ON CONFLICT (content_type, content_id) DO UPDATE
    SET embedding = p_embedding,
        metadata = p_metadata,
        created_at = now()
    RETURNING * INTO v_embedding;
    
    RETURN v_embedding;
END;
$$ LANGUAGE plpgsql;

-- Billing Functions
CREATE OR REPLACE FUNCTION billing.record_usage(
    p_organization_id uuid,
    p_feature text,
    p_quantity int
) RETURNS billing.usage_records AS $$
DECLARE
    v_usage_record billing.usage_records;
    v_subscription billing.subscriptions;
BEGIN
    -- Check active subscription
    SELECT * INTO v_subscription
    FROM billing.subscriptions
    WHERE organization_id = p_organization_id
        AND status = 'active'
        AND current_period_end > now();
        
    IF v_subscription.id IS NULL THEN
        RAISE EXCEPTION 'No active subscription found';
    END IF;
    
    -- Record usage
    INSERT INTO billing.usage_records (
        organization_id,
        feature,
        quantity
    )
    VALUES (
        p_organization_id,
        p_feature,
        p_quantity
    )
    RETURNING * INTO v_usage_record;
    
    RETURN v_usage_record;
END;
$$ LANGUAGE plpgsql;

-- Utility Functions
CREATE OR REPLACE FUNCTION app.calculate_project_metrics(p_project_id uuid)
RETURNS TABLE (
    total_tasks int,
    completed_tasks int,
    completion_percentage numeric,
    overdue_tasks int,
    avg_completion_time interval
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::int as total_tasks,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)::int as completed_tasks,
        ROUND((COUNT(CASE WHEN status = 'completed' THEN 1 END)::numeric / 
               NULLIF(COUNT(*)::numeric, 0)) * 100, 2) as completion_percentage,
        COUNT(CASE WHEN due_date < now() AND status != 'completed' THEN 1 END)::int as overdue_tasks,
        AVG(CASE 
            WHEN status = 'completed' 
            THEN updated_at - created_at 
        END) as avg_completion_time
    FROM app.tasks
    WHERE project_id = p_project_id;
END;
$$ LANGUAGE plpgsql;