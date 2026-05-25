# scripts/add_roadmap_role.py
"""
Migration script to add role column to weekly_roadmaps and a unique constraint.
"""
from sqlalchemy import text
from app.db.session import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        # 1. Add role column
        print("Checking/Adding column weekly_roadmaps.role...")
        db.execute(text(
            "ALTER TABLE weekly_roadmaps ADD COLUMN IF NOT EXISTS role VARCHAR"
        ))
        
        # 2. Update existing roadmaps (default to FULLSTACK if null, or try to guess)
        # For safety, let's just set a default or leave null if unknown.
        # But if we want the unique constraint to work, we might need a value.
        print("Updating existing roadmaps with default role 'FULLSTACK'...")
        db.execute(text(
            "UPDATE weekly_roadmaps SET role = 'FULLSTACK' WHERE role IS NULL"
        ))
        
        # 3. Add unique constraint (batch_id, role)
        # Note: If there are existing duplicates for (batch_id, role), this will fail.
        # We might need to clean up first.
        print("Adding unique constraint (batch_id, role) to weekly_roadmaps...")
        try:
            db.execute(text(
                "ALTER TABLE weekly_roadmaps ADD CONSTRAINT uq_batch_role UNIQUE (batch_id, role)"
            ))
        except Exception as e:
            print(f"Warning: Could not add unique constraint: {e}")
            print("This is likely due to existing duplicate batch_id/role combinations.")

        db.commit()
        print("Migration complete!")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
