#!/usr/bin/env python3
"""
Backend Stability Test Suite

Tests all critical backend functionality to ensure stability and consistency.

Usage:
    python scripts/test_backend_stability.py
"""

import sys
import os
import json
from datetime import date, datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.profile_service import profile_service
from app.services.batch_service import batch_service
from app.services.notification_service import notification_service
from app.services.attendance_service import attendance_service
from app.schemas.profile import ProfileCreate
from app.schemas.batch import BatchCreate
from app.schemas.notification import NotificationCreate
from app.schemas.attendance import AttendanceCreate
from app.core.logger import get_logger

logger = get_logger(__name__)


class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, test_name: str):
        self.passed += 1
        logger.info(f"✅ PASS: {test_name}")
    
    def fail_test(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        logger.error(f"❌ FAIL: {test_name} - {error}")
    
    def summary(self):
        total = self.passed + self.failed
        logger.info("\n" + "=" * 60)
        logger.info(f"TEST SUMMARY: {self.passed}/{total} passed")
        if self.errors:
            logger.error("\nFailed tests:")
            for error in self.errors:
                logger.error(f"  - {error}")
        logger.info("=" * 60)
        return self.failed == 0


def test_intern_creation(db: Session, results: TestResult):
    """Test intern creation with batch assignment."""
    logger.info("\n[TEST] Intern Creation")
    
    try:
        # Create a test batch first
        batch = batch_service.create_batch(db, BatchCreate(
            name=f"Test Batch {uuid4().hex[:8]}",
            tech_stack="Python",
            start_date=date.today()
        ))
        
        # Test 1: Create intern with batch_id
        try:
            intern = profile_service.create_profile(db, ProfileCreate(
                name="Test Intern 1",
                email=f"intern1_{uuid4().hex[:8]}@test.com",
                role="INTERN",
                tech_stack="Python",
                batch_id=batch.id
            ), current_user=None)
            
            if intern.batch_id == batch.id:
                results.pass_test("Intern creation with batch_id")
            else:
                results.fail_test("Intern creation with batch_id", "Batch not assigned correctly")
        except Exception as e:
            results.fail_test("Intern creation with batch_id", str(e))
        
        # Test 2: Create intern with batch_name
        try:
            intern2 = profile_service.create_profile(db, ProfileCreate(
                name="Test Intern 2",
                email=f"intern2_{uuid4().hex[:8]}@test.com",
                role="INTERN",
                tech_stack="Python",
                batch_name=batch.name
            ), current_user=None)
            
            if intern2.batch_id == batch.id:
                results.pass_test("Intern creation with batch_name")
            else:
                results.fail_test("Intern creation with batch_name", "Batch not assigned correctly")
        except Exception as e:
            results.fail_test("Intern creation with batch_name", str(e))
        
        # Test 3: Duplicate email should fail
        try:
            profile_service.create_profile(db, ProfileCreate(
                name="Duplicate Intern",
                email=intern.email,
                role="INTERN",
                tech_stack="Python",
                batch_id=batch.id
            ), current_user=None)
            results.fail_test("Duplicate email prevention", "Should have raised ConflictError")
        except Exception:
            results.pass_test("Duplicate email prevention")
        
        # Cleanup
        db.rollback()
        
    except Exception as e:
        results.fail_test("Intern creation setup", str(e))
        db.rollback()


def test_batch_tech_lead_assignment(db: Session, results: TestResult):
    """Test batch tech lead assignment and display."""
    logger.info("\n[TEST] Batch Tech Lead Assignment")
    
    try:
        # Create tech leads
        tl1 = profile_service.create_profile(db, ProfileCreate(
            name="Tech Lead 1",
            email=f"tl1_{uuid4().hex[:8]}@test.com",
            role="TECHNICAL_LEAD",
            tech_stack="Python"
        ), current_user=None)
        
        tl2 = profile_service.create_profile(db, ProfileCreate(
            name="Tech Lead 2",
            email=f"tl2_{uuid4().hex[:8]}@test.com",
            role="TECHNICAL_LEAD",
            tech_stack="Python"
        ), current_user=None)
        
        # Test 1: Create batch with both tech leads
        try:
            batch = batch_service.create_batch(db, BatchCreate(
                name=f"Test Batch {uuid4().hex[:8]}",
                tech_stack="Python",
                start_date=date.today(),
                first_tech_lead_id=tl1.id,
                second_tech_lead_id=tl2.id
            ))
            
            if batch.first_tech_lead_id == tl1.id and batch.second_tech_lead_id == tl2.id:
                results.pass_test("Batch creation with two tech leads")
            else:
                results.fail_test("Batch creation with two tech leads", "Tech leads not assigned correctly")
        except Exception as e:
            results.fail_test("Batch creation with two tech leads", str(e))
        
        # Test 2: Get batch and verify enriched response
        try:
            enriched = batch_service._enrich_batch_response(db, batch)
            
            if enriched["tech_leads_display"] == f"{tl1.name}/{tl2.name}":
                results.pass_test("Batch tech_leads_display format (A/B)")
            else:
                results.fail_test("Batch tech_leads_display format (A/B)", 
                                f"Expected '{tl1.name}/{tl2.name}', got '{enriched['tech_leads_display']}'")
        except Exception as e:
            results.fail_test("Batch tech_leads_display format (A/B)", str(e))
        
        # Test 3: Batch with only first tech lead
        try:
            batch2 = batch_service.create_batch(db, BatchCreate(
                name=f"Test Batch {uuid4().hex[:8]}",
                tech_stack="Python",
                start_date=date.today(),
                first_tech_lead_id=tl1.id
            ))
            
            enriched2 = batch_service._enrich_batch_response(db, batch2)
            
            if enriched2["tech_leads_display"] == tl1.name:
                results.pass_test("Batch tech_leads_display format (A only)")
            else:
                results.fail_test("Batch tech_leads_display format (A only)", 
                                f"Expected '{tl1.name}', got '{enriched2['tech_leads_display']}'")
        except Exception as e:
            results.fail_test("Batch tech_leads_display format (A only)", str(e))
        
        # Test 4: Batch with no tech leads
        try:
            batch3 = batch_service.create_batch(db, BatchCreate(
                name=f"Test Batch {uuid4().hex[:8]}",
                tech_stack="Python",
                start_date=date.today()
            ))
            
            enriched3 = batch_service._enrich_batch_response(db, batch3)
            
            if enriched3["tech_leads_display"] == "Unassigned":
                results.pass_test("Batch tech_leads_display format (Unassigned)")
            else:
                results.fail_test("Batch tech_leads_display format (Unassigned)", 
                                f"Expected 'Unassigned', got '{enriched3['tech_leads_display']}'")
        except Exception as e:
            results.fail_test("Batch tech_leads_display format (Unassigned)", str(e))
        
        # Cleanup
        db.rollback()
        
    except Exception as e:
        results.fail_test("Batch tech lead assignment setup", str(e))
        db.rollback()


def test_notification_system(db: Session, results: TestResult):
    """Test notification creation and retrieval."""
    logger.info("\n[TEST] Notification System")
    
    try:
        # Create test users
        sender = profile_service.create_profile(db, ProfileCreate(
            name="Sender User",
            email=f"sender_{uuid4().hex[:8]}@test.com",
            role="ADMIN",
            tech_stack="Python"
        ), current_user=None)
        
        receiver = profile_service.create_profile(db, ProfileCreate(
            name="Receiver User",
            email=f"receiver_{uuid4().hex[:8]}@test.com",
            role="INTERN",
            tech_stack="Python"
        ), current_user=None)
        
        # Test 1: Create notification with sender
        try:
            notification = notification_service.create_notification(db, NotificationCreate(
                user_id=receiver.id,
                sender_id=sender.id,
                title="Test Notification",
                message="This is a test message",
                type="INFO"
            ))
            
            if notification.sender_id == sender.id:
                results.pass_test("Notification creation with sender")
            else:
                results.fail_test("Notification creation with sender", "Sender not set correctly")
        except Exception as e:
            results.fail_test("Notification creation with sender", str(e))
        
        # Test 2: List notifications includes sender info
        try:
            notifications = notification_service.list_notifications(
                db,
                user_id=receiver.id,
                current_user=receiver
            )
            
            if notifications and notifications[0].get("sender_name") == sender.name:
                results.pass_test("Notification list includes sender_name")
            else:
                results.fail_test("Notification list includes sender_name", "sender_name not populated")
        except Exception as e:
            results.fail_test("Notification list includes sender_name", str(e))
        
        # Cleanup
        db.rollback()
        
    except Exception as e:
        results.fail_test("Notification system setup", str(e))
        db.rollback()


def test_attendance_system(db: Session, results: TestResult):
    """Test attendance creation and status validation."""
    logger.info("\n[TEST] Attendance System")
    
    try:
        # Create test user
        intern = profile_service.create_profile(db, ProfileCreate(
            name="Test Intern",
            email=f"intern_{uuid4().hex[:8]}@test.com",
            role="INTERN",
            tech_stack="Python"
        ), current_user=None)
        
        # Test 1: Create attendance with PRESENT status
        try:
            attendance = attendance_service.create_attendance(db, AttendanceCreate(
                user_id=intern.id,
                day=date.today(),
                status="PRESENT"
            ), current_user=None)
            
            if attendance.status == "PRESENT":
                results.pass_test("Attendance creation with PRESENT status")
            else:
                results.fail_test("Attendance creation with PRESENT status", "Status not set correctly")
        except Exception as e:
            results.fail_test("Attendance creation with PRESENT status", str(e))
        
        # Test 2: Create attendance with LATE status
        try:
            attendance2 = attendance_service.create_attendance(db, AttendanceCreate(
                user_id=intern.id,
                day=date.today(),
                status="LATE"
            ), current_user=None)
            
            if attendance2.status == "LATE":
                results.pass_test("Attendance creation with LATE status")
            else:
                results.fail_test("Attendance creation with LATE status", "Status not set correctly")
        except Exception as e:
            results.fail_test("Attendance creation with LATE status", str(e))
        
        # Test 3: Invalid status should fail
        try:
            attendance_service.create_attendance(db, AttendanceCreate(
                user_id=intern.id,
                day=date.today(),
                status="INVALID"
            ), current_user=None)
            results.fail_test("Attendance invalid status validation", "Should have raised ValidationError")
        except Exception:
            results.pass_test("Attendance invalid status validation")
        
        # Cleanup
        db.rollback()
        
    except Exception as e:
        results.fail_test("Attendance system setup", str(e))
        db.rollback()


def test_api_response_consistency(db: Session, results: TestResult):
    """Test API response structure consistency."""
    logger.info("\n[TEST] API Response Consistency")
    
    try:
        # Create test batch
        batch = batch_service.create_batch(db, BatchCreate(
            name=f"Test Batch {uuid4().hex[:8]}",
            tech_stack="Python",
            start_date=date.today()
        ))
        
        # Test 1: Single batch GET has same structure as list
        try:
            single = batch_service._enrich_batch_response(db, batch)
            batches_list = batch_service.list_batches(db, skip=0, limit=1)
            
            if batches_list:
                list_item = batches_list[0]
                
                # Check that both have tech_leads_display
                if "tech_leads_display" in single and "tech_leads_display" in list_item:
                    results.pass_test("Batch response consistency (tech_leads_display)")
                else:
                    results.fail_test("Batch response consistency (tech_leads_display)", 
                                    "tech_leads_display missing in one response")
            else:
                results.fail_test("Batch response consistency", "List returned empty")
        except Exception as e:
            results.fail_test("Batch response consistency", str(e))
        
        # Cleanup
        db.rollback()
        
    except Exception as e:
        results.fail_test("API response consistency setup", str(e))
        db.rollback()


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("BACKEND STABILITY TEST SUITE")
    logger.info("=" * 60)
    
    results = TestResult()
    db = SessionLocal()
    
    try:
        # Run all test suites
        test_intern_creation(db, results)
        test_batch_tech_lead_assignment(db, results)
        test_notification_system(db, results)
        test_attendance_system(db, results)
        test_api_response_consistency(db, results)
        
        # Print summary
        success = results.summary()
        
        if success:
            logger.info("\n✅ ALL TESTS PASSED")
            sys.exit(0)
        else:
            logger.error("\n❌ SOME TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n❌ TEST SUITE FAILED: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
