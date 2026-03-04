"""
Sample Document Ingestion — Digital Clone Engine (Session 12)

Runs two sample documents through the real IngestionPipeline:
  1. ParaGPT sample (geopolitics/connectivity)
  2. Sacred Archive sample (compassion teachings)

This bypasses the HTTP API — calls the pipeline directly.
Requires: VOYAGE_API_KEY in .env, PostgreSQL running with seeded clones.

Run: python scripts/ingest_samples.py
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db.schema import Clone, Document
from core.models.clone_profile import paragpt_profile, sacred_archive_profile
from core.rag.ingestion.pipeline import IngestionPipeline


# SQLAlchemy URL (for ORM operations)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Raw psycopg URL (pipeline.py and indexer.py use psycopg.connect directly)
PSYCOPG_URL = DATABASE_URL.replace("+psycopg", "")

SAMPLE_DIR = Path(__file__).parent / "sample_docs"


def ingest_sample(clone_slug, filename, profile, source_type, provenance):
    """Insert a Document row then run the full ingestion pipeline."""
    db = SessionLocal()
    try:
        clone_row = db.query(Clone).filter(Clone.slug == clone_slug).first()
        if not clone_row:
            print(f"  ERROR: Clone '{clone_slug}' not found. Run seed_db.py first.")
            return

        file_path = str(SAMPLE_DIR / filename)
        if not Path(file_path).exists():
            print(f"  ERROR: Sample file not found: {file_path}")
            return

        # Check if already ingested (by filename + clone)
        existing = db.query(Document).filter(
            Document.clone_id == clone_row.id,
            Document.filename == filename,
        ).first()
        if existing:
            print(f"  Document '{filename}' already ingested for {clone_slug} — skipping")
            return

        doc_id = str(uuid.uuid4())

        # Insert Document row first (pipeline._update_status needs it)
        doc = Document(
            id=doc_id,
            clone_id=clone_row.id,
            filename=filename,
            source_type=source_type,
            mime_type="text/markdown",
            file_path=file_path,
            provenance=provenance,
            status="queued",
        )
        db.add(doc)
        db.commit()
        print(f"  Created Document row: {doc_id[:8]}... ({filename})")

        # Run the real pipeline: parse → chunk → embed → index
        pipeline = IngestionPipeline(profile=profile, db_url=PSYCOPG_URL)
        result = pipeline.ingest(
            file_path=file_path,
            doc_id=doc_id,
            clone_id=str(clone_row.id),
            source_type=source_type,
            provenance=provenance,
        )
        print(f"  Result: status={result.status}, chunks={result.chunk_count}")
        if result.error_message:
            print(f"  Error: {result.error_message}")

    finally:
        db.close()


def main():
    print("=== Digital Clone Engine — Sample Document Ingestion ===\n")

    print("1. Ingesting ParaGPT sample...")
    ingest_sample(
        clone_slug="paragpt-client",
        filename="paragpt_sample.md",
        profile=paragpt_profile(),
        source_type="essay",
        provenance={"access_tier": "public"},
    )

    print("2. Ingesting Sacred Archive sample...")
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

    print("\nDone.")


if __name__ == "__main__":
    main()
