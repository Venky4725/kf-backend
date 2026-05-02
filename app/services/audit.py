from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def add_audit_log(
    db: Session,
    *,
    action: str,
    table_name: str,
    record_id: UUID | None,
    user_id: UUID | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
    )
    db.add(audit_log)
    return audit_log
