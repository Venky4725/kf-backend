# app/schemas/audit_log.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    table_name: str
    record_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True