"""
Audit Logging Utility — write_audit() + extract_actor().

Reusable helper for recording immutable audit trail entries.
Used by review, ingest, and GDPR delete endpoints.

Design: fail-silently — audit failure must never break the main operation.
"""

import logging
import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from core.db.schema import AuditLog, AuditDetails

logger = logging.getLogger(__name__)


def write_audit(
    db: Session,
    *,
    clone_id: Optional[str],
    action: str,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    details: Optional[AuditDetails] = None,
) -> None:
    """
    Write an immutable audit log entry. Fails silently — audit failure
    must never break the operation it's logging.

    Args:
        db: SQLAlchemy session (from get_db dependency).
        clone_id: UUID of the clone (None for cross-clone ops like GDPR delete).
        action: Dot-separated verb, max 50 chars (e.g. "review.approve", "gdpr.delete").
        actor_id: UUID of the actor (from X-Actor-Id header).
        actor_role: Role string (from X-Actor-Role header, e.g. "reviewer", "admin").
        details: AuditDetails Pydantic model with action-specific metadata.
    """
    try:
        clone_uuid = _validate_uuid(clone_id)
        actor_uuid = _validate_uuid(actor_id)

        entry = AuditLog(
            clone_id=clone_uuid,
            action=action[:50],
            actor_id=actor_uuid,
            actor_role=actor_role[:20] if actor_role else None,
            details=details.model_dump(exclude_none=True) if details else None,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Audit write failed (non-blocking): {e}")
        try:
            db.rollback()
        except Exception:
            pass


def extract_actor(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract actor identity from request headers.

    Headers:
        X-Actor-Id: UUID of the person performing the action.
        X-Actor-Role: Their role (reviewer, admin, user, system).

    Returns:
        (actor_id, actor_role) — both may be None.
    """
    actor_id = request.headers.get("X-Actor-Id")
    actor_role = request.headers.get("X-Actor-Role")
    return actor_id, actor_role


def _validate_uuid(value: Optional[str]) -> Optional[str]:
    """Validate a string as UUID. Returns None if invalid."""
    if not value:
        return None
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        return None
