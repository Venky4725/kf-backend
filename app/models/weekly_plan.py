from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid

class WeeklyPlanDay(Base):
    __tablename__ = "weekly_plan_days"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    
    day = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    activities = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    
    order_index = Column(Integer, nullable=False, default=0)
