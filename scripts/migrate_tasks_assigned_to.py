#!/usr/bin/env python3
"""
Migration script to add assigned_to column to tasks table.
Run this before deploying the updated backend.
"""

import sys
from sqlalchemy import text
from app.db.session import engine

def migrate():
    print("=" * 70)
    print("TASKS TABLE MIGRATION - ADD assigned_to COLUMN")
    print("=" * 70)
    
    try:
        with engine.begin() as conn:
            # Check if column exists
            print("\n1. Checking existing columns...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks'
            """))
            existing_columns = [row[0] for row in result]
            print(f"   Existing columns: {', '.join(existing_columns)}")
            
            # Add assigned_to column if it doesn't exist
            if 'assigned_to' not in existing_columns:
                print("\n2. Adding 'assigned_to' column...")
                conn.execute(text("""
                    ALTER TABLE tasks 
                    ADD COLUMN assigned_to UUID REFERENCES profiles(id)
                """))
                print("   ✅ Added 'assigned_to' column")
            else:
                print("\n2. 'assigned_to' column already exists ✅")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\nTasks can now be assigned to individual users!")
            print("Use 'assigned_to' field in POST /api/tasks")
            
            return 0
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(migrate())
