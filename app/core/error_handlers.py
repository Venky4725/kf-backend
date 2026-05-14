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
    
    CRITICAL: All error objects must be converted to JSON-serializable strings.
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
    
    # Convert all error details to JSON-serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": [str(loc) for loc in error.get("loc", [])],
            "msg": str(error.get("msg", "Validation error")),
            "type": str(error.get("type", "value_error")),
        }
        
        # Handle the 'ctx' field which may contain non-serializable objects
        if "ctx" in error:
            ctx = error["ctx"]
            if isinstance(ctx, dict):
                serializable_error["ctx"] = {
                    k: str(v) for k, v in ctx.items()
                }
        
        # Handle 'input' field - convert to string if present
        if "input" in error:
            serializable_error["input"] = str(error["input"])
        
        serializable_errors.append(serializable_error)
    
    # Build user-friendly error messages
    error_messages = []
    for error in serializable_errors:
        field = " -> ".join(error["loc"][1:]) if len(error["loc"]) > 1 else "request"
        message = error["msg"]
        error_messages.append(f"{field}: {message}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": serializable_errors,
            "message": "Validation failed: " + "; ".join(error_messages),
            "errors": error_messages,  # Simple list for frontend
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
    
    # Convert exception to string to ensure JSON serialization
    error_message = str(exc)
    error_type = type(exc).__name__
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_message,
            "error_type": error_type,
        },
    )


async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle ValueError exceptions (often from validators).
    Returns 422 Unprocessable Entity with clear message.
    """
    logger.error(f"ValueError on {request.method} {request.url.path}")
    logger.error(f"Error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": str(exc),
            "message": str(exc),
            "error_type": "ValueError",
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
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(DataError, data_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Error handlers registered")
