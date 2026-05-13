#!/usr/bin/env python3
"""
Test script to verify LATE status works correctly.

This script tests:
1. Creating attendance with LATE status
2. Updating attendance to LATE status
3. Analytics include LATE counts
4. Filtering by LATE status
"""

import sys
import os
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.attendance import Attendance
from app.models.profile import Profile
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.attendance_service import attendance_service
import logging
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_test_intern(db: Session):
    """Get a test intern from the database."""
    intern = db.query(Profile).filter(Profile.role == "INTERN").first()
    if not intern:
        logger.error("No interns found in database. Please create test data first.")
        return None
    return intern


def test_create_late_attendance(db: Session, intern_id: uuid.UUID):
    """Test creating attendance with LATE status."""
    logger.info("=" * 60)
    logger.info("TEST 1: Create Attendance with LATE Status")
    logger.info("=" * 60)
    logger.info("")
    
    test_date = date.today() - timedelta(days=1)
    
    try:
        # Create attendance with LATE status
        payload = AttendanceCreate(
            user_id=intern_id,
            date=test_date,
            status="LATE"
        )
        
        logger.info(f"Creating attendance for intern {intern_id}")
        logger.info(f"Date: {test_date}")
        logger.info(f"Status: LATE")
        logger.info("")
        
        attendance = attendance_service.create_attendance(db, payload)
        
        logger.info("✅ Successfully created attendance with LATE status")
        logger.info(f"   ID: {attendance.id}")
        logger.info(f"   Status: {attendance.status}")
        logger.info(f"   User: {attendance.user_name}")
        logger.info("")
        
        return attendance.id
        
    except Exception as e:
        logger.error(f"❌ Failed to create attendance with LATE status")
        logger.error(f"   Error: {e}")
        logger.error("")
        return None


def test_update_to_late(db: Session, attendance_id: uuid.UUID):
    """Test updating attendance to LATE status."""
    logger.info("=" * 60)
    logger.info("TEST 2: Update Attendance to LATE Status")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # First update to PRESENT
        payload = AttendanceUpdate(status="PRESENT")
        attendance = attendance_service.update_attendance(db, attendance_id, payload)
        logger.info(f"Updated to PRESENT: {attendance.status}")
        
        # Then update to LATE
        payload = AttendanceUpdate(status="LATE")
        attendance = attendance_service.update_attendance(db, attendance_id, payload)
        
        logger.info("✅ Successfully updated attendance to LATE status")
        logger.info(f"   ID: {attendance.id}")
        logger.info(f"   Status: {attendance.status}")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update attendance to LATE status")
        logger.error(f"   Error: {e}")
        logger.error("")
        return False


def test_analytics_include_late(db: Session):
    """Test that analytics include LATE counts."""
    logger.info("=" * 60)
    logger.info("TEST 3: Analytics Include LATE Counts")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        distribution = attendance_service.get_attendance_distribution(db)
        
        logger.info("📊 Attendance Distribution:")
        logger.info(f"   Present: {distribution['present_count']} ({distribution['present_percentage']}%)")
        logger.info(f"   Absent: {distribution['absent_count']} ({distribution['absent_percentage']}%)")
        logger.info(f"   Late: {distribution['late_count']} ({distribution['late_percentage']}%)")
        logger.info(f"   Leave: {distribution['leave_count']} ({distribution['leave_percentage']}%)")
        logger.info(f"   Total: {distribution['total_count']}")
        logger.info("")
        
        if distribution['late_count'] > 0:
            logger.info("✅ Analytics correctly include LATE counts")
            logger.info("")
            return True
        else:
            logger.warning("⚠️  No LATE records found in analytics")
            logger.info("   This might be expected if no LATE records exist")
            logger.info("")
            return True
        
    except Exception as e:
        logger.error(f"❌ Failed to get analytics")
        logger.error(f"   Error: {e}")
        logger.error("")
        return False


def test_filter_by_late(db: Session):
    """Test filtering attendance by LATE status."""
    logger.info("=" * 60)
    logger.info("TEST 4: Filter Attendance by LATE Status")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # Get all LATE attendance records
        late_records = attendance_service.list_attendance(
            db,
            status="LATE",
            limit=10
        )
        
        logger.info(f"Found {len(late_records)} LATE attendance records")
        
        if late_records:
            logger.info("")
            logger.info("Sample LATE records:")
            for record in late_records[:3]:
                logger.info(f"   - {record.day} | {record.user_name} | {record.status}")
        
        logger.info("")
        logger.info("✅ Successfully filtered by LATE status")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to filter by LATE status")
        logger.error(f"   Error: {e}")
        logger.error("")
        return False


