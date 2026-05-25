# app/models/task.py

from sqlalchemy import Column, String, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Structured data
    task_type = Column(String, nullable=True, server_default="single") # e.g., "roadmap", "assignment"
    roadmap_entries = Column(JSON, nullable=True, server_default='[]')
    role = Column(String, nullable=False, server_default="GENERAL") # Target intern role (AI/ML, FULLSTACK, GENERAL)

    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)  # NEW
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)

    due_date = Column(Date, nullable=True)
    priority = Column(String, nullable=True, default="MEDIUM")
    status = Column(String, nullable=True, default="OPEN")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    weekly_plan_days = relationship("WeeklyPlanDay", backref="task", cascade="all, delete-orphan")