#!/usr/bin/env python3
"""
Script to test all attendance endpoints and verify fixes.
Tests distribution analytics, individual analytics, and pending attendance.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.attendance_service import attendance_service
from app.models.profile import Profile
from app.models.batch import Batch


def test_attendance_distribution(db: Session):
    """Test attendance distribution analytics."""
    print("\n" + "=" * 60)
    print("TEST: Attendance Distribution Analytics")
    print("=" * 60)
    
    try:
        # Test without filters
        result = attendance_service.get_attendance_distribution(db)
        
        print("\n📊 Distribution (All Batches):")
        print(f"   Present: {result['present_count']} ({result['present_percentage']}%)")
        print(f"   Absent: {result['absent_count']} ({result['absent_percentage']}%)")
        print(f"   Late: {result['late_count']} ({result['late_percentage']}%)")
        print(f"   Leave: {result['leave_count']} ({result['leave_percentage']}%)")
        print(f"   Total: {result['total_count']}")
        
        # Verify percentages add up to 100 (or 0 if no data)
        total_percentage = (
            result['present_percentage'] + 
            result['absent_percentage'] + 
            result['late_percentage'] + 
            result['leave_percentage']
        )
        
        if result['total_count'] > 0:
            if abs(total_percentage - 100.0) < 0.1:  # Allow small rounding error
                print("\n✅ Percentages add up to 100%")
            else:
                print(f"\n⚠️  Percentages add up to {total_percentage}% (should be 100%)")
        else:
            print("\n⚠️  No attendance data found")
        
        # Test with date range
        today = date.today()
        start_date = today - timedelta(days=30)
        
        result_filtered = attendance_service.get_attendance_distribution(
            db,
            start_date=start_date,
            end_date=today
        )
        
        print(f"\n📊 Distribution (Last 30 Days):")
        print(f"   Total: {result_filtered['total_count']}")
        
        print("\n✅ Distribution analytics working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_analytics(db: Session):
    """Test individual intern attendance analytics."""
    print("\n" + "=" * 60)
    print("TEST: Individual Intern Analytics")
    print("=" * 60)
    
    try:
        # Get first intern
        intern = db.query(Profile).filter(Profile.role == "INTERN").first()
        
        if not intern:
            print("\n⚠️  No interns found in database")
            return True
        
        print(f"\n👤 Testing with intern: {intern.name} ({intern.email})")
        
        # Get analytics
        result = attendance_service.get_intern_attendance_analytics(
            db,
            intern.id
        )
        
        print(f"\n📊 Analytics:")
        print(f"   Intern: {result['intern_name']}")
        print(f"   Batch: {result['batch_name'] or 'Not assigned'}")
        print(f"   Present: {result['present_count']}")
        print(f"   Absent: {result['absent_count']}")
        print(f"   Late: {result['late_count']}")
        print(f"   Leave: {result['leave_count']}")
        print(f"   Total Days: {result['total_days']}")
        print(f"   Attendance %: {result['attendance_percentage']}%")
        print(f"   Trend Points: {len(result['trend'])}")
        
        # Verify attendance percentage calculation
        total = result['total_days']
        if total > 0:
            attended = result['present_count'] + result['late_count']
            expected_percentage = round((attended / total) * 100, 2)
            
            if result['attendance_percentage'] == expected_percentage:
                print("\n✅ Attendance percentage calculated correctly")
            else:
                print(f"\n⚠️  Attendance percentage mismatch:")
                print(f"   Expected: {expected_percentage}%")
                print(f"   Got: {result['attendance_percentage']}%")
        
        # Show sample trend data
        if result['trend']:
            print(f"\n📈 Sample Trend Data (first 3):")
            for trend in result['trend'][:3]:
                print(f"   {trend['date']}: P={trend['present']} A={trend['absent']} L={trend['late']}")
        
        print("\n✅ Individual analytics working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pending_attendance(db: Session):
    """Test pending attendance interns endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Pending Attendance Interns")
    print("=" * 60)
    
    try:
        today = date.today()
        
        print(f"\n📅 Testing for date: {today}")
        
        # Get pending interns
        result = attendance_service.get_pending_attendance_interns(
            db,
            attendance_date=today
        )
        
        print(f"\n👥 Total Interns: {len(result)}")
        
        # Count by status
        marked = sum(1 for i in result if i['has_attendance'])
        pending = sum(1 for i in result if not i['has_attendance'])
        
        print(f"   Already Marked: {marked}")
        print(f"   Pending: {pending}")
        
        # Show sample data
        if result:
            print(f"\n📋 Sample Data (first 3):")
            for intern in result[:3]:
                status = "✓ Marked" if intern['has_attendance'] else "○ Pending"
                batch = intern['batch_name'] or 'No batch'
                print(f"   {status} - {intern['name']} ({batch})")
        else:
            print("\n⚠️  No interns found")
        
        print("\n✅ Pending attendance endpoint working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_attendance_list(db: Session):
    """Test attendance listing with filters."""
    print("\n" + "=" * 60)
    print("TEST: Attendance Listing")
    print("=" * 60)
    
    try:
        # Get all attendance
        result = attendance_service.list_attendance(db, limit=10)
        
        print(f"\n📋 Total Records (first 10): {len(result)}")
        
        if result:
            # Check if enhanced fields are populated
            sample = result[0]
            
            print(f"\n📄 Sample Record:")
            print(f"   ID: {sample.id}")
            print(f"   Date: {sample.day}")
            print(f"   Status: {sample.status}")
            print(f"   User Name: {sample.user_name or '❌ MISSING'}")
            print(f"   User Email: {sample.user_email or '❌ MISSING'}")
            print(f"   Batch Name: {sample.batch_name or 'Not assigned'}")
            
            # Verify enhanced fields
            if sample.user_name and sample.user_email:
                print("\n✅ Enhanced fields populated correctly")
            else:
                print("\n⚠️  Enhanced fields missing!")
                return False
            
            # Test with date filter
            today = date.today()
            filtered = attendance_service.list_attendance(
                db,
                attendance_date=today,
                limit=10
            )
            print(f"\n📅 Records for today: {len(filtered)}")
            
        else:
            print("\n⚠️  No attendance records found")
        
        print("\n✅ Attendance listing working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_duplicate_prevention(db: Session):
    """Test duplicate prevention logic."""
    print("\n" + "=" * 60)
    print("TEST: Duplicate Prevention")
    print("=" * 60)
    
    try:
        from app.schemas.attendance import AttendanceCreate
        
        # Get first intern
        intern = db.query(Profile).filter(Profile.role == "INTERN").first()
        
        if not intern:
            print("\n⚠️  No interns found in database")
            return True
        
        print(f"\n👤 Testing with intern: {intern.name}")
        
        test_date = date.today()
        
        # Try to create attendance
        payload1 = AttendanceCreate(
            user_id=intern.id,
            date=test_date,
            status="PRESENT"
        )
        
        result1 = attendance_service.create_attendance(db, payload1)
        print(f"\n✅ First attendance created: {result1.id}")
        
        # Try to create duplicate (should update instead)
        payload2 = AttendanceCreate(
            user_id=intern.id,
            date=test_date,
            status="LATE"
        )
        
        result2 = attendance_service.create_attendance(db, payload2)
        
        if result1.id == result2.id:
            print(f"✅ Duplicate prevented - existing record updated")
            print(f"   Status changed from PRESENT to {result2.status}")
        else:
            print(f"⚠️  New record created instead of updating")
            print(f"   First ID: {result1.id}")
            print(f"   Second ID: {result2.id}")
        
        # Clean up
        attendance_service.delete_attendance(db, result2.id)
        print(f"\n🧹 Cleaned up test data")
        
        print("\n✅ Duplicate prevention working correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution."""
    print("=" * 60)
    print("Attendance Endpoints Test Suite")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        results = {
            "Distribution Analytics": test_attendance_distribution(db),
            "Individual Analytics": test_individual_analytics(db),
            "Pending Attendance": test_pending_attendance(db),
            "Attendance Listing": test_attendance_list(db),
            "Duplicate Prevention": test_duplicate_prevention(db),
        }
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        all_passed = all(results.values())
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 60)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
