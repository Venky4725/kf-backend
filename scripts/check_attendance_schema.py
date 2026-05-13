#!/usr/bin/env python3
"""
Script to check the current attendance table schema and enum status.

This helps diagnose the attendance status enum issue.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Check attendance schema."""
    try:
        logger.info("=" * 60)
        logger.info("ATTENDANCE SCHEMA DIAGNOSTIC")
        logger.info("=" * 60)
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        
        # Check if attendance table exists
        logger.info("1. Checking if attendance table exists...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'attendance' not in tables:
            logger.error("❌ Attendance table does not exist!")
            return 1
        
        logger.info("✅ Attendance table exists")
        logger.info("")
        
        # Get column info
        logger.info("2. Attendance table columns:")
        columns = inspector.get_columns('attendance')
        for col in columns:
            logger.info(f"   - {col['name']}: {col['type']} (nullable={col['nullable']})")
        logger.info("")
        
        # Check for enum type
        logger.info("3. Checking for attendance_status enum type...")
        query = text("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_type 
                WHERE typname = 'attendance_status'
            );
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            enum_exists = result.scalar()
        
        if enum_exists:
            logger.info("✅ attendance_status enum type exists")
            
            # Get enum values
            query = text("""
                SELECT e.enumlabel
                FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'attendance_status'
                ORDER BY e.enumsortorder;
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query)
                values = [row[0] for row in result]
            
            logger.info(f"   Enum values: {', '.join(values)}")
            
            if 'LATE' in values:
                logger.info("   ✅ LATE is included")
            else:
                logger.warning("   ⚠️  LATE is MISSING - this is the problem!")
        else:
            logger.info("ℹ️  attendance_status enum type does not exist")
            logger.info("   (This is fine if the column uses VARCHAR/TEXT)")
        
        logger.info("")
        
        # Check actual column type
        logger.info("4. Checking attendance.status column type...")
        query = text("""
            SELECT 
                column_name,
                data_type,
                udt_name,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'attendance' 
            AND column_name = 'status';
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            row = result.fetchone()
        
        if row:
            logger.info(f"   Column: {row[0]}")
            logger.info(f"   Data type: {row[1]}")
            logger.info(f"   UDT name: {row[2]}")
            logger.info(f"   Max length: {row[3]}")
            
            if row[2] == 'attendance_status':
                logger.info("")
                logger.info("   ⚠️  Column is using attendance_status ENUM type")
                logger.info("   This means the enum MUST include LATE value")
                logger.info("")
                logger.info("   ACTION REQUIRED:")
                logger.info("   Run: python scripts/add_late_status_to_enum.py")
            else:
                logger.info("")
                logger.info("   ✅ Column is using flexible string type")
                logger.info("   No enum migration needed")
        
        logger.info("")
        
        # Check constraints
        logger.info("5. Checking constraints...")
        constraints = inspector.get_unique_constraints('attendance')
        if constraints:
            logger.info("   Unique constraints:")
            for constraint in constraints:
                logger.info(f"   - {constraint['name']}: {constraint['column_names']}")
        else:
            logger.info("   No unique constraints found")
        
        logger.info("")
        
        # Sample data
        logger.info("6. Sample attendance records (last 5)...")
        query = text("""
            SELECT id, user_id, day, status, created_at
            FROM attendance
            ORDER BY created_at DESC
            LIMIT 5;
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
        
        if rows:
            for row in rows:
                logger.info(f"   {row[2]} | {row[3]} | {row[0]}")
        else:
            logger.info("   No attendance records found")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("DIAGNOSTIC COMPLETE")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ DIAGNOSTIC FAILED!")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
