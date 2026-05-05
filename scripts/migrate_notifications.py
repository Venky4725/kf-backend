#!/usr/bin/env python3
"""
Migration script to add type and is_broadcast columns to notifications table.
Run this before deploying the updated backend.
"""

import sys
from sqlalchemy import text
from app.db.session import engine

def migrate():
    print("=" * 70)
    print("NOTIFICATIONS TABLE MIGRATION")
    print("=" * 70)
    
    try:
        with engine.begin() as conn:
            # Check if columns exist
            print("\n1. Checking existing columns...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'notifications'
            """))
            existing_columns = [row[0] for row in result]
            print(f"   Existing columns: {', '.join(existing_columns)}")
            
            # Add type column if it doesn't exist
            if 'type' not in existing_columns:
                print("\n2. Adding 'type' column...")
                conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN type VARCHAR
                """))
                print("   ✅ Added 'type' column")
            else:
                print("\n2. 'type' column already exists ✅")
            
            # Add is_broadcast column if it doesn't exist
            if 'is_broadcast' not in existing_columns:
                print("\n3. Adding 'is_broadcast' column...")
                conn.execute(text("""
                    ALTER TABLE notifications 
                    ADD COLUMN is_broadcast BOOLEAN DEFAULT FALSE
                """))
                print("   ✅ Added 'is_broadcast' column")
            else:
                print("\n3. 'is_broadcast' column already exists ✅")
            
            # Update existing records to have default values
            print("\n4. Updating existing records...")
            conn.execute(text("""
                UPDATE notifications 
                SET is_broadcast = FALSE 
                WHERE is_broadcast IS NULL
            """))
            print("   ✅ Updated existing records")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
            
            return 0
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(migrate())
