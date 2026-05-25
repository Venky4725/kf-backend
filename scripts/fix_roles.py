import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.roadmap import WeeklyRoadmap
from app.models.profile import Profile
from app.models.task import Task
from app.utils.role_utils import normalize_role
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_roles():
    db: Session = SessionLocal()
    try:
        # Migrate roadmaps
        roadmaps = db.query(WeeklyRoadmap).all()
        roadmap_count = 0
        for roadmap in roadmaps:
            normalized = normalize_role(roadmap.role)
            if roadmap.role != normalized:
                logger.info(f"Updating roadmap {roadmap.id} role: '{roadmap.role}' -> '{normalized}'")
                roadmap.role = normalized
                roadmap_count += 1
        
        # Migrate tasks
        tasks = db.query(Task).all()
        task_count = 0
        for task in tasks:
            normalized = normalize_role(task.role)
            if task.role != normalized:
                logger.info(f"Updating task {task.id} role: '{task.role}' -> '{normalized}'")
                task.role = normalized
                task_count += 1
                
        # Migrate profiles (intern_roles)
        profiles = db.query(Profile).filter(Profile.role == 'INTERN').all()
        profile_count = 0
        for profile in profiles:
            if profile.intern_role:
                normalized = normalize_role(profile.intern_role)
                if normalized == "ALL":
                    # If it normalizes to ALL, it was probably empty or invalid, skip or log warning
                    pass
                elif profile.intern_role != normalized:
                    logger.info(f"Updating profile {profile.id} intern_role: '{profile.intern_role}' -> '{normalized}'")
                    profile.intern_role = normalized
                    profile_count += 1

        db.commit()
        logger.info(f"Successfully migrated {roadmap_count} roadmaps, {task_count} tasks, and {profile_count} profiles.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_roles()
