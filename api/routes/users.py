"""
User Data Management API — GDPR "Forget Me" endpoint.

Allows users to request deletion of all their data: messages,
Mem0 memories, and query analytics records.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


class DeleteResponse(BaseModel):
    deleted: bool
    messages_deleted: int
    analytics_deleted: int
    memories_deleted: bool


@router.delete("/{user_id}/data")
async def delete_user_data(
    user_id: str,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """
    Delete all data for a user (GDPR "Forget Me").

    Removes:
    - All messages from this user
    - All query analytics from this user
    - All Mem0 memories for this user

    Returns counts of deleted records.
    """
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot delete data for anonymous users")

    # Delete messages
    from core.db.schema import Message
    msg_count = db.query(Message).filter(Message.user_id == user_id).delete()

    # Delete query analytics
    from core.db.schema import QueryAnalytics
    analytics_count = db.query(QueryAnalytics).filter(
        QueryAnalytics.user_id == user_id
    ).delete()

    db.commit()

    # Delete Mem0 memories (separate client, fails gracefully)
    memories_deleted = False
    try:
        from core.mem0_client import get_mem0_client
        mem = get_mem0_client()
        mem.delete_all(user_id=user_id)
        memories_deleted = True
    except Exception as e:
        logger.warning(f"Mem0 deletion failed for user {user_id}: {e}")

    logger.info(
        f"GDPR delete for user {user_id}: "
        f"{msg_count} messages, {analytics_count} analytics, "
        f"memories={'yes' if memories_deleted else 'failed'}"
    )

    return DeleteResponse(
        deleted=True,
        messages_deleted=msg_count,
        analytics_deleted=analytics_count,
        memories_deleted=memories_deleted,
    )
