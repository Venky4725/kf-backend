# app/models/evaluation.py

from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    intern_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)

    week_number = Column(Integer, nullable=False)
    score = Column(Numeric(5, 2), nullable=False)

    feedback = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    intern = relationship("Profile", foreign_keys=[intern_id], back_populates="evaluations", lazy="select")
    reviewer = relationship("Profile", foreign_keys=[reviewed_by], lazy="select")