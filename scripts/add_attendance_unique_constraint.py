#!/usr/bin/env python3
"""
Script to add unique constraint to attendance table.
Prevents duplicate attendance records for same user+day.

IMPORTANT: Run clean_duplicate_attendance.py first to remove existing duplicates!
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.db.session import engine


def check_constraint_exists():
    """Check if the unique constraint already exists."""
    inspector = inspect(engine)
    constraints = inspector.get_unique_constraints('attendance')
    
    for constraint in constraints:
        if constraint['name'] == 'uq_attendance_user_day':
            return True
        # Check if columns match even if name is different
        if set(constraint['column_names']) == {'user_id', 'day'}:
            return True
    
    return False


def check_for_duplicates():
    """Check if there are any duplicate records that would violate the constraint."""
    with engine.connect() as conn:
        query = text("""
            SELECT user_id, day, COUNT(*) as count
            FROM attendance
            GROUP BY user_id, day
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(query)
        duplicates = result.fetchall()
        
        return duplicates


def add_unique_constraint():
    """Add unique constraint to attendance table."""
    
    print("🔍 Checking if constraint already exists...")
    
    if check_constraint_exists():
        print("✅ Unique constraint already exists!")
        return True
    
    print("🔍 Checking for duplicate records...")
    
    duplicates = check_for_duplicates()
    
    if duplicates:
        print(f"❌ Found {len(duplicates)} duplicate user+day combinations!")
        print()
        print("You must clean duplicates first:")
        print("  python scripts/clean_duplicate_attendance.py")
        print()
        for user_id, day, count in duplicates[:5]:  # Show first 5
            print(f"   - User {user_id} on {day}: {count} records")
        if len(duplicates) > 5:
            print(f"   ... and {len(duplicates) - 5} more")
        return False
    
    print("✅ No duplicates found")
    print()
    print("➕ Adding unique constraint...")
    
    with engine.connect() as conn:
        # Add the unique constraint
        query = text("""
            ALTER TABLE attendance 
            ADD CONSTRAINT uq_attendance_user_day 
            UNIQUE (user_id, day)
        """)
        
        conn.execute(query)
        conn.commit()
    
    print("✅ Unique constraint added successfully!")
    print()
    print("Constraint details:")
    print("  - Name: uq_attendance_user_day")
    print("  - Columns: (user_id, day)")
    print("  - Effect: Prevents duplicate attendance for same user on same day")
    
    return True


def main():
    """Main execution."""
    print("=" * 60)
    print("Add Attendance Unique Constraint")
    print("=" * 60)
    print()
    
    try:
        success = add_unique_constraint()
        
        if success:
            print()
            print("=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
            print()
            print("The attendance table now has a unique constraint on (user_id, day)")
            print("This prevents duplicate attendance records at the database level.")
            return 0
        else:
            print()
            print("=" * 60)
            print("❌ Migration failed!")
            print("=" * 60)
            return 1
            
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
