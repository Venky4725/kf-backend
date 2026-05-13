#!/usr/bin/env python3
"""
Script to fix tech lead batch assignments.

This script:
1. Finds tech leads who are assigned to batches (first_tech_lead_id or second_tech_lead_id)
   but don't have their profile.batch_id set
2. Updates their profile.batch_id to match their batch assignment
3. Validates the 2-tech-lead-per-batch limit
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.profile import Profile
from app.models.batch import Batch
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_mismatched_tech_leads(db: Session):
    """Find tech leads with batch assignment mismatches."""
    logger.info("=" * 60)
    logger.info("FINDING TECH LEAD BATCH ASSIGNMENT ISSUES")
    logger.info("=" * 60)
    logger.info("")
    
    # Find all batches with tech leads assigned
    batches = db.query(Batch).filter(
        or_(
            Batch.first_tech_lead_id.isnot(None),
            Batch.second_tech_lead_id.isnot(None)
        )
    ).all()
    
    logger.info(f"Found {len(batches)} batches with tech leads assigned")
    logger.info("")
    
    issues = []
    
    for batch in batches:
        logger.info(f"Checking batch: {batch.name} (ID: {batch.id})")
        
        # Check first tech lead
        if batch.first_tech_lead_id:
            tl1 = db.get(Profile, batch.first_tech_lead_id)
            if tl1:
                if tl1.batch_id != batch.id:
                    logger.warning(f"  ⚠️  First TL '{tl1.name}' has batch_id={tl1.batch_id}, should be {batch.id}")
                    issues.append({
                        'profile_id': tl1.id,
                        'profile_name': tl1.name,
                        'current_batch_id': tl1.batch_id,
                        'correct_batch_id': batch.id,
                        'batch_name': batch.name,
                        'position': 'first'
                    })
                else:
                    logger.info(f"  ✅ First TL '{tl1.name}' has correct batch_id")
            else:
                logger.error(f"  ❌ First TL ID {batch.first_tech_lead_id} not found!")
        
        # Check second tech lead
        if batch.second_tech_lead_id:
            tl2 = db.get(Profile, batch.second_tech_lead_id)
            if tl2:
                if tl2.batch_id != batch.id:
                    logger.warning(f"  ⚠️  Second TL '{tl2.name}' has batch_id={tl2.batch_id}, should be {batch.id}")
                    issues.append({
                        'profile_id': tl2.id,
                        'profile_name': tl2.name,
                        'current_batch_id': tl2.batch_id,
                        'correct_batch_id': batch.id,
                        'batch_name': batch.name,
                        'position': 'second'
                    })
                else:
                    logger.info(f"  ✅ Second TL '{tl2.name}' has correct batch_id")
            else:
                logger.error(f"  ❌ Second TL ID {batch.second_tech_lead_id} not found!")
        
        logger.info("")
    
    return issues


def check_tech_lead_limits(db: Session):
    """Check if any batch has more than 2 tech leads."""
    logger.info("=" * 60)
    logger.info("CHECKING TECH LEAD LIMITS")
    logger.info("=" * 60)
    logger.info("")
    
    batches = db.query(Batch).all()
    violations = []
    
    for batch in batches:
        # Count tech leads assigned via profile.batch_id
        tl_count = db.query(Profile).filter(
            Profile.batch_id == batch.id,
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True
        ).count()
        
        if tl_count > 2:
            logger.error(f"❌ Batch '{batch.name}' has {tl_count} tech leads (max 2)")
            violations.append({
                'batch_id': batch.id,
                'batch_name': batch.name,
                'tech_lead_count': tl_count
            })
        elif tl_count == 2:
            logger.info(f"✅ Batch '{batch.name}' has {tl_count} tech leads (OK)")
        elif tl_count == 1:
            logger.info(f"ℹ️  Batch '{batch.name}' has {tl_count} tech lead")
        else:
            logger.info(f"ℹ️  Batch '{batch.name}' has no tech leads")
    
    logger.info("")
    return violations


def fix_tech_lead_assignments(db: Session, issues: list):
    """Fix tech lead batch assignments."""
    if not issues:
        logger.info("=" * 60)
        logger.info("✅ NO ISSUES TO FIX")
        logger.info("=" * 60)
        logger.info("")
        return True
    
    logger.info("=" * 60)
    logger.info("FIXING TECH LEAD BATCH ASSIGNMENTS")
    logger.info("=" * 60)
    logger.info("")
    
    logger.info(f"Found {len(issues)} tech leads with incorrect batch_id")
    logger.info("")
    
    for issue in issues:
        logger.info(f"Fixing: {issue['profile_name']}")
        logger.info(f"  Current batch_id: {issue['current_batch_id']}")
        logger.info(f"  Correct batch_id: {issue['correct_batch_id']} ({issue['batch_name']})")
        logger.info(f"  Position: {issue['position']} tech lead")
    
    logger.info("")
    response = input("Apply these fixes? (yes/no): ").strip().lower()
    
    if response != 'yes':
        logger.info("Fixes cancelled by user")
        return False
    
    logger.info("")
    logger.info("Applying fixes...")
    logger.info("")
    
    for issue in issues:
        profile = db.get(Profile, issue['profile_id'])
        if profile:
            old_batch_id = profile.batch_id
            profile.batch_id = issue['correct_batch_id']
            logger.info(f"✅ Updated {profile.name}: batch_id {old_batch_id} -> {issue['correct_batch_id']}")
        else:
            logger.error(f"❌ Profile {issue['profile_id']} not found")
    
    db.commit()
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ FIXES APPLIED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info("")
    
    return True


def show_tech_lead_summary(db: Session):
    """Show summary of tech lead assignments."""
    logger.info("=" * 60)
    logger.info("TECH LEAD ASSIGNMENT SUMMARY")
    logger.info("=" * 60)
    logger.info("")
    
    # Get all tech leads
    tech_leads = db.query(Profile).filter(
        Profile.role == "TECHNICAL_LEAD",
        Profile.is_active == True
    ).all()
    
    logger.info(f"Total active tech leads: {len(tech_leads)}")
    logger.info("")
    
    assigned = 0
    unassigned = 0
    
    for tl in tech_leads:
        if tl.batch_id:
            batch = db.get(Batch, tl.batch_id)
            batch_name = batch.name if batch else "Unknown"
            logger.info(f"✅ {tl.name} -> {batch_name}")
            assigned += 1
        else:
            logger.info(f"⚠️  {tl.name} -> No batch assigned")
            unassigned += 1
    
    logger.info("")
    logger.info(f"Assigned: {assigned}")
    logger.info(f"Unassigned: {unassigned}")
    logger.info("")


def main():
    """Main function."""
    try:
        logger.info("Connecting to database...")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")
        logger.info("")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        db = Session(engine)
        
        # Find issues
        issues = find_mismatched_tech_leads(db)
        
        # Check limits
        violations = check_tech_lead_limits(db)
        
        if violations:
            logger.error("=" * 60)
            logger.error("❌ TECH LEAD LIMIT VIOLATIONS FOUND")
            logger.error("=" * 60)
            logger.error("")
            logger.error("Some batches have more than 2 tech leads!")
            logger.error("Please manually resolve these before proceeding.")
            logger.error("")
            return 1
        
        # Fix issues
        if issues:
            success = fix_tech_lead_assignments(db, issues)
            if not success:
                return 1
        
        # Show summary
        show_tech_lead_summary(db)
        
        logger.info("=" * 60)
        logger.info("✅ COMPLETE")
        logger.info("=" * 60)
        logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ SCRIPT FAILED")
        logger.error("=" * 60)
        logger.error("")
        logger.error(f"Error: {e}")
        logger.error("")
        return 1
    finally:
        if 'db' in locals():
            db.close()


if __name__ == "__main__":
    sys.exit(main())
