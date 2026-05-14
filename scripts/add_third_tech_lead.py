#!/usr/bin/env python3
"""
Add third_tech_lead_id column to batches table

This migration adds support for a third technical lead per batch.

Usage:
    python scripts/add_third_tech_lead.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine
from app.core.logger import get_logger

logger = get_logger(__name__)


def add_third_tech_lead_column():
    """Add third_tech_lead_id column to batches table."""
    logger.info("Adding third_tech_lead_id column to batches table...")
    
    try:
        with engine.begin() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='batches' AND column_name='third_tech_lead_id'
            """))
            
            if result.fetchone():
                logger.info("✅ third_tech_lead_id column already exists")
                return True
            
            # Add the column
            conn.execute(text("""
                ALTER TABLE batches 
                ADD COLUMN third_tech_lead_id UUID REFERENCES profiles(id)
            """))
            
            logger.info("✅ Successfully added third_tech_lead_id column")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to add third_tech_lead_id column: {e}")
        return False


def main():
    """Run the migration."""
    logger.info("=" * 60)
    logger.info("ADD THIRD TECH LEAD MIGRATION")
    logger.info("=" * 60)
    
    try:
        success = add_third_tech_lead_column()
        
        if success:
            logger.info("\n✅ MIGRATION COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            logger.error("\n❌ MIGRATION FAILED")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n❌ MIGRATION FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
