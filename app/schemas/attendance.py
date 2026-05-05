# app/schemas/attendance.py

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date, datetime


class AttendanceCreate(BaseModel):
    user_id: UUID
    date: date = Field(..., alias="date")  # Accept "date" from frontend
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Normalize and validate status"""
        # Normalize to uppercase
        normalized = v.strip().upper()
        
        # Valid statuses
        valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}
        
        if normalized not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
        
        return normalized
    
    @property
    def day(self) -> date:
        """Map 'date' to 'day' for database compatibility"""
        return self.date
    
    class Config:
        populate_by_name = True  # Allow both 'date' and 'day'


class AttendanceUpdate(BaseModel):
    status: str
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Normalize and validate status"""
        # Normalize to uppercase
        normalized = v.strip().upper()
        
        # Valid statuses
        valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}
        
        if normalized not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
        
        return normalized


class AttendanceResponse(BaseModel):
    id: UUID
    user_id: UUID
    day: date
    status: str
    created_at: datetime
    # Enhanced fields
    user_name: str | None = None
    batch_name: str | None = None

    class Config:
        from_attributes = True