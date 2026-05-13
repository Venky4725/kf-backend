#!/usr/bin/env python3
"""
Diagnose the 409 error when updating tech lead profiles.

This script:
1. Shows all tech leads and their batch_id status
2. Shows all batches
3. Attempts to identify the conflict
4. Provides fix recommendations
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.profile import Profile
from app.models.batch import Batch
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Diagnose the issue."""
    try:
        logger.info("=" * 60)
        logger.info("TECH LEAD BATCH ASSIGNMENT DIAGNOSIS")
        logger.info("=" * 60)
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        db = Session(engine)
        
        # Get all tech leads
        logger.info("1. Tech Leads in Database:")
        tech_leads = db.query(Profile).filter(
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True
        ).all()
        
        if not tech_leads:
            logger.warning("No tech leads found!")
            return 1
        
        for tl in tech_leads:
            batch_status = f"batch_id={tl.batch_id}" if tl.batch_id else "❌ NO BATCH"
            logger.info(f"  - {tl.name} ({tl.email})")
            logger.info(f"    ID: {tl.id}")
            logger.info(f"    {batch_status}")
            
            if tl.batch_id:
                batch = db.get(Batch, tl.batch_id)
                if batch:
                    logger.info(f"    Batch: {batch.name}")
                else:
                    logger.error(f"    ⚠️  Batch {tl.batch_id} NOT FOUND!")
        
        logger.info("")
        
        # Get all batches
        logger.info("2. Batches in Database:")
        batches = db.query(Batch).all()
        
        if not batches:
            logger.warning("No batches found!")
            return 1
        
        for batch in batches:
            logger.info(f"  - {batch.name}")
            logger.info(f"    ID: {batch.id}")
            logger.info(f"    Tech Stack: {batch.tech_stack}")
            logger.info(f"    Start Date: {batch.start_date}")
            
            # Count tech leads in this batch
            tl_count = db.query(Profile).filter(
                Profile.batch_id == batch.id,
                Profile.role == "TECHNICAL_LEAD",
                Profile.is_active == True
            ).count()
            logger.info(f"    Tech Leads: {tl_count}")
            
            # Show legacy fields
            if batch.first_tech_lead_id:
                first_tl = db.get(Profile, batch.first_tech_lead_id)
                if first_tl:
                    logger.info(f"    Legacy first_tech_lead_id: {first_tl.name}")
                else:
                    logger.warning(f"    Legacy first_tech_lead_id: {batch.first_tech_lead_id} (NOT FOUND)")
            
            if batch.second_tech_lead_id:
                second_tl = db.get(Profile, batch.second_tech_lead_id)
                if second_tl:
                    logger.info(f"    Legacy second_tech_lead_id: {second_tl.name}")
                else:
                    logger.warning(f"    Legacy second_tech_lead_id: {batch.second_tech_lead_id} (NOT FOUND)")
        
        logger.info("")
        
        # Check for constraints
        logger.info("3. Checking Database Constraints:")
        
        # Check unique constraints
        query = text("""
            SELECT 
                conname as constraint_name,
                pg_get_constraintdef(c.oid) as constraint_def
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE conrelid = 'profiles'::regclass
            AND contype = 'u';
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            constraints = result.fetchall()
        
        if constraints:
            for name, definition in constraints:
                logger.info(f"  - {name}: {definition}")
                if 'batch_id' in definition.lower():
                    logger.error(f"    ⚠️  This constraint blocks multiple tech leads per batch!")
        else:
            logger.info("  ✅ No unique constraints on profiles table")
        
        logger.info("")
        
        # Check for duplicate emails
        logger.info("4. Checking for Duplicate Emails:")
        query = text("""
            SELECT email, COUNT(*) as count
            FROM profiles
            GROUP BY email
            HAVING COUNT(*) > 1;
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            duplicates = result.fetchall()
        
        if duplicates:
            logger.error("Found duplicate emails:")
            for email, count in duplicates:
                logger.error(f"  - {email}: {count} profiles")
        else:
            logger.info("  ✅ No duplicate emails")
        
        logger.info("")
        
        # Recommendations
        logger.info("=" * 60)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 60)
        logger.info("")
        
        tech_leads_without_batch = [tl for tl in tech_leads if tl.batch_id is None]
        
        if tech_leads_without_batch:
            logger.warning(f"Found {len(tech_leads_without_batch)} tech lead(s) without batch_id:")
            for tl in tech_leads_without_batch:
                logger.warning(f"  - {tl.name} ({tl.email})")
            
            logger.info("")
            logger.info("To fix, you can:")
            logger.info("1. Assign them to a batch via frontend")
            logger.info("2. Run SQL update:")
            logger.info("")
            
            if batches:
                logger.info(f"   UPDATE profiles")
                logger.info(f"   SET batch_id = '{batches[0].id}'")
                logger.info(f"   WHERE id = '{tech_leads_without_batch[0].id}';")
            
            logger.info("")
        
        # Check for 409 conflict causes
        logger.info("5. Checking for 409 Conflict Causes:")
        
        # Try to simulate the update
        if tech_leads_without_batch and batches:
            tl = tech_leads_without_batch[0]
            batch = batches[0]
            
            logger.info(f"Simulating: Assign {tl.name} to {batch.name}")
            
            try:
                # Check if email would conflict
                existing = db.query(Profile).filter(
                    Profile.email == tl.email,
                    Profile.id != tl.id
                ).first()
                
                if existing:
                    logger.error(f"  ❌ Email conflict: {tl.email} already used by {existing.name}")
                else:
                    logger.info(f"  ✅ No email conflict")
                
                # Check if batch exists
                if db.get(Batch, batch.id):
                    logger.info(f"  ✅ Batch exists")
                else:
                    logger.error(f"  ❌ Batch not found")
                
            except Exception as e:
                logger.error(f"  ❌ Error: {e}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("DIAGNOSIS COMPLETE")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ DIAGNOSIS FAILED")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    sys.exit(main())
