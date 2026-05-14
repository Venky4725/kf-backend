#!/usr/bin/env python3
"""
Quick Health Check Script

Performs rapid health checks on the backend to ensure everything is working.

Usage:
    python scripts/quick_health_check.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.db.session import engine
from app.core.logger import get_logger

logger = get_logger(__name__)


def check_database_connection():
    """Check if database is accessible."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection: OK")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection: FAILED - {e}")
        return False


def check_tables_exist():
    """Check if all required tables exist."""
    required_tables = [
        'profiles',
        'batches',
        'attendance',
        'notifications',
        'tasks',
        'submissions',
        'evaluations',
        'audit_logs'
    ]
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    all_exist = True
    for table in required_tables:
        if table in existing_tables:
            logger.info(f"✅ Table '{table}': EXISTS")
        else:
            logger.error(f"❌ Table '{table}': MISSING")
            all_exist = False
    
    return all_exist


def check_critical_columns():
    """Check if critical columns exist."""
    checks = [
        ('profiles', 'email'),
        ('profiles', 'batch_id'),
        ('profiles', 'password_hash'),
        ('batches', 'first_tech_lead_id'),
        ('batches', 'second_tech_lead_id'),
        ('notifications', 'sender_id'),
        ('notifications', 'edited_at'),
        ('attendance', 'status'),
        ('attendance', 'day'),
    ]
    
    inspector = inspect(engine)
    all_exist = True
    
    for table, column in checks:
        try:
            columns = [col['name'] for col in inspector.get_columns(table)]
            if column in columns:
                logger.info(f"✅ Column '{table}.{column}': EXISTS")
            else:
                logger.error(f"❌ Column '{table}.{column}': MISSING")
                all_exist = False
        except Exception as e:
            logger.error(f"❌ Error checking '{table}.{column}': {e}")
            all_exist = False
    
    return all_exist


def check_enum_values():
    """Check if attendance_status enum has all required values."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'attendance_status')
                ORDER BY enumlabel
            """))
            enum_values = [row[0] for row in result]
        
        required_values = ['ABSENT', 'LATE', 'LEAVE', 'PRESENT']
        
        if set(enum_values) == set(required_values):
            logger.info(f"✅ Attendance status enum: OK ({', '.join(sorted(enum_values))})")
            return True
        else:
            missing = set(required_values) - set(enum_values)
            extra = set(enum_values) - set(required_values)
            if missing:
                logger.error(f"❌ Attendance status enum: MISSING VALUES - {missing}")
            if extra:
                logger.warning(f"⚠️  Attendance status enum: EXTRA VALUES - {extra}")
            return False
    except Exception as e:
        logger.error(f"❌ Attendance status enum check: FAILED - {e}")
        return False


def check_foreign_keys():
    """Check if critical foreign keys exist."""
    critical_fks = [
        ('profiles', 'batch_id'),
        ('batches', 'first_tech_lead_id'),
        ('batches', 'second_tech_lead_id'),
        ('attendance', 'user_id'),
        ('notifications', 'user_id'),
        ('notifications', 'sender_id'),
    ]
    
    inspector = inspect(engine)
    all_exist = True
    
    for table, column in critical_fks:
        try:
            fks = inspector.get_foreign_keys(table)
            fk_exists = any(column in fk['constrained_columns'] for fk in fks)
            
            if fk_exists:
                logger.info(f"✅ Foreign key '{table}.{column}': EXISTS")
            else:
                logger.warning(f"⚠️  Foreign key '{table}.{column}': MISSING (may be intentional)")
        except Exception as e:
            logger.error(f"❌ Error checking FK '{table}.{column}': {e}")
            all_exist = False
    
    return all_exist


def check_indexes():
    """Check if performance indexes exist."""
    recommended_indexes = [
        ('profiles', 'email'),
        ('profiles', 'role'),
        ('attendance', 'day'),
    ]
    
    inspector = inspect(engine)
    
    for table, column in recommended_indexes:
        try:
            indexes = inspector.get_indexes(table)
            index_exists = any(column in idx['column_names'] for idx in indexes)
            
            if index_exists:
                logger.info(f"✅ Index on '{table}.{column}': EXISTS")
            else:
                logger.warning(f"⚠️  Index on '{table}.{column}': MISSING (performance may be affected)")
        except Exception as e:
            logger.error(f"❌ Error checking index '{table}.{column}': {e}")


def check_data_integrity():
    """Quick data integrity checks."""
    try:
        with engine.connect() as conn:
            # Check for orphaned profiles
            result = conn.execute(text("""
                SELECT COUNT(*) FROM profiles p
                WHERE p.batch_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM batches b WHERE b.id = p.batch_id)
            """))
            orphaned_profiles = result.scalar()
            
            if orphaned_profiles == 0:
                logger.info("✅ Data integrity (profiles): OK")
            else:
                logger.warning(f"⚠️  Data integrity: {orphaned_profiles} profiles with invalid batch_id")
            
            # Check for duplicate attendance
            result = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT user_id, day, COUNT(*) as count
                    FROM attendance
                    GROUP BY user_id, day
                    HAVING COUNT(*) > 1
                ) duplicates
            """))
            duplicate_attendance = result.scalar()
            
            if duplicate_attendance == 0:
                logger.info("✅ Data integrity (attendance): OK")
            else:
                logger.warning(f"⚠️  Data integrity: {duplicate_attendance} duplicate attendance records")
            
            return orphaned_profiles == 0 and duplicate_attendance == 0
    except Exception as e:
        logger.error(f"❌ Data integrity check: FAILED - {e}")
        return False


def main():
    """Run all health checks."""
    logger.info("=" * 60)
    logger.info("BACKEND HEALTH CHECK")
    logger.info("=" * 60)
    
    checks = [
        ("Database Connection", check_database_connection),
        ("Required Tables", check_tables_exist),
        ("Critical Columns", check_critical_columns),
        ("Enum Values", check_enum_values),
        ("Foreign Keys", check_foreign_keys),
        ("Performance Indexes", check_indexes),
        ("Data Integrity", check_data_integrity),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        logger.info(f"\n[CHECK] {check_name}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"❌ {check_name}: EXCEPTION - {e}")
            results.append((check_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("HEALTH CHECK SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {check_name}")
    
    logger.info("=" * 60)
    logger.info(f"Result: {passed}/{total} checks passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("\n✅ ALL CHECKS PASSED - Backend is healthy!")
        sys.exit(0)
    else:
        logger.error(f"\n❌ {total - passed} CHECK(S) FAILED - Review errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
