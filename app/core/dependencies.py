from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.auth_service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    token: str | None = Depends(oauth2_scheme),
) -> Any:
    """Dependency to get the current authenticated user from JWT token."""
    return auth_service.get_current_user(db, token)


def require_roles(*roles: str):
    """Dependency factory to require specific roles for access."""
    def dependency(
        db: DBSession,
        token: str | None = Depends(oauth2_scheme),
    ) -> Any:
        return auth_service.require_roles(db, token, *roles)

    return dependency
