#!/usr/bin/env python3
"""
Migration script to add roadmap columns to tasks table.
Columns: task_type, roadmap_entries
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
    logger.info("Starting tasks roadmap columns migration...")
    
    # Using JSONB for roadmap_entries as requested for PostgreSQL
    columns_to_add = [
        ("task_type", "VARCHAR", "'single'"),
        ("roadmap_entries", "JSONB", "'[]'"),
    ]
    
    with engine.begin() as conn:
        for col_name, col_type, default_val in columns_to_add:
            logger.info(f"Checking/Adding column tasks.{col_name}...")
            # PostgreSQL supports ADD COLUMN IF NOT EXISTS
            conn.execute(text(
                f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default_val}"
            ))
            logger.info(f"✅ Processed column tasks.{col_name}")

    logger.info("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
