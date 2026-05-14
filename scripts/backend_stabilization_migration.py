#!/usr/bin/env python3
"""
Backend Stabilization Migration Script

This script ensures database integrity and adds missing columns/constraints.

Run this script to:
1. Add edited_at column to notifications table
2. Ensure attendance status enum includes LATE
3. Verify all foreign key constraints
4. Add missing indexes for performance
5. Validate data integrity

Usage:
    python scripts/backend_stabilization_migration.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.db.session import engine
from app.core.logger import get_logger

logger = get_logger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_enum_value_exists(enum_name: str, value: str) -> bool:
    """Check if an enum value exists."""
    with engine.connect() as conn:
        result = conn.execute(text(
            f"SELECT EXISTS(SELECT 1 FROM pg_enum WHERE enumlabel = '{value}' "
            f"AND enumtypid = (SELECT oid FROM pg_type WHERE typname = '{enum_name}'))"
        ))
        return result.scalar()


def add_notification_edited_at():
    """Add edited_at column to notifications table if it doesn't exist."""
    logger.info("Checking notifications.edited_at column...")
    
    if check_column_exists('notifications', 'edited_at'):
        logger.info("✅ notifications.edited_at already exists")
        return
    
    logger.info("Adding notifications.edited_at column...")
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE notifications ADD COLUMN edited_at TIMESTAMP WITH TIME ZONE"
        ))
    logger.info("✅ Added notifications.edited_at column")


def ensure_attendance_status_enum():
    """Ensure attendance status enum includes all required values."""
    logger.info("Checking attendance status enum...")
    
    # Check if enum type exists
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_type WHERE typname = 'attendance_status')"
        ))
        enum_exists = result.scalar()
    
    if not enum_exists:
        logger.info("Creating attendance_status enum...")
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TYPE attendance_status AS ENUM ('PRESENT', 'ABSENT', 'LEAVE', 'LATE')"
            ))
        logger.info("✅ Created attendance_status enum")
        return
    
    # Check if LATE value exists
    required_values = ['PRESENT', 'ABSENT', 'LEAVE', 'LATE']
    missing_values = []
    
    for value in required_values:
        if not check_enum_value_exists('attendance_status', value):
            missing_values.append(value)
    
    if not missing_values:
        logger.info("✅ All attendance status enum values exist")
        return
    
    # Add missing values
    for value in missing_values:
        logger.info(f"Adding '{value}' to attendance_status enum...")
        with engine.begin() as conn:
            conn.execute(text(
                f"ALTER TYPE attendance_status ADD VALUE IF NOT EXISTS '{value}'"
            ))
        logger.info(f"✅ Added '{value}' to attendance_status enum")


def verify_foreign_keys():
    """Verify all foreign key constraints are in place."""
    logger.info("Verifying foreign key constraints...")
    
    inspector = inspect(engine)
    
    # Check critical foreign keys
    critical_fks = [
        ('profiles', 'batch_id', 'batches'),
        ('batches', 'first_tech_lead_id', 'profiles'),
        ('batches', 'second_tech_lead_id', 'profiles'),
        ('attendance', 'user_id', 'profiles'),
        ('notifications', 'user_id', 'profiles'),
        ('notifications', 'sender_id', 'profiles'),
    ]
    
    for table, column, ref_table in critical_fks:
        fks = inspector.get_foreign_keys(table)
        fk_exists = any(
            column in fk['constrained_columns'] and ref_table in fk['referred_table']
            for fk in fks
        )
        
        if fk_exists:
            logger.info(f"✅ {table}.{column} -> {ref_table} FK exists")
        else:
            logger.warning(f"⚠️  {table}.{column} -> {ref_table} FK missing")


