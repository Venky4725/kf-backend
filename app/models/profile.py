# app/models/profile.py

from sqlalchemy import Boolean, Column, DateTime, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    intern_role = Column(String, nullable=True) # AI/ML, FULLSTACK
    tech_stack = Column(String, nullable=True)

    batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True, index=True)

    # Authentication fields - use Text for bcrypt hash (60 chars)
    password_hash = Column(Text, nullable=True)
    must_change_password = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to Batch (bidirectional with back_populates)
    batch = relationship("Batch", foreign_keys=[batch_id], back_populates="profiles", lazy="joined")
    
    @property
    def batch_name(self):
        """Helper property to get batch name safely."""
        return self.batch.name if self.batch else None
    
    # Relationship to Evaluations
    evaluations = relationship("Evaluation", foreign_keys="Evaluation.intern_id", back_populates="intern", lazy="select")

    # Relationships for Technical Leads (Three possible assignment positions in Batch table)
    batches_first = relationship("Batch", foreign_keys="[Batch.first_tech_lead_id]", lazy="select")
    batches_second = relationship("Batch", foreign_keys="[Batch.second_tech_lead_id]", lazy="select")
    batches_third = relationship("Batch", foreign_keys="[Batch.third_tech_lead_id]", lazy="select")

    @property
    def led_batches(self):
        """Returns all batches where this profile is assigned as a technical lead."""
        all_led = []
        if self.batches_first:
            all_led.extend(self.batches_first)
        if self.batches_second:
            all_led.extend(self.batches_second)
        if self.batches_third:
            all_led.extend(self.batches_third)
            
        # Unique batches only
        seen_ids = set()
        unique_led = []
        for b in all_led:
            if b.id not in seen_ids:
                unique_led.append(b)
                seen_ids.add(b.id)
        return unique_led