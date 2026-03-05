import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException

from core.db.schema import Clone
from core.models.clone_profile import CloneProfile

# Load .env BEFORE reading DATABASE_URL — this module is imported before
# FastAPI's lifespan runs, so env vars aren't available yet without this
load_dotenv()

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Session:
    """Dependency: yields a SQLAlchemy session for the request lifetime."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_clone(clone_slug: str, db: Session = Depends(get_db)) -> tuple[str, CloneProfile]:
    """
    Dependency: Loads a clone by slug from the database.
    Returns (clone_id, CloneProfile).
    Raises 404 if clone not found.
    """
    clone_row = db.query(Clone).filter(Clone.slug == clone_slug).first()
    if not clone_row:
        raise HTTPException(status_code=404, detail=f"Clone '{clone_slug}' not found")

    # Reconstruct CloneProfile from JSONB profile column
    profile = CloneProfile(**clone_row.profile)
    return str(clone_row.id), profile
