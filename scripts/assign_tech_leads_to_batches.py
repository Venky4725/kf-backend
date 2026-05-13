#!/usr/bin/env python3
"""
Assign tech leads to batches safely.

This script helps assign tech leads who have batch_id=NULL to actual batches.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.profile import Profile
from app.models.batch import Batch
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Assign tech leads to batches."""
    try:
        logger.info("=" * 60)
        logger.info("ASSIGN TECH LEADS TO BATCHES")
        logger.info("=" * 60)
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        db = Session(engine)
        
        # Get tech leads without batch
        tech_leads = db.query(Profile).filter(
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True,
            Profile.batch_id == None
        ).all()
        
        if not tech_leads:
            logger.info("✅ All tech leads have batch assignments!")
            return 0
        
        logger.info(f"Found {len(tech_leads)} tech lead(s) without batch:")
        for tl in tech_leads:
            logger.info(f"  - {tl.name} ({tl.email})")
        
        logger.info("")
        
        # Get available batches
        batches = db.query(Batch).all()
        
        if not batches:
            logger.error("❌ No batches found! Create a batch first.")
            return 1
        
        logger.info(f"Available batches:")
        for i, batch in enumerate(batches, 1):
            # Count current tech leads
            tl_count = db.query(Profile).filter(
                Profile.batch_id == batch.id,
                Profile.role == "TECHNICAL_LEAD",
                Profile.is_active == True
            ).count()
            
            logger.info(f"  {i}. {batch.name} (Tech Stack: {batch.tech_stack}, Current TLs: {tl_count})")
        
        logger.info("")
        logger.info("Assignment Options:")
        logger.info("1. Auto-assign all tech leads to first batch")
        logger.info("2. Manual assignment (interactive)")
        logger.info("3. Cancel")
        logger.info("")
        
        choice = input("Choose option (1-3): ").strip()
        
        if choice == "1":
            # Auto-assign to first batch
            target_batch = batches[0]
            logger.info("")
            logger.info(f"Assigning all tech leads to: {target_batch.name}")
            logger.info("")
            
            for tl in tech_leads:
                tl.batch_id = target_batch.id
                logger.info(f"  ✅ Assigned {tl.name} to {target_batch.name}")
            
            db.commit()
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ ASSIGNMENT COMPLETE")
            logger.info("=" * 60)
            
        elif choice == "2":
            # Manual assignment
            logger.info("")
            for tl in tech_leads:
                logger.info(f"Assign {tl.name} to which batch?")
                for i, batch in enumerate(batches, 1):
                    logger.info(f"  {i}. {batch.name}")
                logger.info(f"  0. Skip")
                
                batch_choice = input("Choose batch (0-{}): ".format(len(batches))).strip()
                
                try:
                    batch_idx = int(batch_choice)
                    if batch_idx == 0:
                        logger.info(f"  Skipped {tl.name}")
                    elif 1 <= batch_idx <= len(batches):
                        target_batch = batches[batch_idx - 1]
                        tl.batch_id = target_batch.id
                        logger.info(f"  ✅ Assigned {tl.name} to {target_batch.name}")
                    else:
                        logger.warning(f"  Invalid choice, skipped {tl.name}")
                except ValueError:
                    logger.warning(f"  Invalid input, skipped {tl.name}")
                
                logger.info("")
            
            db.commit()
            logger.info("=" * 60)
            logger.info("✅ ASSIGNMENT COMPLETE")
            logger.info("=" * 60)
            
        else:
            logger.info("Assignment cancelled")
            return 0
        
        # Show final status
        logger.info("")
        logger.info("Final Status:")
        
        for batch in batches:
            tls = db.query(Profile).filter(
                Profile.batch_id == batch.id,
                Profile.role == "TECHNICAL_LEAD",
                Profile.is_active == True
            ).all()
            
            if tls:
                logger.info(f"  {batch.name}:")
                for tl in tls:
                    logger.info(f"    - {tl.name}")
        
        logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ ASSIGNMENT FAILED")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        if 'db' in locals():
            db.rollback()
        return 1
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    sys.exit(main())
