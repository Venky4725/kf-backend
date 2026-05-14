# app/models/notification.py

from sqlalchemy import Column, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)  # NEW

    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=True)  # SYSTEM, INFO, WARNING, etc.

    is_read = Column(Boolean, default=False)
    is_broadcast = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    edited_at = Column(DateTime(timezone=True), nullable=True)  # NEW: Track when notification was edited
    
    # Relationships
    sender = relationship("Profile", foreign_keys=[sender_id])