#!/usr/bin/env python3
"""
Check database constraints on profiles table.

Verifies that multiple TECHNICAL_LEAD users can be assigned to the same batch.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Check profile constraints."""
    try:
        logger.info("=" * 60)
        logger.info("PROFILE CONSTRAINTS CHECK")
        logger.info("=" * 60)
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        inspector = inspect(engine)
        
        # Check unique constraints
        logger.info("1. Checking unique constraints on profiles table...")
        unique_constraints = inspector.get_unique_constraints('profiles')
        
        if unique_constraints:
            logger.info(f"Found {len(unique_constraints)} unique constraint(s):")
            for constraint in unique_constraints:
                columns = ', '.join(constraint['column_names'])
                logger.info(f"  - {constraint['name']}: ({columns})")
                
                # Check if batch_id is in any unique constraint
                if 'batch_id' in constraint['column_names']:
                    logger.error(f"  ❌ PROBLEM: batch_id is in unique constraint!")
                    logger.error(f"     This prevents multiple tech leads per batch")
        else:
            logger.info("  ✅ No unique constraints found (besides primary key)")
        
        logger.info("")
        
        # Check indexes
        logger.info("2. Checking indexes on profiles table...")
        indexes = inspector.get_indexes('profiles')
        
        if indexes:
            logger.info(f"Found {len(indexes)} index(es):")
            for index in indexes:
                columns = ', '.join(index['column_names'])
                unique = "UNIQUE" if index.get('unique') else "NON-UNIQUE"
                logger.info(f"  - {index['name']}: ({columns}) [{unique}]")
                
                # Check if batch_id is in any unique index
                if index.get('unique') and 'batch_id' in index['column_names']:
                    logger.error(f"  ❌ PROBLEM: batch_id is in unique index!")
                    logger.error(f"     This prevents multiple tech leads per batch")
        else:
            logger.info("  No indexes found")
        
        logger.info("")
        
        # Check foreign keys
        logger.info("3. Checking foreign keys on profiles table...")
        foreign_keys = inspector.get_foreign_keys('profiles')
        
        if foreign_keys:
            logger.info(f"Found {len(foreign_keys)} foreign key(s):")
            for fk in foreign_keys:
                columns = ', '.join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_columns = ', '.join(fk['referred_columns'])
                logger.info(f"  - {fk['name']}: {columns} -> {ref_table}({ref_columns})")
        else:
            logger.info("  No foreign keys found")
        
        logger.info("")
        
        # Test query: Count tech leads per batch
        logger.info("4. Checking current tech lead distribution...")
        query = text("""
            SELECT 
                b.name as batch_name,
                COUNT(p.id) as tech_lead_count,
                STRING_AGG(p.name, ', ') as tech_leads
            FROM batches b
            LEFT JOIN profiles p ON p.batch_id = b.id AND p.role = 'TECHNICAL_LEAD' AND p.is_active = true
            GROUP BY b.id, b.name
            HAVING COUNT(p.id) > 0
            ORDER BY tech_lead_count DESC, b.name;
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            rows = result.fetchall()
        
        if rows:
            logger.info(f"Found {len(rows)} batch(es) with tech leads:")
            for batch_name, count, tech_leads in rows:
                if count > 2:
                    logger.warning(f"  ⚠️  {batch_name}: {count} tech leads ({tech_leads})")
                elif count == 2:
                    logger.info(f"  ✅ {batch_name}: {count} tech leads ({tech_leads})")
                else:
                    logger.info(f"  ℹ️  {batch_name}: {count} tech lead ({tech_leads})")
        else:
            logger.info("  No batches with tech leads found")
        
        logger.info("")
        
        # Summary
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info("")
        
        # Check for blocking constraints
        has_blocking_constraint = False
        
        for constraint in unique_constraints:
            if 'batch_id' in constraint['column_names']:
                has_blocking_constraint = True
                logger.error("❌ BLOCKING CONSTRAINT FOUND")
                logger.error(f"   Constraint: {constraint['name']}")
                logger.error(f"   Columns: {', '.join(constraint['column_names'])}")
                logger.error("")
                logger.error("   This constraint prevents multiple tech leads per batch!")
                logger.error("")
                logger.error("   To fix, run:")
                logger.error(f"   ALTER TABLE profiles DROP CONSTRAINT {constraint['name']};")
                logger.error("")
        
        for index in indexes:
            if index.get('unique') and 'batch_id' in index['column_names']:
                has_blocking_constraint = True
                logger.error("❌ BLOCKING INDEX FOUND")
                logger.error(f"   Index: {index['name']}")
                logger.error(f"   Columns: {', '.join(index['column_names'])}")
                logger.error("")
                logger.error("   This index prevents multiple tech leads per batch!")
                logger.error("")
                logger.error("   To fix, run:")
                logger.error(f"   DROP INDEX {index['name']};")
                logger.error("")
        
        if not has_blocking_constraint:
            logger.info("✅ NO BLOCKING CONSTRAINTS FOUND")
            logger.info("")
            logger.info("Multiple tech leads can be assigned to the same batch!")
            logger.info("")
        
        return 0 if not has_blocking_constraint else 1
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ CHECK FAILED")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
