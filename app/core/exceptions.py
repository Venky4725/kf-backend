from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base HTTP exception for application-level errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request.") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AuthenticationException(AppException):
    def __init__(self, detail: str = "Authentication failed.") -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AuthorizationException(AppException):
    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} '{identifier}' was not found.",
        )


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource conflict.") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ExternalServiceException(AppException):
    def __init__(self, detail: str = "External service is unavailable.") -> None:
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class NotImplementedException(AppException):
    def __init__(self, detail: str = "This feature is not implemented yet.") -> None:
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)
