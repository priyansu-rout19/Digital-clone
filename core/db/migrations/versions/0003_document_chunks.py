"""Create document_chunks table for RAG ingestion.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# Revision ID and down_revision
revision = "0003"
down_revision = "0002"  # This migration runs after 0002
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), primary_key=True, nullable=False),
        sa.Column("doc_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("clone_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_id", sa.String, nullable=False, unique=True),
        sa.Column("passage", sa.Text, nullable=False),
        sa.Column("source_type", sa.String, nullable=False),  # book|essay|transcript|audio|video
        sa.Column("access_tier", sa.String, nullable=False, server_default="public"),
        sa.Column("date", sa.String),  # ISO 8601 from provenance
        sa.Column("embedding", Vector(1024)),  # Qwen3-Embedding-0.6B dimensions
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        # Foreign key constraints
        sa.ForeignKeyConstraint(["doc_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clone_id"], ["clones.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(
        "ix_document_chunks_embedding",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_index(
        "ix_document_chunks_clone_access",
        "document_chunks",
        ["clone_id", "access_tier"],
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
