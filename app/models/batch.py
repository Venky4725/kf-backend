# app/models/batch.py

from sqlalchemy import Column, String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Batch(Base):
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String, nullable=False)
    tech_stack = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)

    # Three tech leads per batch
    first_tech_lead_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    second_tech_lead_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    third_tech_lead_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    profiles = relationship("Profile", foreign_keys="[Profile.batch_id]", back_populates="batch", lazy="select")
    first_tech_lead = relationship("Profile", foreign_keys=[first_tech_lead_id], lazy="joined")
    second_tech_lead = relationship("Profile", foreign_keys=[second_tech_lead_id], lazy="joined")
    third_tech_lead = relationship("Profile", foreign_keys=[third_tech_lead_id], lazy="joined")