"""
Database Seeder — Digital Clone Engine (Session 12)

Idempotent script that populates the database with:
  1. Two clone profiles (ParaGPT + Sacred Archive) from factory functions
  2. One admin user for Sacred Archive review workflow
  3. Sample provenance graph data (Sacred Archive only)

Run: python scripts/seed_db.py
Safe to re-run — checks for existing rows before inserting.
"""

import os
import sys
import uuid
from pathlib import Path

# Add project root to sys.path so core/ imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db.schema import (
    Clone, User,
    TeachingSource, Topic, Scripture, Teaching,
    TeachingTopic, TeachingScripture, TeachingRelation,
)
from core.models.clone_profile import paragpt_profile, sacred_archive_profile


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_clones(db):
    """Insert ParaGPT and Sacred Archive clone rows."""
    for profile_fn in [paragpt_profile, sacred_archive_profile]:
        profile = profile_fn()
        existing = db.query(Clone).filter(Clone.slug == profile.slug).first()
        if existing:
            print(f"  Clone '{profile.slug}' already exists — skipping")
            continue

        clone = Clone(
            id=uuid.uuid4(),
            slug=profile.slug,
            display_name=profile.display_name,
            bio=profile.bio,
            avatar_url=profile.avatar_url,
            profile=profile.model_dump(mode="json"),
            status="active",
        )
        db.add(clone)
        print(f"  Inserted clone: {profile.slug}")
    db.commit()


def seed_admin_user(db):
    """Insert one admin reviewer for Sacred Archive."""
    email = "admin@sacred-archive.local"
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"  Admin user '{email}' already exists — skipping")
        return existing.id

    user = User(
        id=uuid.uuid4(),
        email=email,
        name="Sacred Archive Admin",
        role="reviewer",
    )
    db.add(user)
    db.commit()
    print(f"  Inserted admin user: {email}")
    return user.id


def seed_provenance(db, sacred_clone_id):
    """Insert sample provenance graph data for Sacred Archive."""
    # Idempotency check — if any topic exists, skip entire block
    existing = db.query(Topic).filter(Topic.name == "compassion").first()
    if existing:
        print("  Provenance data already exists — skipping")
        return

    # Teaching source
    source = TeachingSource(
        id=uuid.uuid4(),
        source_type="retreat",
        event_name="Mountain Retreat 2024",
    )
    db.add(source)

    # Topics
    topic_compassion = Topic(id=uuid.uuid4(), name="compassion", description="The nature of compassion in practice")
    topic_devotion = Topic(id=uuid.uuid4(), name="devotion", description="Surrender and devotion as a path")
    db.add_all([topic_compassion, topic_devotion])

    # Scripture
    scripture = Scripture(id=uuid.uuid4(), reference="Bhagavad Gita 2.47", tradition="Hindu")
    db.add(scripture)
    db.flush()  # Get IDs assigned before creating FKs

    # Teaching 1 — linked to source, topics, and scripture
    teaching1 = Teaching(
        id=uuid.uuid4(),
        clone_id=sacred_clone_id,
        title="On Compassion and Selfless Action",
        date="2024-07-15",
        location="Mountain Retreat Center",
        access_tier="devotee",
        chunk_refs=[],
        source_id=source.id,
    )
    db.add(teaching1)

    # Teaching 2 — related to teaching 1
    teaching2 = Teaching(
        id=uuid.uuid4(),
        clone_id=sacred_clone_id,
        title="The Path of Devotion",
        date="2024-07-16",
        location="Mountain Retreat Center",
        access_tier="devotee",
        chunk_refs=[],
        source_id=source.id,
    )
    db.add(teaching2)
    db.flush()

    # Junction: teaching_topics
    db.add_all([
        TeachingTopic(teaching_id=teaching1.id, topic_id=topic_compassion.id),
        TeachingTopic(teaching_id=teaching1.id, topic_id=topic_devotion.id),
        TeachingTopic(teaching_id=teaching2.id, topic_id=topic_devotion.id),
    ])

    # Junction: teaching_scriptures
    db.add(TeachingScripture(teaching_id=teaching1.id, scripture_id=scripture.id))

    # Self-relation: teaching1 elaborates teaching2
    db.add(TeachingRelation(
        from_teaching_id=teaching1.id,
        to_teaching_id=teaching2.id,
        relation_type="elaborates",
    ))

    db.commit()
    print(f"  Inserted: 1 source, 2 topics, 1 scripture, 2 teachings, 4 junctions")


def main():
    db = SessionLocal()
    try:
        print("=== Digital Clone Engine — Database Seeder ===\n")

        print("1. Seeding clone profiles...")
        seed_clones(db)

        print("2. Seeding admin user...")
        seed_admin_user(db)

        print("3. Seeding provenance graph (Sacred Archive)...")
        sacred = db.query(Clone).filter(Clone.slug == "sacred-archive").first()
        if sacred:
            seed_provenance(db, sacred.id)
        else:
            print("  WARNING: Sacred Archive clone not found — skipping provenance")

        print("\nDone. Database seeded successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
