#!/usr/bin/env python3
"""
Migration script to add sender_id column to notifications table.

This script adds the sender_id column to track who sent each notification.

Usage:
    python scripts/migrate_notifications_sender.py
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.db.session import SessionLocal


def migrate():
    """Add sender_id column to notifications table"""
    db = SessionLocal()
    
    try:
        print("Starting migration: Adding sender_id to notifications table...")
        
        # Add sender_id column
        db.execute(text("""
            ALTER TABLE notifications 
            ADD COLUMN IF NOT EXISTS sender_id UUID REFERENCES profiles(id);
        """))
        
        db.commit()
        print("✅ Migration completed successfully!")
        print("   - Added sender_id column to notifications table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
