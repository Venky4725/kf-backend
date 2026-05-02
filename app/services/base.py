from collections.abc import Mapping
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.audit import add_audit_log
from app.services.exceptions import ConflictError, NotFoundError

ModelT = TypeVar("ModelT")


class CRUDService(Generic[ModelT]):
    model: type[ModelT]
    resource_name: str
    table_name: str

    def list(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelT]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def get(self, db: Session, resource_id: UUID) -> ModelT:
        instance = db.get(self.model, resource_id)
        if instance is None:
            raise NotFoundError(self.resource_name, str(resource_id))
        return instance

    def create(self, db: Session, payload: Mapping[str, Any]) -> ModelT:
        instance = self.model(**dict(payload))
        db.add(instance)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise self._map_integrity_error(exc) from exc
        add_audit_log(db, action="CREATE", table_name=self.table_name, record_id=getattr(instance, "id", None))
        return self._commit_and_refresh(db, instance)

    def update(self, db: Session, resource_id: UUID, payload: Mapping[str, Any]) -> ModelT:
        instance = self.get(db, resource_id)
        for field, value in payload.items():
            setattr(instance, field, value)
        add_audit_log(db, action="UPDATE", table_name=self.table_name, record_id=resource_id)
        return self._commit_and_refresh(db, instance)

    def delete(self, db: Session, resource_id: UUID) -> None:
        instance = self.get(db, resource_id)
        add_audit_log(db, action="DELETE", table_name=self.table_name, record_id=resource_id)
        db.delete(instance)
        self._commit(db)

    def _commit_and_refresh(self, db: Session, instance: ModelT) -> ModelT:
        self._commit(db)
        db.refresh(instance)
        return instance

    def _commit(self, db: Session) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise self._map_integrity_error(exc) from exc

    def _map_integrity_error(self, exc: IntegrityError) -> ConflictError:
        detail = str(exc.orig).lower() if exc.orig else str(exc).lower()
        
        # Check for unique constraint violation
        if "unique" in detail or "duplicate" in detail:
            # Try to extract the column name from the error message
            if "email" in detail:
                return ConflictError("This email address is already registered in the system. Please use a different email.")
            if "profiles_email_key" in detail:
                return ConflictError("This email address is already registered in the system. Please use a different email.")
            return ConflictError(f"This {self.resource_name.lower()} already exists. Please check for duplicate values.")
        
        # Check for foreign key constraint violation
        if "foreign key" in detail:
            if "batch" in detail:
                return ConflictError("The selected batch does not exist. Please select a valid batch.")
            return ConflictError(f"This {self.resource_name.lower()} references a record that does not exist.")
        
        return ConflictError(f"Unable to save {self.resource_name.lower()} due to a database constraint.")
