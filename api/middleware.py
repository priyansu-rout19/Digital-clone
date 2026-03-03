"""
Auth Middleware — Digital Clone Engine

Simple API key validation for development.
Production: replace env var check with DB lookup (api_keys table, per-clone keys).

Why BaseHTTPMiddleware?
- Runs before routing — one place catches all endpoints
- Avoids adding auth to every single route function signature
- Cleaner for blanket protection with selective exemptions

Why return Response directly, not raise HTTPException?
- BaseHTTPMiddleware runs outside FastAPI's exception handler chain
- HTTPException won't be caught; must return raw Response object
"""

import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Paths that do NOT require authentication
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validates X-API-Key header against DCE_API_KEY env var.
    Returns 401 if missing, 403 if invalid.
    Exempt paths bypass this check entirely.

    When DCE_API_KEY is not configured (env var empty/unset):
    - All requests pass through (dev convenience, preserves existing tests)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Read the expected key from env (loaded at startup via load_dotenv in conftest.py)
        expected_key = os.environ.get("DCE_API_KEY")

        # If DCE_API_KEY is not configured, allow all
        # This prevents lockout during local development before .env is set
        if not expected_key:
            return await call_next(request)

        # Validate the provided key
        provided_key = request.headers.get("X-API-Key")

        if not provided_key:
            return Response(
                content='{"detail": "Missing X-API-Key header"}',
                status_code=401,
                media_type="application/json",
            )

        if provided_key != expected_key:
            return Response(
                content='{"detail": "Invalid API key"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)
