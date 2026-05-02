from fastapi import HTTPException, status


class ServiceError(HTTPException):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(ServiceError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} '{identifier}' was not found.",
        )


class ConflictError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class NotImplementedServiceError(ServiceError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=detail)
