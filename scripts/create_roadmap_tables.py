#!/usr/bin/env python3
"""
Migration script to create roadmap tables.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.models.roadmap import WeeklyRoadmap, RoadmapEntry
from app.core.logger import get_logger

logger = get_logger(__name__)


def migrate():
    """Create weekly_roadmaps and roadmap_entries tables."""
    logger.info("Creating roadmap tables...")
    try:
        WeeklyRoadmap.__table__.create(bind=engine, checkfirst=True)
        RoadmapEntry.__table__.create(bind=engine, checkfirst=True)
        logger.info("✅ Roadmap tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create roadmap tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    migrate()
