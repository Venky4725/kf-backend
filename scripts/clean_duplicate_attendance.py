#!/usr/bin/env python3
"""
Script to clean duplicate attendance records before adding unique constraint.
Keeps the most recent record for each user+day combination.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import engine


def clean_duplicates():
    """Remove duplicate attendance records, keeping the most recent one."""
    
    print("🔍 Checking for duplicate attendance records...")
    
    with engine.connect() as conn:
        # Check for duplicates
        check_query = text("""
            SELECT user_id, day, COUNT(*) as count
            FROM attendance
            GROUP BY user_id, day
            HAVING COUNT(*) > 1
        """)
        
        result = conn.execute(check_query)
        duplicates = result.fetchall()
        
        if not duplicates:
            print("✅ No duplicate attendance records found!")
            return True
        
        print(f"⚠️  Found {len(duplicates)} duplicate user+day combinations")
        
        # Show duplicates
        for user_id, day, count in duplicates:
            print(f"   - User {user_id} on {day}: {count} records")
        
        # Ask for confirmation
        response = input("\n❓ Delete older duplicate records? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Aborted. No changes made.")
            return False
        
        # Delete duplicates, keeping the most recent
        delete_query = text("""
            DELETE FROM attendance a
            USING attendance b
            WHERE a.user_id = b.user_id 
              AND a.day = b.day 
              AND a.created_at < b.created_at
        """)
        
        result = conn.execute(delete_query)
        conn.commit()
        
        deleted_count = result.rowcount
        print(f"✅ Deleted {deleted_count} duplicate records")
        print("✅ Kept the most recent record for each user+day combination")
        
        return True


def main():
    """Main execution."""
    print("=" * 60)
    print("Clean Duplicate Attendance Records")
    print("=" * 60)
    print()
    
    try:
        success = clean_duplicates()
        
        if success:
            print()
            print("=" * 60)
            print("✅ Cleanup completed successfully!")
            print("=" * 60)
            print()
            print("Next step: Run the migration script to add unique constraint")
            print("  python scripts/add_attendance_unique_constraint.py")
            return 0
        else:
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
