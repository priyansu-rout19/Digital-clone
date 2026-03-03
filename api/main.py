import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok"}


# Import and register routers
from api.routes import chat, ingest, review, config

app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(review.router, prefix="/review", tags=["Review"])
app.include_router(config.router, prefix="/clone", tags=["Config"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
