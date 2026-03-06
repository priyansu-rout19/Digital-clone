import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.middleware import APIKeyMiddleware


# Rate limiter (keyed by client IP address)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context: startup and shutdown hooks."""
    # Startup
    load_dotenv()
    os.makedirs("/tmp/dce_uploads", exist_ok=True)
    print("FastAPI app started. Upload directory ready at /tmp/dce_uploads")
    yield
    # Shutdown
    print("FastAPI app shutting down")


app = FastAPI(
    title="Digital Clone Engine API",
    description="API gateway for the Digital Clone Engine (ParaGPT + Sacred Archive)",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Auth middleware (registered first → executes second, inner)
app.add_middleware(APIKeyMiddleware)

# CORS middleware (registered second → executes first, outer)
# Production: set CORS_ORIGINS env var (comma-separated) e.g. "https://paragpt.prem.ai"
cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}


# Import and register routers
from api.routes import chat, ingest, review, config, analytics, users, models

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(review.router, prefix="/review", tags=["Review"])
app.include_router(config.router, prefix="/clone", tags=["Config"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(models.router, prefix="/models", tags=["Models"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
