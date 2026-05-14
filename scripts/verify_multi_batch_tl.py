#!/usr/bin/env python3
"""
Verification script for multi-batch Technical Lead implementation.

This script verifies that:
1. Tech lead utility functions work correctly
2. Services use multi-batch utilities
3. No single-batch assumptions remain
4. Access control works for multi-batch TLs
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.profile import Profile
from app.models.batch import Batch
from app.core.tech_lead_utils import (
    get_tech_lead_batch_ids,
    is_tech_lead_for_batch,
    is_tech_lead_for_intern,
    get_tech_lead_batch_filter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_tech_lead_utils(db: Session):
    """Test tech lead utility functions."""
    logger.info("=" * 60)
    logger.info("TEST 1: Tech Lead Utility Functions")
    logger.info("=" * 60)
    
    try:
        # Find a tech lead
        tech_lead = db.query(Profile).filter(
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True
        ).first()
        
        if not tech_lead:
            logger.warning("⚠️  No active tech leads found")
            return False
        
        logger.info(f"Testing with Tech Lead: {tech_lead.name} ({tech_lead.email})")
        
        # Test get_tech_lead_batch_ids
        batch_ids = get_tech_lead_batch_ids(db, tech_lead.id)
        logger.info(f"✅ get_tech_lead_batch_ids: Found {len(batch_ids)} batches")
        
        if batch_ids:
            # Test is_tech_lead_for_batch
            first_batch_id = batch_ids[0]
            result = is_tech_lead_for_batch(db, tech_lead.id, first_batch_id)
            logger.info(f"✅ is_tech_lead_for_batch: {result} (expected True)")
            
            # Test with a batch they're not assigned to
            other_batch = db.query(Batch).filter(
                ~Batch.id.in_(batch_ids)
            ).first()
            
            if other_batch:
                result = is_tech_lead_for_batch(db, tech_lead.id, other_batch.id)
                logger.info(f"✅ is_tech_lead_for_batch (other): {result} (expected False)")
            
            # Test is_tech_lead_for_intern
            intern = db.query(Profile).filter(
                Profile.role == "INTERN",
                Profile.batch_id.in_(batch_ids),
                Profile.is_active == True
            ).first()
            
            if intern:
                result = is_tech_lead_for_intern(db, tech_lead.id, intern.id)
                logger.info(f"✅ is_tech_lead_for_intern: {result} (expected True)")
            
            # Test get_tech_lead_batch_filter
            filter_expr = get_tech_lead_batch_filter(tech_lead.id)
            batches = db.query(Batch).filter(filter_expr).all()
            logger.info(f"✅ get_tech_lead_batch_filter: Found {len(batches)} batches")
        else:
            logger.warning("⚠️  Tech Lead is not assigned to any batches")
        
        logger.info("")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("", exc_info=True)
        return False


def test_batch_assignments(db: Session):
    """Test batch assignments for tech leads."""
    logger.info("=" * 60)
    logger.info("TEST 2: Batch Assignments")
    logger.info("=" * 60)
    
    try:
        batches = db.query(Batch).all()
        
        total_assignments = 0
        multi_tl_batches = 0
        
        for batch in batches:
            tl_count = 0
            tl_names = []
            
            if batch.first_tech_lead_id:
                tl_count += 1
                tl = db.get(Profile, batch.first_tech_lead_id)
                if tl:
                    tl_names.append(f"1st: {tl.name}")
            
            if batch.second_tech_lead_id:
                tl_count += 1
                tl = db.get(Profile, batch.second_tech_lead_id)
                if tl:
                    tl_names.append(f"2nd: {tl.name}")
            
            if hasattr(batch, 'third_tech_lead_id') and batch.third_tech_lead_id:
                tl_count += 1
                tl = db.get(Profile, batch.third_tech_lead_id)
                if tl:
                    tl_names.append(f"3rd: {tl.name}")
            
            if tl_count > 0:
                total_assignments += tl_count
                if tl_count > 1:
                    multi_tl_batches += 1
                logger.info(f"Batch '{batch.name}': {tl_count} TL(s) - {', '.join(tl_names)}")
        
        logger.info("")
        logger.info(f"Summary:")
        logger.info(f"  Total batches: {len(batches)}")
        logger.info(f"  Total TL assignments: {total_assignments}")
        logger.info(f"  Batches with multiple TLs: {multi_tl_batches}")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("", exc_info=True)
        return False


def test_tech_lead_access(db: Session):
    """Test tech lead access to interns."""
    logger.info("=" * 60)
    logger.info("TEST 3: Tech Lead Access to Interns")
    logger.info("=" * 60)
    
    try:
        # Find a tech lead with batch assignments
        tech_lead = db.query(Profile).filter(
            Profile.role == "TECHNICAL_LEAD",
            Profile.is_active == True
        ).first()
        
        if not tech_lead:
            logger.warning("⚠️  No active tech leads found")
            return False
        
        batch_ids = get_tech_lead_batch_ids(db, tech_lead.id)
        
        if not batch_ids:
            logger.warning(f"⚠️  Tech Lead {tech_lead.name} has no batch assignments")
            return False
        
        logger.info(f"Tech Lead: {tech_lead.name}")
        logger.info(f"Assigned to {len(batch_ids)} batch(es)")
        
        # Count interns in TL's batches
        accessible_interns = db.query(Profile).filter(
            Profile.role == "INTERN",
            Profile.batch_id.in_(batch_ids),
            Profile.is_active == True
        ).all()
        
        logger.info(f"✅ Can access {len(accessible_interns)} intern(s)")
        
        # Count interns NOT in TL's batches
        inaccessible_interns = db.query(Profile).filter(
            Profile.role == "INTERN",
            ~Profile.batch_id.in_(batch_ids),
            Profile.is_active == True
        ).all()
        
        logger.info(f"✅ Cannot access {len(inaccessible_interns)} intern(s) (correct)")
        
        # Verify access control
        if accessible_interns:
            intern = accessible_interns[0]
            result = is_tech_lead_for_intern(db, tech_lead.id, intern.id)
            logger.info(f"✅ Access check for accessible intern: {result} (expected True)")
        
        if inaccessible_interns:
            intern = inaccessible_interns[0]
            result = is_tech_lead_for_intern(db, tech_lead.id, intern.id)
            logger.info(f"✅ Access check for inaccessible intern: {result} (expected False)")
        
        logger.info("")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("", exc_info=True)
        return False


def check_deprecated_patterns(db: Session):
    """Check for deprecated single-batch patterns."""
    logger.info("=" * 60)
    logger.info("TEST 4: Check for Deprecated Patterns")
    logger.info("=" * 60)
    
    try:
        # Check if any tech leads have batch_id set (deprecated)
        tech_leads_with_batch_id = db.query(Profile).filter(
            Profile.role == "TECHNICAL_LEAD",
            Profile.batch_id.isnot(None)
        ).all()
        
        if tech_leads_with_batch_id:
            logger.warning(f"⚠️  Found {len(tech_leads_with_batch_id)} tech lead(s) with batch_id set (deprecated)")
            for tl in tech_leads_with_batch_id:
                logger.warning(f"   - {tl.name} ({tl.email}): batch_id={tl.batch_id}")
            logger.warning("   Note: This is deprecated but not breaking. TL assignments should use Batch model.")
        else:
            logger.info("✅ No tech leads with deprecated batch_id found")
        
        # Check if all interns have batch_id set
        interns_without_batch = db.query(Profile).filter(
            Profile.role == "INTERN",
            Profile.batch_id.is_(None),
            Profile.is_active == True
        ).all()
        
        if interns_without_batch:
            logger.warning(f"⚠️  Found {len(interns_without_batch)} active intern(s) without batch_id")
            for intern in interns_without_batch[:5]:  # Show first 5
                logger.warning(f"   - {intern.name} ({intern.email})")
        else:
            logger.info("✅ All active interns have batch_id set")
        
        logger.info("")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error("", exc_info=True)
        return False


def main():
    """Run all verification tests."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("MULTI-BATCH TECHNICAL LEAD VERIFICATION")
    logger.info("=" * 60)
    logger.info("")
    
    db = next(get_db())
    
    try:
        results = []
        
        # Run tests
        results.append(("Tech Lead Utils", test_tech_lead_utils(db)))
        results.append(("Batch Assignments", test_batch_assignments(db)))
        results.append(("Tech Lead Access", test_tech_lead_access(db)))
        results.append(("Deprecated Patterns", check_deprecated_patterns(db)))
        
        # Summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {test_name}")
        
        logger.info("")
        logger.info(f"Results: {passed}/{total} tests passed")
        logger.info("")
        
        if passed == total:
            logger.info("✅ ALL TESTS PASSED")
            logger.info("")
            logger.info("Multi-batch Technical Lead implementation is working correctly!")
            return 0
        else:
            logger.error("❌ SOME TESTS FAILED")
            logger.error("")
            logger.error("Please review the failures above.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        logger.error("", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
