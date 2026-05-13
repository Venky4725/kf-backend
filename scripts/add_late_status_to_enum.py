#!/usr/bin/env python3
"""
Migration script to add 'LATE' status to attendance_status enum.

This script fixes the production issue where attendance creation fails with:
    sqlalchemy.exc.DataError: invalid input value for enum attendance_status: "LATE"

The script:
1. Checks if attendance_status enum exists
2. Checks current enum values
3. Adds 'LATE' value if not present
4. Verifies the migration

Usage:
    python scripts/add_late_status_to_enum.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_enum_exists(engine):
    """Check if attendance_status enum type exists."""
    query = text("""
        SELECT EXISTS (
            SELECT 1 
            FROM pg_type 
            WHERE typname = 'attendance_status'
        );
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        exists = result.scalar()
    
    return exists


def get_enum_values(engine):
    """Get current values of attendance_status enum."""
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
    
    return values


def add_late_to_enum(engine):
    """Add LATE value to attendance_status enum if not present."""
    
    logger.info("=" * 60)
    logger.info("ATTENDANCE STATUS ENUM MIGRATION")
    logger.info("=" * 60)
    logger.info("")
    
    # Check if enum exists
    logger.info("Step 1: Checking if attendance_status enum exists...")
    enum_exists = check_enum_exists(engine)
    
    if not enum_exists:
        logger.warning("⚠️  attendance_status enum does not exist!")
        logger.info("Creating attendance_status enum with all values...")
        
        # Create the enum with all values
        create_query = text("""
            CREATE TYPE attendance_status AS ENUM ('PRESENT', 'ABSENT', 'LEAVE', 'LATE');
        """)
        
        with engine.begin() as conn:
            conn.execute(create_query)
        
        logger.info("✅ Created attendance_status enum with values: PRESENT, ABSENT, LEAVE, LATE")
        logger.info("")
        return True
    
    logger.info("✅ attendance_status enum exists")
    logger.info("")
    
    # Get current enum values
    logger.info("Step 2: Checking current enum values...")
    current_values = get_enum_values(engine)
    logger.info(f"Current values: {', '.join(current_values)}")
    logger.info("")
    
    # Check if LATE already exists
    if 'LATE' in current_values:
        logger.info("✅ LATE value already exists in enum")
        logger.info("No migration needed!")
        logger.info("")
        return True
    
    # Add LATE to enum
    logger.info("Step 3: Adding LATE value to enum...")
    
    # PostgreSQL 9.1+ supports ALTER TYPE ... ADD VALUE
    add_query = text("""
        ALTER TYPE attendance_status ADD VALUE IF NOT EXISTS 'LATE';
    """)
    
    try:
        with engine.begin() as conn:
            conn.execute(add_query)
        
        logger.info("✅ Successfully added LATE to attendance_status enum")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Failed to add LATE value: {e}")
        logger.info("")
        return False
    
    # Verify the change
    logger.info("Step 4: Verifying migration...")
    updated_values = get_enum_values(engine)
    logger.info(f"Updated values: {', '.join(updated_values)}")
    logger.info("")
    
    if 'LATE' in updated_values:
        logger.info("=" * 60)
        logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("The attendance_status enum now includes:")
        for value in updated_values:
            logger.info(f"  - {value}")
        logger.info("")
        logger.info("You can now create attendance records with status='LATE'")
        logger.info("")
        return True
    else:
        logger.error("=" * 60)
        logger.error("❌ MIGRATION VERIFICATION FAILED!")
        logger.error("=" * 60)
        logger.error("")
        logger.error("LATE value was not found in enum after migration")
        logger.error("")
        return False


def check_attendance_table_uses_enum(engine):
    """Check if attendance table uses the enum type."""
    query = text("""
        SELECT 
            column_name,
            data_type,
            udt_name
        FROM information_schema.columns
        WHERE table_name = 'attendance' 
        AND column_name = 'status';
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        row = result.fetchone()
    
    if row:
        logger.info(f"Attendance.status column info:")
        logger.info(f"  - Column: {row[0]}")
        logger.info(f"  - Data type: {row[1]}")
        logger.info(f"  - UDT name: {row[2]}")
        logger.info("")
        
        # Check if it's using the enum
        if row[2] == 'attendance_status':
            logger.info("✅ Attendance table is using attendance_status enum")
            return True
        else:
            logger.warning(f"⚠️  Attendance table is using {row[1]} type, not enum")
            logger.info("This is actually fine - the column can accept any string value")
            return False
    else:
        logger.warning("⚠️  Could not find attendance.status column")
        return False


def main():
    """Main migration function."""
    try:
        logger.info("Connecting to database...")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")  # Hide credentials
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        
        # Check table structure
        check_attendance_table_uses_enum(engine)
        
        # Run migration
        success = add_late_to_enum(engine)
        
        if success:
            logger.info("=" * 60)
            logger.info("NEXT STEPS")
            logger.info("=" * 60)
            logger.info("")
            logger.info("1. Restart your FastAPI application")
            logger.info("2. Test attendance creation with status='LATE'")
            logger.info("3. Verify analytics endpoints include LATE counts")
            logger.info("")
            return 0
        else:
            return 1
            
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ MIGRATION FAILED!")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Please check:")
        logger.error("1. Database connection settings in .env")
        logger.error("2. Database is running and accessible")
        logger.error("3. User has ALTER TYPE permissions")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
