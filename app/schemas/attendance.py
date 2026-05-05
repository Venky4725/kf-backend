# app/schemas/attendance.py

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date as DateType, datetime


class AttendanceCreate(BaseModel):
    user_id: UUID
    day: DateType = Field(..., alias="date")  # Accept "date" from frontend, store as "day"
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Normalize and validate status - MUST BE LOWERCASE for PostgreSQL enum"""
        # Normalize to lowercase (database enum is lowercase)
        normalized = v.strip().lower()
        
        # Valid statuses (lowercase to match database enum)
        valid_statuses = {"present", "absent", "late", "leave"}
        
        if normalized not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
        
        return normalized
    
    class Config:
        populate_by_name = True  # Allow both 'date' and 'day'


class AttendanceUpdate(BaseModel):
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Normalize and validate status - MUST BE LOWERCASE for PostgreSQL enum"""
        # Normalize to lowercase (database enum is lowercase)
        normalized = v.strip().lower()
        
        # Valid statuses (lowercase to match database enum)
        valid_statuses = {"present", "absent", "late", "leave"}
        
        if normalized not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
        
        return normalized


class AttendanceResponse(BaseModel):
    id: UUID
    user_id: UUID
    day: DateType
    status: str
    created_at: datetime
    # Enhanced fields
    user_name: str | None = None
    batch_name: str | None = None

    class Config:
        from_attributes = True