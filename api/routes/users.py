"""
User Data Management API — GDPR "Forget Me" + Memory Management endpoints.

Allows users to request deletion of all their data: messages,
Mem0 memories, and query analytics records.  Also provides read/delete
access to individual Mem0 memories for the Memory Panel UI.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_db
from api.auth import verify_gdpr_access
from core.audit import write_audit, extract_actor
from core.db.schema import AuditDetails

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Pydantic models ---

class DeleteResponse(BaseModel):
    deleted: bool
    messages_deleted: int
    analytics_deleted: int
    memories_deleted: bool


class MemoryItem(BaseModel):
    id: str
    memory: str
    created_at: str | None = None
    updated_at: str | None = None


class MemoryListResponse(BaseModel):
    memories: list[MemoryItem]
    count: int


@router.delete("/{user_id}/data")
async def delete_user_data(
    user_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
) -> DeleteResponse:
    """
    Delete all data for a user (GDPR "Forget Me").

    Authorization: X-Admin-Key (admin) or X-User-Id matching path (self-delete).

    Removes:
    - All messages from this user
    - All query analytics from this user
    - All Mem0 memories for this user

    Returns counts of deleted records.
    """
    # Auth check (raises 403 if unauthorized)
    actor_role = verify_gdpr_access(user_id, http_request)

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

    # Audit trail
    actor_id, _ = extract_actor(http_request)
    write_audit(
        db,
        clone_id=None,
        action="gdpr.delete",
        actor_id=actor_id or user_id,
        actor_role=actor_role,
        details=AuditDetails(
            session_id=user_id,
            reason=f"msgs={msg_count}, analytics={analytics_count}, mem0={'yes' if memories_deleted else 'failed'}",
        ),
    )

    return DeleteResponse(
        deleted=True,
        messages_deleted=msg_count,
        analytics_deleted=analytics_count,
        memories_deleted=memories_deleted,
    )


# --- Memory Management Endpoints ---


@router.get("/{user_id}/memories")
async def list_user_memories(
    user_id: str,
    http_request: Request,
) -> MemoryListResponse:
    """List all Mem0 memories for a user. Auth: X-User-Id must match path."""
    verify_gdpr_access(user_id, http_request)

    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot list memories for anonymous users")

    try:
        from core.mem0_client import get_mem0_client
        mem = get_mem0_client()
        result = mem.get_all(user_id=user_id, limit=100)

        # Mem0 returns {"results": [...]} — each item has id, memory, created_at, updated_at
        raw = result.get("results", []) if isinstance(result, dict) else result
        items = [
            MemoryItem(
                id=m["id"],
                memory=m.get("memory", ""),
                created_at=m.get("created_at"),
                updated_at=m.get("updated_at"),
            )
            for m in raw
        ]
        return MemoryListResponse(memories=items, count=len(items))
    except Exception as e:
        logger.warning(f"Mem0 list failed for user {user_id}: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")


@router.delete("/{user_id}/memories/{memory_id}")
async def delete_user_memory(
    user_id: str,
    memory_id: str,
    http_request: Request,
) -> dict:
    """Delete a single Mem0 memory. Auth: X-User-Id must match path."""
    verify_gdpr_access(user_id, http_request)

    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot delete memories for anonymous users")

    try:
        from core.mem0_client import get_mem0_client
        mem = get_mem0_client()
        mem.delete(memory_id)
        return {"deleted": True, "memory_id": memory_id}
    except Exception as e:
        logger.warning(f"Mem0 single delete failed for {memory_id}: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")


@router.delete("/{user_id}/memories")
async def delete_all_user_memories(
    user_id: str,
    http_request: Request,
) -> dict:
    """Delete ALL Mem0 memories for a user. Auth: X-User-Id must match path."""
    verify_gdpr_access(user_id, http_request)

    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot delete memories for anonymous users")

    try:
        from core.mem0_client import get_mem0_client
        mem = get_mem0_client()
        mem.delete_all(user_id=user_id)
        return {"deleted": True, "user_id": user_id}
    except Exception as e:
        logger.warning(f"Mem0 delete_all failed for user {user_id}: {e}")
        raise HTTPException(status_code=503, detail="Memory service unavailable")


# --- Conversation History Endpoints ---


@router.get("/{user_id}/history/{clone_slug}")
async def get_user_conversation_history_count(
    user_id: str,
    clone_slug: str,
    http_request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Get conversation history message count for a user+clone pair."""
    verify_gdpr_access(user_id, http_request)

    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot get history for anonymous users")

    from core.db.schema import Clone, Message
    clone_row = db.query(Clone).filter(Clone.slug == clone_slug).first()
    if not clone_row:
        raise HTTPException(status_code=404, detail="Clone not found")

    count = db.query(Message).filter(
        Message.clone_id == clone_row.id,
        Message.user_id == user_id,
    ).count()

    return {"message_count": count}


@router.delete("/{user_id}/history/{clone_slug}")
async def delete_user_conversation_history(
    user_id: str,
    clone_slug: str,
    http_request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Delete conversation history for a user+clone pair."""
    verify_gdpr_access(user_id, http_request)

    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=400, detail="Cannot delete history for anonymous users")

    from core.db.schema import Clone, Message
    clone_row = db.query(Clone).filter(Clone.slug == clone_slug).first()
    if not clone_row:
        raise HTTPException(status_code=404, detail="Clone not found")

    messages_deleted = db.query(Message).filter(
        Message.clone_id == clone_row.id,
        Message.user_id == user_id,
    ).delete()
    db.commit()

    return {"deleted": True, "messages_deleted": messages_deleted}
