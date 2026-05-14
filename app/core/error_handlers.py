# app/core/error_handlers.py
"""
Centralized error handling for the application.
Ensures consistent error responses and proper logging.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
from app.core.logger import get_logger

logger = get_logger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors (422 Unprocessable Entity).
    Provides detailed error information for debugging.
    """
    logger.error(f"Validation error on {request.method} {request.url.path}")
    logger.error(f"Errors: {exc.errors()}")
    
    # Try to log request body (if available)
    try:
        body = await request.body()
        if body:
            logger.error(f"Request body: {body.decode('utf-8')}")
    except Exception:
        pass
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "message": "Request validation failed. Please check your input data.",
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Handle database integrity errors (unique constraints, foreign keys, etc.).
    Returns 409 Conflict with user-friendly message.
    """
    logger.error(f"Database integrity error on {request.method} {request.url.path}")
    logger.error(f"Error: {exc}")
    
    # Parse error message to provide helpful feedback
    error_msg = str(exc.orig).lower() if hasattr(exc, 'orig') else str(exc).lower()
    
    if 'unique' in error_msg:
        if 'email' in error_msg:
            message = "This email address is already in use."
        elif 'attendance' in error_msg and 'user_id' in error_msg and 'day' in error_msg:
            message = "Attendance record already exists for this user and date."
        else:
            message = "This record already exists or conflicts with existing data."
    elif 'foreign key' in error_msg:
        if 'batch' in error_msg:
            message = "The specified batch does not exist."
        elif 'profile' in error_msg or 'user' in error_msg:
            message = "The specified user does not exist."
        else:
            message = "Referenced resource does not exist."
    elif 'not null' in error_msg:
        message = "Required field is missing."
    else:
        message = "Database constraint violation. Please check your input data."
    
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": message,
            "error_type": "IntegrityError",
        },
    )


async def data_error_handler(request: Request, exc: DataError):
    """
    Handle database data errors (invalid data types, enum violations, etc.).
    Returns 400 Bad Request with user-friendly message.
    """
    logger.error(f"Database data error on {request.method} {request.url.path}")
    logger.error(f"Error: {exc}")
    
    # Parse error message
    error_msg = str(exc.orig).lower() if hasattr(exc, 'orig') else str(exc).lower()
    
    if 'enum' in error_msg:
        if 'attendance_status' in error_msg:
            message = "Invalid attendance status. Valid values: PRESENT, ABSENT, LATE, LEAVE."
        else:
            message = "Invalid value for enumerated field."
    elif 'uuid' in error_msg:
        message = "Invalid UUID format."
    elif 'date' in error_msg or 'timestamp' in error_msg:
        message = "Invalid date or timestamp format."
    else:
        message = "Invalid data format. Please check your input."
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": message,
            "error_type": "DataError",
        },
    )


async def operational_error_handler(request: Request, exc: OperationalError):
    """
    Handle database operational errors (connection issues, timeouts, etc.).
    Returns 503 Service Unavailable.
    """
    logger.error(f"Database operational error on {request.method} {request.url.path}")
    logger.error(f"Error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Database service is temporarily unavailable. Please try again later.",
            "error_type": "OperationalError",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Returns 500 Internal Server Error.
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}")
    logger.error(f"Error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again or contact support.",
            "error_type": type(exc).__name__,
        },
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.
    Call this function in main.py after creating the app.
    """
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import IntegrityError, DataError, OperationalError
    
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DataError, data_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Error handlers registered")
