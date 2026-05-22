#!/usr/bin/env python3
"""
Migration script to add missing columns to tasks table for bulk creation support.
Columns: priority, status, created_by
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


def migrate():
    """Add missing columns to tasks table."""
    logger.info("Starting tasks table migration...")
    
    columns_to_add = [
        ("priority", "VARCHAR", "'MEDIUM'"),
        ("status", "VARCHAR", "'OPEN'"),
        ("created_by", "UUID", "NULL"),
    ]
    
    with engine.begin() as conn:
        for col_name, col_type, default_val in columns_to_add:
            if check_column_exists('tasks', col_name):
                logger.info(f"✅ Column tasks.{col_name} already exists")
            else:
                logger.info(f"Adding column tasks.{col_name}...")
                conn.execute(text(
                    f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"
                ))
                if default_val != "NULL":
                    conn.execute(text(
                        f"UPDATE tasks SET {col_name} = {default_val} WHERE {col_name} IS NULL"
                    ))
                logger.info(f"✅ Added column tasks.{col_name}")

    # Add foreign key for created_by
    logger.info("Checking foreign key for created_by...")
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys('tasks')
    fk_exists = any(
        'created_by' in fk['constrained_columns'] and 'profiles' in fk['referred_table']
        for fk in fks
    )
    
    if fk_exists:
        logger.info("✅ Foreign key tasks.created_by -> profiles.id already exists")
    else:
        logger.info("Adding foreign key tasks.created_by -> profiles.id...")
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE tasks ADD CONSTRAINT fk_tasks_created_by "
                    "FOREIGN KEY (created_by) REFERENCES profiles(id)"
                ))
            logger.info("✅ Added foreign key tasks.created_by")
        except Exception as e:
            logger.warning(f"⚠️  Could not add foreign key: {e}")

    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
