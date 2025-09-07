#!/usr/bin/env python3
"""
Script to run the milestone system migration.
This creates all necessary tables for the milestone tracking system.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Debug: Print database URL
print(f"DATABASE_URL from env: {os.getenv('DATABASE_URL')}")

from sqlalchemy import text
from src.models.base import engine, Base
from src.models import (
    Milestone, MilestoneDependency, UserMilestone,
    MilestoneArtifact, UserMilestoneArtifact,
    MilestoneProgressLog, MilestoneCache
)


async def run_migration():
    """Execute the milestone system migration"""
    async with engine.begin() as conn:
        try:
            # Create all tables defined in the models
            await conn.run_sync(Base.metadata.create_all)
            
            print("[SUCCESS] Milestone system tables created successfully!")
            
            # Verify tables were created
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'milestones', 'milestone_dependencies', 'user_milestones',
                    'milestone_artifacts', 'user_milestone_artifacts',
                    'milestone_progress_logs', 'milestone_cache'
                )
                ORDER BY table_name;
            """))
            
            tables = result.fetchall()
            print("\n[INFO] Created tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            # Check if we need to insert initial milestone data
            milestone_count = await conn.execute(text("SELECT COUNT(*) FROM milestones"))
            count = milestone_count.scalar()
            
            if count == 0:
                print("\n[INFO] Inserting initial milestone definitions...")
                
                # Insert milestone definitions
                await conn.execute(text("""
                    INSERT INTO milestones (id, code, name, description, milestone_type, order_index, 
                                          estimated_minutes, is_active, requires_payment, auto_unlock)
                    VALUES 
                    (gen_random_uuid(), 'M0', 'Business Foundation', 
                     'Define your business idea, target market, and value proposition', 
                     'free', 0, 45, true, false, true),
                    
                    (gen_random_uuid(), 'M1', 'Market Research & Validation', 
                     'Conduct comprehensive market research and validate your business concept', 
                     'paid', 1, 60, true, true, false),
                    
                    (gen_random_uuid(), 'M2', 'Business Model & Strategy', 
                     'Develop your business model canvas and strategic roadmap', 
                     'paid', 2, 90, true, true, false),
                    
                    (gen_random_uuid(), 'M3', 'Financial Planning', 
                     'Create financial projections, budgets, and funding strategies', 
                     'paid', 3, 120, true, true, false),
                    
                    (gen_random_uuid(), 'M4', 'Product Development Plan', 
                     'Design your MVP and product development roadmap', 
                     'paid', 4, 90, true, true, false),
                    
                    (gen_random_uuid(), 'M5', 'Marketing & Sales Strategy', 
                     'Build your go-to-market strategy and sales funnel', 
                     'paid', 5, 75, true, true, false),
                    
                    (gen_random_uuid(), 'M6', 'Operations Planning', 
                     'Plan operational workflows, supply chain, and logistics', 
                     'paid', 6, 60, true, true, false),
                    
                    (gen_random_uuid(), 'M7', 'Legal & Compliance', 
                     'Address legal structure, intellectual property, and compliance requirements', 
                     'paid', 7, 45, true, true, false),
                    
                    (gen_random_uuid(), 'M8', 'Launch Preparation', 
                     'Prepare for launch with final checklists and contingency plans', 
                     'paid', 8, 60, true, true, false),
                    
                    (gen_random_uuid(), 'M9', 'Executive Summary', 
                     'Compile a comprehensive executive summary and pitch deck', 
                     'free', 9, 30, true, false, false)
                """))
                
                print("[SUCCESS] Milestone definitions inserted!")
                
                # Set up dependencies
                await conn.execute(text("""
                    WITH milestone_ids AS (
                        SELECT id, code FROM milestones
                    )
                    INSERT INTO milestone_dependencies (id, milestone_id, dependency_id, is_required)
                    SELECT 
                        gen_random_uuid(),
                        m.id,
                        d.id,
                        true
                    FROM milestone_ids m
                    CROSS JOIN milestone_ids d
                    WHERE 
                        (m.code IN ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8') AND d.code = 'M0')
                        OR (m.code = 'M9' AND d.code IN ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8'))
                """))
                
                print("[SUCCESS] Milestone dependencies configured!")
            else:
                print(f"\n[OK] Milestones already exist ({count} found)")
            
            # Show milestone summary
            milestones = await conn.execute(text("""
                SELECT code, name, milestone_type, requires_payment 
                FROM milestones 
                ORDER BY order_index
            """))
            
            print("\n[INFO] Milestone Summary:")
            for m in milestones:
                payment = "[PAID]" if m[3] else "[FREE]"
                print(f"  {payment} {m[0]}: {m[1]} ({m[2]})")
            
            print("\n[SUCCESS] Migration completed successfully!")
            
        except Exception as e:
            print(f"\n[ERROR] Migration failed: {str(e)}")
            raise
    
    await engine.dispose()


if __name__ == "__main__":
    print("Running Milestone System Migration...")
    print("=" * 50)
    asyncio.run(run_migration())