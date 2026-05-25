# app/models/roadmap.py

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class WeeklyRoadmap(Base):
    __tablename__ = "weekly_roadmaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    role = Column(String, nullable=False, server_default="ALL") # AIML, FULLSTACK, ALL
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    batch = relationship("Batch", backref="roadmaps")
    creator = relationship("Profile", backref="created_roadmaps")
    entries = relationship("RoadmapEntry", back_populates="roadmap", cascade="all, delete-orphan", order_by="RoadmapEntry.sort_order")

    __table_args__ = (
        UniqueConstraint('batch_id', 'role', name='uq_batch_role'),
    )


class RoadmapEntry(Base):
    __tablename__ = "roadmap_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roadmap_id = Column(UUID(as_uuid=True), ForeignKey("weekly_roadmaps.id"), nullable=False)
    day_label = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    activities = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)

    # Relationships
    roadmap = relationship("WeeklyRoadmap", back_populates="entries")
