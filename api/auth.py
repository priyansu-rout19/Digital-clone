"""
Authorization helpers for protected operations.

Separate from middleware.py (which handles blanket API key auth).
These are endpoint-specific authorization checks used as FastAPI dependencies.
"""

import os
import logging
from typing import Callable

from fastapi import Request, HTTPException, Depends

logger = logging.getLogger(__name__)


def require_role(*allowed_roles: str) -> Callable:
    """
    FastAPI dependency factory: enforce X-Actor-Role header.

    Usage: Depends(require_role("reviewer", "curator"))

    Returns the validated role string so it can be used downstream.
    When DCE_API_KEY is not set (dev mode), enforcement is skipped
    and the header value (or "dev") is returned.
    """
    allowed = set(allowed_roles)

    def _check(request: Request) -> str:
        role = request.headers.get("X-Actor-Role", "").lower().strip()

        # Dev convenience: skip enforcement when API key is not configured
        if not os.environ.get("DCE_API_KEY"):
            return role or "dev"

        if role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"This endpoint requires one of these roles: {', '.join(sorted(allowed))}. "
                       f"Send X-Actor-Role header with your request.",
            )
        return role

    return _check


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
