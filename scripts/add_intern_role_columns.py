#!/usr/bin/env python3
"""
Migration script to add intern_role to profiles and role to tasks.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine
from app.core.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """Add intern_role to profiles and role to tasks."""
    print("Starting intern role columns migration...")
    
    with engine.begin() as conn:
        # Add intern_role to profiles
        print("Checking/Adding column profiles.intern_role...")
        conn.execute(text(
            "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS intern_role VARCHAR"
        ))
        
        # Add role to tasks
        print("Checking/Adding column tasks.role...")
        conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS role VARCHAR"
        ))
        
    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
