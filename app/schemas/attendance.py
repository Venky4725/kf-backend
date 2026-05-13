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
        """Normalize and validate status - MUST BE UPPERCASE for PostgreSQL enum"""
        # Normalize to UPPERCASE (database enum is UPPERCASE)
        normalized = v.strip().upper()
        
        # Valid statuses (UPPERCASE to match database enum)
        valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}
        
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
        """Normalize and validate status - MUST BE UPPERCASE for PostgreSQL enum"""
        # Normalize to UPPERCASE (database enum is UPPERCASE)
        normalized = v.strip().upper()
        
        # Valid statuses (UPPERCASE to match database enum)
        valid_statuses = {"PRESENT", "ABSENT", "LATE", "LEAVE"}
        
        if normalized not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(sorted(valid_statuses))}")
        
        return normalized


# Nested schemas for profile data
class InternInfo(BaseModel):
    """Nested intern information"""
    id: UUID
    name: str
    email: str
    batch_id: UUID | None = None
    
    class Config:
        from_attributes = True


class BatchInfo(BaseModel):
    """Nested batch information"""
    id: UUID
    name: str
    
    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    """
    Enhanced attendance response with nested profile and batch data.
    This ensures frontend receives proper user names and batch information.
    """
    id: UUID
    user_id: UUID
    day: DateType
    status: str
    created_at: datetime
    
    # Enhanced fields for frontend display
    user_name: str | None = None
    user_email: str | None = None
    batch_id: UUID | None = None
    batch_name: str | None = None

    class Config:
        from_attributes = True


class AttendanceDetailResponse(BaseModel):
    """
    Detailed attendance response with full nested objects.
    Use this for single record retrieval where full details are needed.
    """
    id: UUID
    user_id: UUID
    day: DateType
    status: str
    created_at: datetime
    
    # Nested objects
    intern: InternInfo | None = None
    batch: BatchInfo | None = None

    class Config:
        from_attributes = True