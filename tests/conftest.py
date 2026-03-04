"""
Pytest configuration for Digital Clone Engine tests.

Configures pytest-asyncio for async test support and loads .env for tests.
Provides session-scoped fixtures for real database integration:
  - ensure_db_seeded: idempotent DB seeding (clones + sample documents)
  - paragpt_clone_id: real UUID for the ParaGPT clone
  - sacred_clone_id: real UUID for the Sacred Archive clone
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env at test session startup
load_dotenv()

# Ensure project root is on sys.path so scripts/ and core/ imports work
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure pytest-asyncio for async test support
pytest_plugins = ('pytest_asyncio',)


# ---------------------------------------------------------------------------
# Database fixtures for real integration tests
# ---------------------------------------------------------------------------

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core.db.schema import Clone, Document
from core.models.clone_profile import paragpt_profile, sacred_archive_profile


@pytest.fixture(scope="session", autouse=True)
def ensure_db_seeded():
    """
    Session-scoped, autouse fixture that ensures the database has:
      1. Clone rows for paragpt-client and sacred-archive
      2. An admin user for Sacred Archive
      3. Provenance graph data for Sacred Archive
      4. Ingested sample documents with chunks for both clones

    Idempotent: checks for existing data before inserting.
    Skips entirely if DATABASE_URL is not set (unit tests still work).
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # No database configured — skip seeding, let unit tests run
        yield
        return

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # --- Step 1: Seed clones, admin user, and provenance ---
        paragpt_row = db.query(Clone).filter(Clone.slug == "paragpt-client").first()
        sacred_row = db.query(Clone).filter(Clone.slug == "sacred-archive").first()

        if not paragpt_row or not sacred_row:
            from scripts.seed_db import seed_clones, seed_admin_user, seed_provenance
            seed_clones(db)
            seed_admin_user(db)

            # Re-query after seeding
            sacred_row = db.query(Clone).filter(Clone.slug == "sacred-archive").first()
            if sacred_row:
                seed_provenance(db, sacred_row.id)

            # Re-query paragpt too
            paragpt_row = db.query(Clone).filter(Clone.slug == "paragpt-client").first()

        # --- Step 2: Seed sample documents (if chunks are missing) ---
        if paragpt_row:
            has_chunks = db.execute(
                text("SELECT 1 FROM document_chunks WHERE clone_id = :cid LIMIT 1"),
                {"cid": str(paragpt_row.id)},
            ).fetchone()

            if not has_chunks:
                from scripts.ingest_samples import ingest_sample

                # ParaGPT sample
                ingest_sample(
                    clone_slug="paragpt-client",
                    filename="paragpt_sample.md",
                    profile=paragpt_profile(),
                    source_type="essay",
                    provenance={"access_tier": "public"},
                )
                # Sacred Archive sample
                ingest_sample(
                    clone_slug="sacred-archive",
                    filename="sacred_archive_sample.md",
                    profile=sacred_archive_profile(),
                    source_type="transcript",
                    provenance={
                        "date": "2024-07-15",
                        "location": "Mountain Retreat Center",
                        "event": "Mountain Retreat 2024",
                        "verifier": "admin@sacred-archive.local",
                        "access_tier": "devotee",
                    },
                )

    finally:
        db.close()

    yield


@pytest.fixture(scope="session")
def paragpt_clone_id():
    """
    Returns the real UUID (as string) for the ParaGPT clone from the database.
    Requires DATABASE_URL to be set and ensure_db_seeded to have run.
    """
    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL must be set for integration tests"

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        clone = db.query(Clone).filter(Clone.slug == "paragpt-client").first()
        assert clone, "paragpt-client clone not found in database"
        return str(clone.id)
    finally:
        db.close()


@pytest.fixture(scope="session")
def sacred_clone_id():
    """
    Returns the real UUID (as string) for the Sacred Archive clone from the database.
    Requires DATABASE_URL to be set and ensure_db_seeded to have run.
    """
    db_url = os.environ.get("DATABASE_URL")
    assert db_url, "DATABASE_URL must be set for integration tests"

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        clone = db.query(Clone).filter(Clone.slug == "sacred-archive").first()
        assert clone, "sacred-archive clone not found in database"
        return str(clone.id)
    finally:
        db.close()
