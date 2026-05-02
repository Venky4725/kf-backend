#!/usr/bin/env python3
"""Delete all dummy attendance data."""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.base import Base
from app.models.attendance import Attendance

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def delete_dummy_attendance():
    db = SessionLocal()
    try:
        count = db.query(Attendance).delete()
        db.commit()
        print(f"Deleted {count} attendance records.")
    except Exception as e:
        db.rollback()
        print(f"Error deleting attendance data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    delete_dummy_attendance()