#!/usr/bin/env python3
"""
Backfill script to set sender_id for existing notifications that have NULL sender_id.

This script will:
1. Find all notifications with NULL sender_id
2. Set sender_id to the first ADMIN user (for system notifications)
3. Or set to a specific user if needed

Usage:
    python scripts/backfill_notification_sender.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.db.session import SessionLocal


def backfill():
    """Backfill sender_id for existing notifications"""
    db = SessionLocal()
    
    try:
        print("Starting backfill: Setting sender_id for existing notifications...")
        
        # Check how many notifications have NULL sender_id
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM notifications 
            WHERE sender_id IS NULL;
        """))
        null_count = result.fetchone()[0]
        
        if null_count == 0:
            print("✅ No notifications need backfilling. All have sender_id set.")
            return
        
        print(f"Found {null_count} notifications with NULL sender_id")
        
        # Get first ADMIN user to use as default sender
        result = db.execute(text("""
            SELECT id, name 
            FROM profiles 
            WHERE role = 'ADMIN' 
            LIMIT 1;
        """))
        admin = result.fetchone()
        
        if not admin:
            print("❌ No ADMIN user found. Cannot backfill.")
            print("   Please create an ADMIN user first or manually set sender_id.")
            return
        
        admin_id = admin[0]
        admin_name = admin[1]
        
        print(f"Using ADMIN user '{admin_name}' ({admin_id}) as default sender")
        
        # Update all NULL sender_id to admin
        db.execute(text("""
            UPDATE notifications 
            SET sender_id = :admin_id 
            WHERE sender_id IS NULL;
        """), {"admin_id": admin_id})
        
        db.commit()
        
        print(f"✅ Backfill completed successfully!")
        print(f"   - Updated {null_count} notifications")
        print(f"   - Set sender_id to ADMIN user: {admin_name}")
        
    except Exception as e:
        print(f"❌ Backfill failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