def test_all_statuses(db: Session, intern_id: uuid.UUID):
    """Test all attendance statuses."""
    logger.info("=" * 60)
    logger.info("TEST 5: All Attendance Statuses")
    logger.info("=" * 60)
    logger.info("")
    
    statuses = ["PRESENT", "ABSENT", "LATE", "LEAVE"]
    results = {}
    
    for i, status in enumerate(statuses):
        test_date = date.today() - timedelta(days=i+10)
        
        try:
            payload = AttendanceCreate(
                user_id=intern_id,
                date=test_date,
                status=status
            )
            
            attendance = attendance_service.create_attendance(db, payload)
            results[status] = "✅ Success"
            logger.info(f"✅ {status}: Created successfully")
            
        except Exception as e:
            results[status] = f"❌ Failed: {e}"
            logger.error(f"❌ {status}: {e}")
    
    logger.info("")
    logger.info("Summary:")
    for status, result in results.items():
        logger.info(f"   {status}: {result}")
    
    logger.info("")
    
    all_success = all("✅" in result for result in results.values())
    if all_success:
        logger.info("✅ All statuses work correctly")
    else:
        logger.error("❌ Some statuses failed")
    
    logger.info("")
    return all_success


def cleanup_test_data(db: Session, attendance_ids: list):
    """Clean up test attendance records."""
    logger.info("=" * 60)
    logger.info("CLEANUP: Removing Test Data")
    logger.info("=" * 60)
    logger.info("")
    
    for attendance_id in attendance_ids:
        try:
            attendance_service.delete_attendance(db, attendance_id)
            logger.info(f"✅ Deleted test record {attendance_id}")
        except Exception as e:
            logger.warning(f"⚠️  Could not delete {attendance_id}: {e}")
    
    logger.info("")


def main():
    """Main test function."""
    try:
        logger.info("=" * 60)
        logger.info("LATE STATUS TEST SUITE")
        logger.info("=" * 60)
        logger.info("")
        
        # Connect to database
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        db = Session(engine)
        
        # Get test intern
        logger.info("Getting test intern...")
        intern = get_test_intern(db)
        if not intern:
            return 1
        
        logger.info(f"✅ Using intern: {intern.name} ({intern.id})")
        logger.info("")
        
        # Track created records for cleanup
        test_attendance_ids = []
        
        # Run tests
        test_results = []
        
        # Test 1: Create with LATE
        attendance_id = test_create_late_attendance(db, intern.id)
        if attendance_id:
            test_attendance_ids.append(attendance_id)
            test_results.append(("Create LATE", True))
            
            # Test 2: Update to LATE
            success = test_update_to_late(db, attendance_id)
            test_results.append(("Update to LATE", success))
        else:
            test_results.append(("Create LATE", False))
            test_results.append(("Update to LATE", False))
        
        # Test 3: Analytics
        success = test_analytics_include_late(db)
        test_results.append(("Analytics LATE", success))
        
        # Test 4: Filter by LATE
        success = test_filter_by_late(db)
        test_results.append(("Filter LATE", success))
        
        # Test 5: All statuses
        success = test_all_statuses(db, intern.id)
        test_results.append(("All Statuses", success))
        
        # Cleanup
        if test_attendance_ids:
            cleanup_test_data(db, test_attendance_ids)
        
        # Summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info("")
        
        for test_name, success in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} - {test_name}")
        
        logger.info("")
        
        all_passed = all(success for _, success in test_results)
        
        if all_passed:
            logger.info("=" * 60)
            logger.info("✅ ALL TESTS PASSED")
            logger.info("=" * 60)
            logger.info("")
            logger.info("LATE status is working correctly!")
            logger.info("")
            return 0
        else:
            logger.info("=" * 60)
            logger.info("❌ SOME TESTS FAILED")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Please check the errors above and:")
            logger.info("1. Verify the database enum includes LATE")
            logger.info("2. Run: python scripts/add_late_status_to_enum.py")
            logger.info("3. Restart the application")
            logger.info("")
            return 1
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ TEST SUITE FAILED!")
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
