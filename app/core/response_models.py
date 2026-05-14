# app/core/response_models.py
"""
Standardized API response models for consistent frontend/backend communication.
"""

from typing import Generic, TypeVar, Any
from pydantic import BaseModel

T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    success: bool = True
    data: T
    message: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: str | None = None
    error_type: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response for list endpoints."""
    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True


class BulkOperationResponse(BaseModel):
    """Response for bulk operations (CSV upload, batch delete, etc.)."""
    success: bool = True
    created: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0
    errors: list[str] = []
    message: str | None = None


# Response validation helpers

def validate_response_structure(response: dict, required_fields: list[str]) -> bool:
    """
    Validate that a response dict contains all required fields.
    
    Args:
        response: Response dictionary to validate
        required_fields: List of required field names
    
    Returns:
        True if all required fields are present, False otherwise
    """
    return all(field in response for field in required_fields)


def ensure_consistent_null_handling(data: dict) -> dict:
    """
    Ensure consistent null handling across API responses.
    Converts None to null in JSON, ensures empty strings are not used instead of null.
    
    Args:
        data: Response data dictionary
    
    Returns:
        Cleaned data dictionary
    """
    cleaned = {}
    for key, value in data.items():
        if value == "":
            # Convert empty strings to None for optional fields
            cleaned[key] = None
        elif isinstance(value, dict):
            cleaned[key] = ensure_consistent_null_handling(value)
        elif isinstance(value, list):
            cleaned[key] = [
                ensure_consistent_null_handling(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def ensure_uuid_strings(data: dict, uuid_fields: list[str]) -> dict:
    """
    Ensure UUID fields are properly serialized as strings.
    
    Args:
        data: Response data dictionary
        uuid_fields: List of field names that should be UUIDs
    
    Returns:
        Data with UUIDs converted to strings
    """
    from uuid import UUID
    
    for field in uuid_fields:
        if field in data and isinstance(data[field], UUID):
            data[field] = str(data[field])
    
    return data


def ensure_datetime_iso_format(data: dict, datetime_fields: list[str]) -> dict:
    """
    Ensure datetime fields are in ISO 8601 format.
    
    Args:
        data: Response data dictionary
        datetime_fields: List of field names that should be datetimes
    
    Returns:
        Data with datetimes in ISO format
    """
    from datetime import datetime, date
    
    for field in datetime_fields:
        if field in data:
            value = data[field]
            if isinstance(value, datetime):
                data[field] = value.isoformat()
            elif isinstance(value, date):
                data[field] = value.isoformat()
    
    return data
