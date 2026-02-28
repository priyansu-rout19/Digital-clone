"""Provenance graph tables for Sacred Archive only.
Replaces Apache AGE (eliminated Oct 2024) with pure PostgreSQL tables + recursive CTEs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"       # This migration runs after 0001
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- teaching_sources (no dependencies) ---
    op.create_table(
        "teaching_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_type", sa.String(20)),
        sa.Column("event_name", sa.Text()),
        sa.Column("recording_url", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- teachings (depends on clones and teaching_sources) ---
    op.create_table(
        "teachings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("clone_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("date", sa.Text()),
        sa.Column("location", sa.Text()),
        sa.Column("access_tier", sa.String(20), server_default="public", nullable=False),
        sa.Column("chunk_refs", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teaching_sources.id")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_teachings_clone_id", "teachings", ["clone_id"])
    op.create_index("idx_teachings_access_tier", "teachings", ["access_tier"])

    # --- topics (no dependencies) ---
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_index("idx_topics_name", "topics", ["name"])

    # --- scriptures (no dependencies) ---
    op.create_table(
        "scriptures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("tradition", sa.Text()),
    )

    # --- teaching_topics junction (depends on teachings and topics) ---
    op.create_table(
        "teaching_topics",
        sa.Column("teaching_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )

    # --- teaching_scriptures junction (depends on teachings and scriptures) ---
    op.create_table(
        "teaching_scriptures",
        sa.Column("teaching_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("scripture_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scriptures.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )

    # --- teaching_relations self-referential (depends on teachings) ---
    op.create_table(
        "teaching_relations",
        sa.Column("from_teaching_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("to_teaching_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("relation_type", sa.String(20), nullable=False),
    )

    # --- teaching_reviewer_links junction (depends on teachings and users) ---
    op.create_table(
        "teaching_reviewer_links",
        sa.Column("teaching_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teachings.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )


def downgrade() -> None:
    # Drop junction tables first (they reference teaching node tables)
    op.drop_table("teaching_reviewer_links")
    op.drop_table("teaching_relations")
    op.drop_table("teaching_scriptures")
    op.drop_table("teaching_topics")
    op.drop_table("scriptures")
    op.drop_table("topics")
    op.drop_table("teachings")
    op.drop_table("teaching_sources")
