"""
Authorization helpers for protected operations.

Separate from middleware.py (which handles blanket API key auth).
These are endpoint-specific authorization checks used as FastAPI dependencies.
"""

import os
import logging

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


def verify_gdpr_access(user_id: str, request: Request) -> str:
    """
    Verify the caller is authorized to delete this user's data.

    Authorization paths:
    1. Admin: X-Admin-Key header matches DCE_ADMIN_KEY env var.
    2. Self-delete: X-User-Id header matches user_id in path.

    Returns the actor_role ("admin" or "user") for audit logging.
    Raises HTTPException 403 if neither condition is met.

    When DCE_ADMIN_KEY is not set, only self-delete works —
    same dev-convenience pattern as APIKeyMiddleware.
    """
    # Path 1: Admin key
    admin_key = os.environ.get("DCE_ADMIN_KEY")
    provided_admin_key = request.headers.get("X-Admin-Key")

    if admin_key and provided_admin_key and provided_admin_key == admin_key:
        return "admin"

    # Path 2: Self-delete (user proves identity via header)
    header_user_id = request.headers.get("X-User-Id")
    if header_user_id and header_user_id == user_id:
        return "user"

    raise HTTPException(
        status_code=403,
        detail=(
            "GDPR delete requires authorization. "
            "Send X-Admin-Key header (admin) or X-User-Id header matching the path (self-delete)."
        ),
    )
