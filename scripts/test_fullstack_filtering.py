"""
Test script to verify FULLSTACK intern filtering fix.

This script tests:
1. Profile filtering by tech_stack=FULLSTACK
2. Profile filtering by tech_stack=AIML
3. Normalization of role values
4. Batch filtering combined with role filtering

Run with:
    python -m scripts.test_fullstack_filtering
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.profile import Profile
from app.models.batch import Batch
from app.utils.role_utils import normalize_role
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_normalize_role():
    """Test the normalize_role function with various inputs."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: normalize_role() Function")
    logger.info("="*60)
    
    test_cases = [
        ("Full Stack", "FULLSTACK"),
        ("FULLSTACK", "FULLSTACK"),
        ("full-stack", "FULLSTACK"),
        ("MERN Stack", "FULLSTACK"),
        ("Django Full Stack", "FULLSTACK"),
        ("AI/ML", "AIML"),
        ("AIML", "AIML"),
        ("AI-ML", "AIML"),
        ("Machine Learning", "AIML"),
        ("Data Science", "AIML"),
        ("", "GENERAL"),
        (None, "GENERAL"),
        ("GENERAL", "GENERAL"),
    ]
    
    all_passed = True
    for input_val, expected in test_cases:
        result = normalize_role(input_val)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result != expected:
            all_passed = False
        logger.info(f"{status} | Input: '{input_val}' -> Expected: '{expected}' | Got: '{result}'")
    
    return all_passed


def test_profile_data():
    """Check actual profile data in the database."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Profile Data Analysis")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # Get all interns
        interns = db.query(Profile).filter(Profile.role == "INTERN").all()
        logger.info(f"\nTotal Interns: {len(interns)}")
        
        # Group by tech_stack
        tech_stack_groups = {}
        for intern in interns:
            tech_stack = intern.tech_stack or "NULL"
            if tech_stack not in tech_stack_groups:
                tech_stack_groups[tech_stack] = []
            tech_stack_groups[tech_stack].append(intern)
        
        logger.info("\nInterns grouped by tech_stack:")
        for tech_stack, group in tech_stack_groups.items():
            logger.info(f"  {tech_stack}: {len(group)} interns")
            for intern in group[:3]:  # Show first 3
                logger.info(f"    - {intern.name} | intern_role: {intern.intern_role} | batch: {intern.batch_id}")
        
        # Group by intern_role
        intern_role_groups = {}
        for intern in interns:
            intern_role = intern.intern_role or "NULL"
            if intern_role not in intern_role_groups:
                intern_role_groups[intern_role] = []
            intern_role_groups[intern_role].append(intern)
        
        logger.info("\nInterns grouped by intern_role:")
        for intern_role, group in intern_role_groups.items():
            logger.info(f"  {intern_role}: {len(group)} interns")
        
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        db.close()


def test_filtering_logic():
    """Test the actual filtering logic used in profile service."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Filtering Logic Simulation")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # Get a batch to test with
        batch = db.query(Batch).first()
        if not batch:
            logger.warning("No batches found in database")
            return False
        
        logger.info(f"\nTesting with batch: {batch.name} (ID: {batch.id})")
        
        # Test 1: Filter by tech_stack=FULLSTACK (OLD WAY - should fail)
        logger.info("\n--- OLD METHOD (Raw tech_stack comparison) ---")
        query_old = db.query(Profile).filter(
            Profile.role == "INTERN",
            Profile.batch_id == batch.id,
            Profile.tech_stack.ilike("FULLSTACK")
        )
        results_old = query_old.all()
        logger.info(f"Results with tech_stack.ilike('FULLSTACK'): {len(results_old)} interns")
        for profile in results_old:
            logger.info(f"  - {profile.name} | tech_stack: {profile.tech_stack} | intern_role: {profile.intern_role}")
        
        # Test 2: Filter by intern_role=FULLSTACK (NEW WAY - should work)
        logger.info("\n--- NEW METHOD (Normalized intern_role) ---")
        normalized = normalize_role("FULLSTACK")
        query_new = db.query(Profile).filter(
            Profile.role == "INTERN",
            Profile.batch_id == batch.id,
            Profile.intern_role == normalized
        )
        results_new = query_new.all()
        logger.info(f"Results with intern_role == normalize_role('FULLSTACK'): {len(results_new)} interns")
        for profile in results_new:
            logger.info(f"  - {profile.name} | tech_stack: {profile.tech_stack} | intern_role: {profile.intern_role}")
        
        # Test 3: Same for AIML
        logger.info("\n--- AIML Filtering ---")
        normalized_aiml = normalize_role("AIML")
        query_aiml = db.query(Profile).filter(
            Profile.role == "INTERN",
            Profile.batch_id == batch.id,
            Profile.intern_role == normalized_aiml
        )
        results_aiml = query_aiml.all()
        logger.info(f"Results with intern_role == normalize_role('AIML'): {len(results_aiml)} interns")
        for profile in results_aiml:
            logger.info(f"  - {profile.name} | tech_stack: {profile.tech_stack} | intern_role: {profile.intern_role}")
        
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        db.close()


def test_batch_listing():
    """Test batch listing to verify 'All Batches' issue."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Batch Listing (Issue 2 Verification)")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        batches = db.query(Batch).all()
        logger.info(f"\nTotal Batches: {len(batches)}")
        
        for batch in batches:
            logger.info(f"\nBatch: {batch.name}")
            logger.info(f"  ID: {batch.id}")
            logger.info(f"  Tech Stack: {batch.tech_stack}")
            logger.info(f"  Start Date: {batch.start_date}")
            logger.info(f"  First TL: {batch.first_tech_lead_id}")
            logger.info(f"  Second TL: {batch.second_tech_lead_id}")
            logger.info(f"  Third TL: {batch.third_tech_lead_id}")
            
            # Count interns in this batch
            intern_count = db.query(func.count(Profile.id)).filter(
                Profile.role == "INTERN",
                Profile.batch_id == batch.id
            ).scalar()
            logger.info(f"  Interns: {intern_count}")
        
        # Check if "All Batches" exists anywhere
        all_batches_found = any("All Batches" in batch.name for batch in batches)
        if all_batches_found:
            logger.error("❌ FOUND 'All Batches' in batch names!")
            return False
        else:
            logger.info("\n✅ No 'All Batches' found in batch names (as expected)")
            return True
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        db.close()


def main():
    """Run all tests."""
    logger.info("\n" + "="*60)
    logger.info("FULLSTACK FILTERING FIX - TEST SUITE")
    logger.info("="*60)
    
    results = {
        "normalize_role": test_normalize_role(),
        "profile_data": test_profile_data(),
        "filtering_logic": test_filtering_logic(),
        "batch_listing": test_batch_listing(),
    }
    
    logger.info("\n" + "="*60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status} | {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED!")
    else:
        logger.info("\n⚠️ SOME TESTS FAILED - Review logs above")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