def add_performance_indexes():
    """Add indexes for common query patterns."""
    logger.info("Checking performance indexes...")
    
    indexes_to_create = [
        ("idx_profiles_email", "profiles", "email"),
        ("idx_profiles_role", "profiles", "role"),
        ("idx_profiles_batch_id", "profiles", "batch_id"),
        ("idx_attendance_user_day", "attendance", "user_id, day"),
        ("idx_attendance_day", "attendance", "day"),
        ("idx_notifications_user_id", "notifications", "user_id"),
        ("idx_notifications_sender_id", "notifications", "sender_id"),
    ]
    
    inspector = inspect(engine)
    
    for index_name, table_name, columns in indexes_to_create:
        # Check if index exists
        existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        
        if index_name in existing_indexes:
            logger.info(f"✅ Index {index_name} already exists")
            continue
        
        logger.info(f"Creating index {index_name} on {table_name}({columns})...")
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
                ))
            logger.info(f"✅ Created index {index_name}")
        except Exception as e:
            logger.warning(f"⚠️  Could not create index {index_name}: {e}")


def verify_unique_constraints():
    """Verify unique constraints are in place."""
    logger.info("Verifying unique constraints...")
    
    inspector = inspect(engine)
    
    # Check critical unique constraints
    critical_uniques = [
        ('profiles', 'email'),
        ('attendance', ['user_id', 'day']),  # Composite unique
    ]
    
    for table, columns in critical_uniques:
        if isinstance(columns, str):
            columns = [columns]
        
        unique_constraints = inspector.get_unique_constraints(table)
        constraint_exists = any(
            set(columns) == set(uc['column_names'])
            for uc in unique_constraints
        )
        
        if constraint_exists:
            logger.info(f"✅ {table}({', '.join(columns)}) unique constraint exists")
        else:
            logger.warning(f"⚠️  {table}({', '.join(columns)}) unique constraint missing")


def validate_data_integrity():
    """Validate data integrity across tables."""
    logger.info("Validating data integrity...")
    
    with engine.connect() as conn:
        # Check for orphaned profiles (batch_id references non-existent batch)
        result = conn.execute(text("""
            SELECT COUNT(*) FROM profiles p
            WHERE p.batch_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM batches b WHERE b.id = p.batch_id)
        """))
        orphaned_profiles = result.scalar()
        
        if orphaned_profiles > 0:
            logger.warning(f"⚠️  Found {orphaned_profiles} profiles with invalid batch_id")
        else:
            logger.info("✅ No orphaned profiles found")
        
        # Check for orphaned attendance records
        result = conn.execute(text("""
            SELECT COUNT(*) FROM attendance a
            WHERE NOT EXISTS (SELECT 1 FROM profiles p WHERE p.id = a.user_id)
        """))
        orphaned_attendance = result.scalar()
        
        if orphaned_attendance > 0:
            logger.warning(f"⚠️  Found {orphaned_attendance} attendance records with invalid user_id")
        else:
            logger.info("✅ No orphaned attendance records found")
        
        # Check for duplicate attendance records (should be prevented by unique constraint)
        result = conn.execute(text("""
            SELECT user_id, day, COUNT(*) as count
            FROM attendance
            GROUP BY user_id, day
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        
        if duplicates:
            logger.warning(f"⚠️  Found {len(duplicates)} duplicate attendance records")
            for user_id, day, count in duplicates:
                logger.warning(f"   - user_id={user_id}, day={day}, count={count}")
        else:
            logger.info("✅ No duplicate attendance records found")


def main():
    """Run all migration and validation steps."""
    logger.info("=" * 60)
    logger.info("BACKEND STABILIZATION MIGRATION")
    logger.info("=" * 60)
    
    try:
        # Step 1: Add missing columns
        logger.info("\n[STEP 1] Adding missing columns...")
        add_notification_edited_at()
        
        # Step 2: Ensure enums are correct
        logger.info("\n[STEP 2] Ensuring enum values...")
        ensure_attendance_status_enum()
        
        # Step 3: Verify foreign keys
        logger.info("\n[STEP 3] Verifying foreign keys...")
        verify_foreign_keys()
        
        # Step 4: Add performance indexes
        logger.info("\n[STEP 4] Adding performance indexes...")
        add_performance_indexes()
        
        # Step 5: Verify unique constraints
        logger.info("\n[STEP 5] Verifying unique constraints...")
        verify_unique_constraints()
        
        # Step 6: Validate data integrity
        logger.info("\n[STEP 6] Validating data integrity...")
        validate_data_integrity()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ MIGRATION FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
